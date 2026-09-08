from uuid import UUID

from youtube.apps.comment.models import Comment
from youtube.apps.comment.repository import CommentRepository
from youtube.apps.comment.schemas import CommentCreateInDbSchema, CommentCreateSchema, CommentReadSchema


class CommentService:
    def __init__(self, repository: CommentRepository):
        self.repository = repository

    async def create(self, create_schema: CommentCreateSchema, user_id: UUID) -> CommentReadSchema:
        created = await self.repository.create(
            CommentCreateInDbSchema(
                content=create_schema.content,
                video_id=create_schema.video_id,
                user_id=user_id,
                parent_id=create_schema.parent_id,
            )
        )
        async with self.repository.session_manager.get_session() as s:
            stmt = self.repository.select().where(Comment.id == created.id)
            model = (await s.execute(stmt)).scalar_one()
            return CommentReadSchema.model_validate(model, from_attributes=True)

    async def get_by_video(self, video_id: UUID) -> list[CommentReadSchema]:
        async with self.repository.session_manager.get_session() as s:
            stmt = (
                self.repository.select()
                .where((Comment.video_id == video_id) & (Comment.parent_id == None))  # noqa: E711
                .order_by(Comment.created_at.desc())
            )
            models = (await s.execute(stmt)).scalars().all()
            return [CommentReadSchema.model_validate(m, from_attributes=True) for m in models]

    async def get_replies(self, comment_id: UUID) -> list[CommentReadSchema]:
        async with self.repository.session_manager.get_session() as s:
            stmt = (
                self.repository.select()
                .where(Comment.parent_id == comment_id)
                .order_by(Comment.created_at.asc())
            )
            models = (await s.execute(stmt)).scalars().all()
            return [CommentReadSchema.model_validate(m, from_attributes=True) for m in models]

    async def delete_comment(self, comment_id: UUID, user_id: UUID) -> None:
        from fastapi import HTTPException, status

        comment = await self.repository.get(comment_id)
        if comment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete someone else's comment"
            )
        await self.repository.delete([comment_id])
