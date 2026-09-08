from typing import Iterable
from uuid import UUID
from youtube.apps.video.repository import VideoRepository
from youtube.apps.video.schemas import (
    VideoCreateSchema,
    VideoReadSchema,
    VideoUpdateSchema,
)
from youtube.schemas.pagination import (
    PaginationResultSchema,
    PaginationSchema,
)


class VideoService:
    def __init__(self, repository: VideoRepository):
        self.repository = repository

    async def get_videos(
        self,
        pagination: PaginationSchema,
        sorting: Iterable[str] | None = None,
        search: str | None = None,
        user_id: UUID | None = None,
    ) -> PaginationResultSchema[VideoReadSchema]:

        result = await self.repository.paginate_with_tag_filter(
            pagination,
            search=search,
            search_by=['russian_title', 'official_title'],
            sorting=sorting,
            user_id=user_id,
        )
        return result

    async def get_videos_by_tag(
        self,
        tag_slug: str,
        pagination: PaginationSchema,
        sorting: Iterable[str] | None = None,
        search: str | None = None,
        user_id: UUID | None = None,
    ) -> PaginationResultSchema[VideoReadSchema]:

        result = await self.repository.paginate_with_tag_filter(
            pagination,
            search=search,
            search_by=['russian_title', 'official_title'],
            sorting=sorting,
            tag_slug=tag_slug,
            user_id=user_id,
        )
        return result

    async def get_video(self, video_id: UUID) -> VideoReadSchema:
        return await self.repository.get(video_id)

    async def get_video_by_slug(self, slug: str, user_id: UUID | None = None) -> VideoReadSchema:
        return await self.repository.get_by_slug_with_progress(slug, user_id)

    async def create_video(self, video: VideoCreateSchema) -> VideoReadSchema:
        return await self.repository.create(video)

    async def update_video(self, video: VideoUpdateSchema) -> VideoReadSchema:
        return await self.repository.update(video)

    async def get_videos_by_ids(self, video_ids: list[UUID]) -> list[VideoReadSchema]:
        return await self.repository.get_by_ids(video_ids)

    async def toggle_like(self, video_slug: str, user_id: UUID) -> tuple[int, int, bool | None]:
        return await self.repository.toggle_reaction(video_slug, user_id, is_like=True)

    async def toggle_dislike(self, video_slug: str, user_id: UUID) -> tuple[int, int, bool | None]:
        return await self.repository.toggle_reaction(video_slug, user_id, is_like=False)
