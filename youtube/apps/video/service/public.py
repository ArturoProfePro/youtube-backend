"""
VideoPublicService — handles public video endpoints.
ChannelService    — handles channel endpoints.
"""
from uuid import UUID
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from youtube.db import SessionManagerProtocol


class VideoPublicService:
    def __init__(self, session_manager: SessionManagerProtocol) -> None:
        self.session_manager = session_manager

    async def get_all(self, search_term: str | None = None) -> list[dict]:
        from youtube.apps.video.models import Video
        async with self.session_manager.get_session() as s:
            stmt = sa.select(Video).where(Video.is_public == True)
            if search_term:
                stmt = stmt.where(
                    (Video.title.ilike(f'%{search_term}%')) |
                    (Video.russian_title.ilike(f'%{search_term}%')) |
                    (Video.description.ilike(f'%{search_term}%'))
                )
            stmt = stmt.order_by(Video.created_at.desc()).limit(50)
            result = await s.execute(stmt)
            videos = result.scalars().all()
            return [self._to_dict(v) for v in videos]

    async def get_trending(self) -> list[dict]:
        from youtube.apps.video.models import Video
        async with self.session_manager.get_session() as s:
            stmt = (
                sa.select(Video)
                .where(Video.is_public == True)
                .order_by((Video.views + Video.views_count).desc())
                .limit(20)
            )
            result = await s.execute(stmt)
            return [self._to_dict(v) for v in result.scalars().all()]

    async def get_by_category(self, category: str) -> list[dict]:
        from youtube.apps.video.models import Video, VideoTag, video_tags_association, TagCategory
        async with self.session_manager.get_session() as s:
            stmt = (
                sa.select(Video)
                .join(video_tags_association, video_tags_association.c.video_id == Video.id)
                .join(VideoTag, VideoTag.id == video_tags_association.c.tag_id)
                .join(TagCategory, TagCategory.id == VideoTag.category_id)
                .where(Video.is_public == True)
                .where(
                    VideoTag.slug.ilike(f'%{category}%') |
                    VideoTag.name.ilike(f'%{category}%') |
                    TagCategory.name.ilike(f'%{category}%')
                )
                .limit(30)
            )
            result = await s.execute(stmt)
            return [self._to_dict(v) for v in result.scalars().all()]

    async def get_explore(
        self,
        page: int = 1,
        limit: int = 10,
        user_id: str | None = None,
        exclude_ids: list[str] | None = None,
    ) -> dict:
        from youtube.apps.video.models import Video
        async with self.session_manager.get_session() as s:
            stmt = sa.select(Video).where(Video.is_public == True)
            if exclude_ids:
                stmt = stmt.where(Video.public_id.not_in(exclude_ids))
            count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
            total = (await s.execute(count_stmt)).scalar_one()
            stmt = stmt.order_by(Video.created_at.desc()).offset((page - 1) * limit).limit(limit)
            result = await s.execute(stmt)
            videos = result.scalars().all()
            total_pages = (total + limit - 1) // limit if total > 0 else 0
            return {
                'page': page,
                'limit': limit,
                'totalCount': total,
                'totalPages': total_pages,
                'videos': [self._to_dict(v) for v in videos],
            }

    async def get_by_public_id(self, public_id: str) -> dict:
        from youtube.apps.video.models import Video
        async with self.session_manager.get_session() as s:
            stmt = sa.select(Video).where(Video.public_id == public_id)
            result = await s.execute(stmt)
            video = result.scalar_one_or_none()
            if video is None:
                from youtube.exceptions import ModelNotFoundError
                raise ModelNotFoundError(Video, model_id=public_id)
            # Get similar (same channel or tags)
            similar_stmt = (
                sa.select(Video)
                .where(Video.is_public == True)
                .where(Video.id != video.id)
                .where(Video.channel_id == video.channel_id)
                .limit(6)
            )
            similar_result = await s.execute(similar_stmt)
            similar = similar_result.scalars().all()
            video_dict = self._to_dict_full(video)
            video_dict['similarVideos'] = [self._to_dict(v) for v in similar]
            return video_dict

    async def increment_views(self, public_id: str) -> None:
        from youtube.apps.video.models import Video
        async with self.session_manager.get_session() as s:
            stmt = (
                sa.update(Video)
                .where(Video.public_id == public_id)
                .values(views=Video.views + 1, views_count=Video.views_count + 1)
            )
            await s.execute(stmt)

    def _to_dict(self, v) -> dict:
        channel_dict = self._channel_dict(v)
        return {
            'id': str(v.id),
            'publicId': v.public_id,
            'title': v.title or v.russian_title or '',
            'description': v.description,
            'thumbnailUrl': v.thumbnail_url or v.poster_url or '',
            'videoFileName': v.video_file_name or '',
            'maxResolution': v.max_resolution or '1080p',
            'views': (v.views or 0) + (v.views_count or 0),
            'isPublic': v.is_public,
            'createdAt': v.created_at.isoformat() if hasattr(v, 'created_at') and v.created_at else '',
            'channel': channel_dict,
        }

    def _to_dict_full(self, v) -> dict:
        d = self._to_dict(v)
        likes = [{'userId': str(lk.user_id)} for lk in (v.likes or [])]
        comments = [
            {
                'id': str(c.id),
                'text': c.text or c.content or '',
                'createdAt': c.created_at.isoformat() if c.created_at else '',
                'videoId': str(c.video_id),
                'user': {'id': str(c.user.id), 'username': c.user.username} if c.user else {},
            }
            for c in (v.comments or [])
        ]
        d['likes'] = likes
        d['comments'] = comments
        d['tags'] = list(v.tags_list or [])
        return d

    def _channel_dict(self, v) -> dict | None:
        if not v.channel:
            return None
        ch = v.channel
        return {
            'id': str(ch.id),
            'slug': ch.slug,
            'description': ch.description or '',
            'isVerified': ch.is_verified,
            'avatar': ch.avatar or '',
            'banner': ch.banner or '',
        }


