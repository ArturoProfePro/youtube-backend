from typing import Any, Callable, Iterable, Self, override
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func, select

from youtube.apps.video.models import (
    TagCategory,
    Video,
    VideoDirectSource,
    VideoExternalPlayer,
    VideoTag,
    WatchHistory,
    VideoLike,
)
from youtube.apps.video.schemas import VideoCreateSchema, VideoReadSchema, VideoUpdateSchema
from youtube.exceptions import ModelNotFoundError
from youtube.repositories.crud import DbCrudRepository
from youtube.schemas.pagination import PaginationResultSchema, PaginationSchema


class VideoRepository(DbCrudRepository[Video, VideoReadSchema, VideoCreateSchema, VideoUpdateSchema]):
    """
    Repository for performing CRUD operations on Video models.
    """

    @classmethod
    @override
    def select(cls):
        return (
            super()
            .select()
            .options(
                selectinload(Video.tags).joinedload(VideoTag.category),
                selectinload(Video.direct_sources),
                selectinload(Video.external_players),
            )
        )

    async def increment_views(self, video_slug: str) -> None:
        async with self.session_manager.get_session() as s:
            stmt = (
                sa.update(self.model_type)
                .where(self.model_type.slug == video_slug)
                .values(views_count=self.model_type.views_count + 1)
            )
            await s.execute(stmt)
            await s.commit()

    async def get_by_slug(self: Self, slug: str) -> VideoReadSchema:
        """
        Get a model by slug.
        """
        async with self.session_manager.get_session() as s:
            statement = self.select().where(Video.slug == slug)
            model = await s.scalar(statement)
            if model is None:
                raise ModelNotFoundError(Video, message=f'Video with slug {slug} not found')
            return VideoReadSchema.model_validate(model)

    async def get_by_slug_with_progress(self, slug: str, user_id: UUID | None = None) -> VideoReadSchema:
        if user_id is None:
            return await self.get_by_slug(slug)

        async with self.session_manager.get_session() as s:
            stmt = (
                sa.select(
                    self.model_type,
                    WatchHistory.progress_seconds.label('progress_seconds'),
                    VideoLike.is_like.label('user_reaction'),
                )
                .options(
                    selectinload(Video.tags).joinedload(VideoTag.category),
                    selectinload(Video.direct_sources),
                    selectinload(Video.external_players),
                )
                .outerjoin(WatchHistory, (Video.id == WatchHistory.video_id) & (WatchHistory.user_id == user_id))
                .outerjoin(VideoLike, (Video.id == VideoLike.video_id) & (VideoLike.user_id == user_id))
                .where(Video.slug == slug)
            )
            result = await s.execute(stmt)
            row = result.first()
            if row is None:
                raise ModelNotFoundError(Video, message=f'Video with slug {slug} not found')

            video, progress_seconds, user_reaction = row
            setattr(video, 'user_progress', progress_seconds)  # noqa: B010
            setattr(video, 'user_reaction', user_reaction)  # noqa: B010
            return VideoReadSchema.model_validate(video)

    async def get_by_ids_with_progress(self, ids: Iterable[UUID]) -> list[VideoReadSchema]:
        async with self.session_manager.get_session() as s:
            stmt = (
                sa.select(
                    self.model_type,
                    WatchHistory.progress_seconds.label('progress_seconds'),
                    VideoLike.is_like.label('user_reaction'),
                )
                .options(
                    selectinload(Video.tags).joinedload(VideoTag.category),
                    selectinload(Video.direct_sources),
                    selectinload(Video.external_players),
                )
                .outerjoin(WatchHistory, (Video.id == WatchHistory.video_id))
                .outerjoin(VideoLike, (Video.id == VideoLike.video_id))
                .where(Video.id.in_(ids))
            )
            result = await s.execute(stmt)
            rows = result.all()
            videos = []
            for row in rows:
                video, progress_seconds, user_reaction = row
                setattr(video, 'user_progress', progress_seconds)  # noqa: B010
                setattr(video, 'user_reaction', user_reaction)  # noqa: B010
                videos.append(VideoReadSchema.model_validate(video))
            return videos

    async def paginate_with_tag_filter(
        self: Self,
        pagination: PaginationSchema,
        *,
        search: str | None = None,
        search_by: Iterable[str] | None = None,
        sorting: Iterable[str] | None = None,
        tag_slug: str | None = None,
        user_id: UUID | None = None,
    ) -> PaginationResultSchema[VideoReadSchema]:
        """
        Get a list of models with pagination, search, sorting, and filters.
        """
        search_by = search_by or []
        sorting = sorting or []

        where_clauses = []

        if tag_slug:
            where_clauses.append(self.model_type.tags.any(VideoTag.slug == tag_slug))

        if search:
            search_where: sa.ColumnElement[Any] = sa.false()
            for sb in search_by:
                search_where = sa.or_(search_where, getattr(self.model_type, sb).ilike(f'%{search}%'))
            where_clauses.append(search_where)

        async with self.session_manager.get_session() as s:
            order_by_expr = self.get_order_by_expr(sorting)
            if user_id is not None:
                statement = (
                    sa.select(
                        self.model_type,
                        WatchHistory.progress_seconds.label('progress_seconds'),
                        VideoLike.is_like.label('user_reaction'),
                    )
                    .options(
                        selectinload(Video.tags).joinedload(VideoTag.category),
                        selectinload(Video.direct_sources),
                        selectinload(Video.external_players),
                    )
                    .outerjoin(WatchHistory, (Video.id == WatchHistory.video_id) & (WatchHistory.user_id == user_id))
                    .outerjoin(VideoLike, (Video.id == VideoLike.video_id) & (VideoLike.user_id == user_id))
                    .where(*where_clauses)
                )
                result = await s.execute(
                    statement.limit(pagination.limit).offset(pagination.offset).order_by(*order_by_expr)
                )
                rows = result.all()
                objects = []
                for row in rows:
                    video, progress_seconds, user_reaction = row
                    setattr(video, 'user_progress', progress_seconds)  # noqa: B010
                    setattr(video, 'user_reaction', user_reaction)  # noqa: B010
                    objects.append(self.model_validate(video))
            else:
                statement = self.select().where(*where_clauses)
                models = (
                    (
                        await s.execute(
                            statement.limit(pagination.limit).offset(pagination.offset).order_by(*order_by_expr)
                        )
                    )
                    .scalars()
                    .all()
                )
                objects = [self.model_validate(model) for model in models]

            count_statement = sa.select(func.count(self.model_type.id)).where(*where_clauses)
            count = (await s.execute(count_statement)).scalar_one()
            return PaginationResultSchema(count=count, objects=objects)

    async def save_video(self, video_data: VideoCreateSchema) -> VideoReadSchema:
        """
        Create or update a video based on source_url and external_id.
        """
        async with self.session_manager.get_session() as session:
            stmt = self.select().where(
                Video.source_url == video_data.source_url,
                Video.external_id == video_data.external_id,
            )
            result = await session.execute(stmt)
            db_video = result.scalar_one_or_none()

            is_new = db_video is None

            if is_new:
                db_video = Video(
                    source_url=video_data.source_url,
                    external_id=video_data.external_id,
                    russian_title=video_data.russian_title,
                    official_title=video_data.official_title,
                    other_titles=video_data.other_titles,
                    description=video_data.description,
                    poster_url=video_data.poster_url,
                    is_censored=video_data.is_censored,
                    duration=video_data.duration,
                    studio=video_data.studio,
                    year=video_data.year,
                    translation_types=video_data.translation_types,
                )
            else:
                for key, val in video_data.model_dump(
                    exclude={'tags', 'direct_sources', 'external_players', 'id'}
                ).items():
                    setattr(db_video, key, val)

            tags_objs: list[VideoTag] = []
            if video_data.tags:
                category_names = {tag.category.name for tag in video_data.tags}
                stmt = sa.select(TagCategory).where(TagCategory.name.in_(category_names))
                existing_categories = (await session.execute(stmt)).scalars().all()
                existing_category_map = {category.name: category for category in existing_categories}

                for category in category_names:
                    if category not in existing_category_map:
                        category_obj = TagCategory(name=category)
                        session.add(category_obj)
                        existing_category_map[category] = category_obj

                await session.flush()

                tag_conditions = [
                    sa.and_(
                        VideoTag.category_id == existing_category_map[tag.category.name].id,
                        VideoTag.name == tag.name,
                    )
                    for tag in video_data.tags
                ]
                stmt_tags = sa.select(VideoTag).where(sa.or_(*tag_conditions))

                existing_tags = {
                    (tag.category.name, tag.name): tag for tag in (await session.execute(stmt_tags)).scalars()
                }

                seen_keys = set()

                for tag in video_data.tags:
                    category_id = existing_category_map[tag.category.name].id
                    key = (tag.category.name, tag.name)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)

                    if key in existing_tags:
                        tags_objs.append(existing_tags[key])
                    else:
                        new_tag = VideoTag(name=tag.name, slug=tag.slug, category_id=category_id)
                        session.add(new_tag)
                        tags_objs.append(new_tag)
                        existing_tags[key] = new_tag

            if is_new:
                db_video.tags = tags_objs
                db_video.direct_sources = [VideoDirectSource(**ds.model_dump()) for ds in video_data.direct_sources]
                db_video.external_players = [
                    VideoExternalPlayer(**ep.model_dump()) for ep in video_data.external_players
                ]
                session.add(db_video)
            else:
                db_video.tags = tags_objs
                db_video.direct_sources.clear()
                db_video.direct_sources.extend(
                    [VideoDirectSource(**ds.model_dump()) for ds in video_data.direct_sources]
                )
                db_video.external_players.clear()
                db_video.external_players.extend(
                    [VideoExternalPlayer(**ep.model_dump()) for ep in video_data.external_players]
                )

            await session.flush()
            await session.refresh(db_video, ['tags', 'direct_sources', 'external_players'])
            return self.model_validate(db_video)

    @override
    async def create(self: Self, create_object: VideoCreateSchema) -> VideoReadSchema:
        """
        Override default create method to handle relationships correctly.
        """
        return await self.save_video(create_object)

    @override
    async def upsert(self: Self, create_object: VideoCreateSchema) -> VideoReadSchema:
        """
        Override default upsert method to handle relationships correctly.
        """
        return await self.save_video(create_object)

    @override
    async def update(self: Self, update_object: VideoUpdateSchema) -> VideoReadSchema:
        """
        Override default update method to handle relationships correctly.
        """

        if not hasattr(update_object, 'id'):
            raise ValueError('update_object must have an id')

        async with self.session_manager.get_session() as session:
            stmt = self.select().where(Video.id == update_object.id)
            result = await session.execute(stmt)
            db_video = result.scalar_one_or_none()
            if db_video is None:
                raise ValueError(f'Video with id {update_object.id} not found')

            create_data = VideoCreateSchema(**update_object.model_dump(exclude_unset=True))
            return await self.save_video(create_data)

    async def toggle_reaction(self, slug: str, user_id: UUID, is_like: bool) -> tuple[int, int, bool | None]:
        """
        Toggles the reaction (like/dislike) for a user on a video.
        Returns: (likes_count, dislikes_count, current_user_reaction)
        """
        async with self.session_manager.get_session() as session:
            stmt = sa.select(Video).where(Video.slug == slug).with_for_update()
            result = await session.execute(stmt)
            video = result.scalar_one_or_none()
            if video is None:
                raise ModelNotFoundError(Video, message=f'Video with slug {slug} not found')

            stmt_like = (
                sa.select(VideoLike)
                .where(
                    VideoLike.video_id == video.id,
                    VideoLike.user_id == user_id,
                )
                .options(sa.orm.lazyload(VideoLike.user))
                .with_for_update()
            )
            result_like = await session.execute(stmt_like)
            existing_reaction = result_like.scalar_one_or_none()

            new_reaction: bool | None = None

            if existing_reaction is None:
                reaction = VideoLike(video_id=video.id, user_id=user_id, is_like=is_like)
                session.add(reaction)
                if is_like:
                    video.likes_count += 1
                else:
                    video.dislikes_count += 1
                new_reaction = is_like
            elif existing_reaction.is_like == is_like:
                await session.delete(existing_reaction)
                if is_like:
                    video.likes_count = max(0, video.likes_count - 1)
                else:
                    video.dislikes_count = max(0, video.dislikes_count - 1)
                new_reaction = None
            else:
                existing_reaction.is_like = is_like
                if is_like:
                    video.likes_count += 1
                    video.dislikes_count = max(0, video.dislikes_count - 1)
                else:
                    video.dislikes_count += 1
                    video.likes_count = max(0, video.likes_count - 1)
                new_reaction = is_like

            await session.commit()
            return video.likes_count, video.dislikes_count, new_reaction
