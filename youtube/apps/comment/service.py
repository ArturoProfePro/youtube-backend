from uuid import UUID

import sqlalchemy as sa

from youtube.apps.comment.models import Comment
from youtube.apps.comment.repository import CommentRepository
from youtube.apps.comment.schemas import CommentCreateInDbSchema, CommentCreateSchema, CommentReadSchema
from youtube.exceptions import PermissionDeniedError


def _comment_to_dict(m: Comment) -> dict:
    user_dict = {}
    if m.user:
        user_dict = {
            'id': str(m.user.id),
            'username': m.user.username,
            'avatar': m.user.avatar or None,
        }
    return {
        'id': str(m.id),
        'text': m.text or m.content or '',
        'createdAt': m.created_at.isoformat() if m.created_at else '',
        'videoId': str(m.video_id),
        'user': user_dict,
    }


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

    async def get_by_video_public_id(self, public_id: str) -> list[dict]:
        """Get comments for a video by its publicId."""
        from youtube.apps.video.models import Video

        async with self.repository.session_manager.get_session() as s:
            # Resolve video id
            vid_stmt = sa.select(Video).where(Video.public_id == public_id)
            vid_result = await s.execute(vid_stmt)
            video = vid_result.scalar_one_or_none()
            if video is None:
                return []

            stmt = (
                self.repository.select()
                .where((Comment.video_id == video.id) & (Comment.parent_id == None))  # noqa: E711
                .order_by(Comment.created_at.desc())
            )
            models = (await s.execute(stmt)).scalars().all()
            return [_comment_to_dict(m) for m in models]

    async def create_by_public_id(self, text: str, video_public_id: str, user_id: UUID) -> dict:
        """Create a comment on a video identified by publicId."""
        from youtube.apps.video.models import Video

        async with self.repository.session_manager.get_session() as s:
            vid_stmt = sa.select(Video).where(Video.public_id == video_public_id)
            result = await s.execute(vid_stmt)
            video = result.scalar_one_or_none()
            if video is None:
                from youtube.exceptions import ModelNotFoundError
                raise ModelNotFoundError(Video, model_id=video_public_id)

            comment = Comment(
                text=text,
                content=text,
                video_id=video.id,
                user_id=user_id,
            )
            s.add(comment)
            await s.flush()

            # Reload with user
            stmt = self.repository.select().where(Comment.id == comment.id)
            model = (await s.execute(stmt)).scalar_one()
            return _comment_to_dict(model)

    async def update_comment(self, comment_id: UUID, user_id: UUID, text: str) -> dict:
        """Edit a comment's text."""
        async with self.repository.session_manager.get_session() as s:
            stmt = self.repository.select().where(Comment.id == comment_id)
            model = (await s.execute(stmt)).scalar_one_or_none()
            if model is None:
                from youtube.exceptions import ModelNotFoundError
                raise ModelNotFoundError(Comment, model_id=comment_id)
            if model.user_id != user_id:
                raise PermissionDeniedError()
            model.text = text
            model.content = text
            return _comment_to_dict(model)

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
        async with self.repository.session_manager.get_session() as s:
            stmt = self.repository.select().where(Comment.id == comment_id)
            model = (await s.execute(stmt)).scalar_one_or_none()
            if model is None:
                from youtube.exceptions import ModelNotFoundError
                raise ModelNotFoundError(Comment, model_id=comment_id)
            if model.user_id != user_id:
                raise PermissionDeniedError()
            await s.delete(model)
