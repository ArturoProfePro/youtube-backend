from sqlalchemy.orm import selectinload
import sqlalchemy as sa
from youtube.apps.comment.models import Comment
from youtube.apps.comment.schemas import (
    CommentCreateInDbSchema,
    CommentUpdateSchema,
    CommentCreateDbResponseSchema,
)
from youtube.repositories import DbCrudRepository


class CommentRepository(DbCrudRepository[Comment, CommentCreateDbResponseSchema, CommentCreateInDbSchema, CommentUpdateSchema]):

    @classmethod
    def select(cls) -> sa.Select[tuple[Comment]]:
        return sa.select(Comment).options(selectinload(Comment.user))
