"""
Comment routes: /comment
  GET    /comment/by-video/{publicId}  — list comments
  POST   /comment                       — create (auth)
  PUT    /comment/{id}                  — edit (auth)
  DELETE /comment/{id}                  — delete (auth)
"""
from uuid import UUID

import sqlalchemy as sa
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Optional

from youtube.apps.user.depends import CurrentUser
from youtube.apps.comment.service import CommentService
from youtube.apps.comment.schemas import CommentCreateSchema, CommentReadSchema

comment_router = APIRouter(prefix='/comment', tags=['comments'], route_class=DishkaRoute)


class CommentBody(BaseModel):
    text: str
    videoId: str


class CommentUpdateBody(BaseModel):
    text: str


@comment_router.get('/by-video/{publicId}', status_code=status.HTTP_200_OK)
async def get_comments_by_video(
    publicId: str,
    comment_service: FromDishka[CommentService],
) -> dict:
    """Get all comments for a video by publicId."""
    from youtube.apps.video.models import Video
    from youtube.db import SessionManagerProtocol
    from youtube.apps.comment.models import Comment

    # We need to look up video by public_id first
    comments = await comment_service.get_by_video_public_id(publicId)
    return {'comments': comments}


@comment_router.post('', status_code=status.HTTP_201_CREATED)
async def create_comment(
    body: CommentBody,
    current_user: FromDishka[CurrentUser],
    comment_service: FromDishka[CommentService],
) -> dict:
    """Create a comment on a video (auth required)."""
    return await comment_service.create_by_public_id(
        text=body.text,
        video_public_id=body.videoId,
        user_id=current_user.id,
    )


@comment_router.put('/{comment_id}', status_code=status.HTTP_200_OK)
async def update_comment(
    comment_id: UUID,
    body: CommentUpdateBody,
    current_user: FromDishka[CurrentUser],
    comment_service: FromDishka[CommentService],
) -> dict:
    """Edit a comment (auth required, must be owner)."""
    return await comment_service.update_comment(
        comment_id=comment_id,
        user_id=current_user.id,
        text=body.text,
    )


@comment_router.delete('/{comment_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    current_user: FromDishka[CurrentUser],
    comment_service: FromDishka[CommentService],
) -> None:
    """Delete a comment (auth required, must be owner)."""
    await comment_service.delete_comment(comment_id, current_user.id)
