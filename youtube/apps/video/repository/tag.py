from typing import Self, override
from uuid import UUID

from sqlalchemy import Select
from sqlalchemy.orm import selectinload

from youtube.apps.video.models import VideoTag
from youtube.apps.video.schemas import VideoTagCreateSchema, VideoTagReadSchema, VideoTagUpdateSchema
from youtube.repositories.crud.db import DbCrudRepository


class VideoTagRepository(DbCrudRepository[VideoTag, VideoTagReadSchema, VideoTagCreateSchema, VideoTagUpdateSchema]):
    @override
    def select(self: Self) -> Select:
        return (
            super()
            .select()
            .options(
                selectinload(VideoTag.category),
            )
        )

    async def get_by_category(self: Self, category_id: UUID) -> list[VideoTagReadSchema]:
        """
        Get a list of models by category.
        """

        async with self.session_manager.get_session() as s:
            statement = self.select().where(VideoTag.category_id == category_id)
            models = (await s.execute(statement)).scalars().all()
            return [VideoTagReadSchema.model_validate(model) for model in models]
