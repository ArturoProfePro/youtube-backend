from typing import Optional
from uuid import UUID

from youtube.schemas import BaseSchema, ReadSchema, UpdateSchema, CreateSchema


class CommentAuthorSchema(BaseSchema):
    id: UUID
    username: str
    avatar: Optional[str] = None


class CommentReadSchema(ReadSchema):
    content: str
    video_id: UUID
    user_id: UUID
    parent_id: Optional[UUID]

    likes_count: int
    dislikes_count: int

    user: CommentAuthorSchema


class CommentCreateDbResponseSchema(ReadSchema):
    content: str
    video_id: UUID
    user_id: UUID
    parent_id: Optional[UUID]
    likes_count: int
    dislikes_count: int


class CommentCreateSchema(BaseSchema):
    content: str
    video_id: UUID
    parent_id: Optional[UUID] = None


class CommentCreateInDbSchema(CommentCreateSchema, CreateSchema):
    user_id: UUID


class CommentUpdateSchema(UpdateSchema):
    content: Optional[str]


from youtube.schemas_api import IComment, ICommentData  # noqa: E402