class ChannelService:
    def __init__(self, session_manager: SessionManagerProtocol) -> None:
        self.session_manager = session_manager

    async def get_all(self) -> list[dict]:
        from youtube.apps.user.models import Channel
        async with self.session_manager.get_session() as s:
            result = await s.execute(sa.select(Channel))
            channels = result.scalars().all()
            return [self._to_dict(ch) for ch in channels]

    async def get_by_slug(self, slug: str) -> dict:
        from youtube.apps.user.models import Channel
        async with self.session_manager.get_session() as s:
            stmt = sa.select(Channel).where(Channel.slug == slug)
            result = await s.execute(stmt)
            ch = result.scalar_one_or_none()
            if ch is None:
                from youtube.exceptions import ModelNotFoundError
                raise ModelNotFoundError(Channel, model_id=slug)
            return self._to_dict(ch, include_videos=True)

    async def toggle_subscribe(self, slug: str, user_id: UUID) -> dict:
        from youtube.apps.user.models import Channel, Subscription
        async with self.session_manager.get_session() as s:
            ch_stmt = sa.select(Channel).where(Channel.slug == slug)
            result = await s.execute(ch_stmt)
            ch = result.scalar_one_or_none()
            if ch is None:
                from youtube.exceptions import ModelNotFoundError
                raise ModelNotFoundError(Channel, model_id=slug)

            sub_stmt = sa.select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.channel_id == ch.id,
            )
            result = await s.execute(sub_stmt)
            existing = result.scalar_one_or_none()

            if existing:
                await s.delete(existing)
                return {'subscribed': False}
            else:
                new_sub = Subscription(user_id=user_id, channel_id=ch.id)
                s.add(new_sub)
                return {'subscribed': True}

    def _to_dict(self, ch, include_videos=False) -> dict:
        owner = None
        if ch.user:
            owner = {'id': str(ch.user.id), 'username': ch.user.username, 'email': ch.user.email}
        videos = []
        if include_videos and ch.videos:
            for v in ch.videos:
                if v.is_public:
                    videos.append({
                        'id': str(v.id),
                        'publicId': v.public_id,
                        'title': v.title or v.russian_title or '',
                        'thumbnailUrl': v.thumbnail_url or v.poster_url or '',
                        'views': (v.views or 0) + (v.views_count or 0),
                        'isPublic': v.is_public,
                        'createdAt': v.created_at.isoformat() if v.created_at else '',
                    })
        subs = [{'id': str(s.user_id)} for s in (ch.subscribers or [])]
        return {
            'id': str(ch.id),
            'slug': ch.slug,
            'description': ch.description or '',
            'isVerified': ch.is_verified,
            'avatar': ch.avatar or '',
            'banner': ch.banner or '',
            'owner': owner,
            'videos': videos,
            'subscriptions': subs,
            'createdAt': ch.created_at.isoformat() if hasattr(ch, 'created_at') and ch.created_at else '',
        }
