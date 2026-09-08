from uuid import UUID

from youtube.apps.video.repository import VideoTagRepository
from youtube.apps.video.schemas import VideoTagReadSchema, VideoTagUpdateSchema, VideoTagCreateSchema


class VideoTagService:
    def __init__(self, tag_repository: VideoTagRepository):
        self.tag_repository = tag_repository

    async def get_all(self) -> list[VideoTagReadSchema]:
        return await self.tag_repository.get_all()

    async def get(self, id: UUID) -> VideoTagReadSchema:
        return await self.tag_repository.get(id)

    async def get_by_category(self, category_id: UUID) -> list[VideoTagReadSchema]:
        return await self.tag_repository.get_by_category(category_id)

    async def create(self, tag: VideoTagCreateSchema) -> VideoTagReadSchema:
        return await self.tag_repository.create(tag)

    async def update(self, tag: VideoTagUpdateSchema) -> VideoTagReadSchema:
        return await self.tag_repository.update(tag)

    async def delete(self, id):
        return self.tag_repository.delete(id)
