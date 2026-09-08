from uuid import UUID
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Response, status

from youtube.apps.user.depends import CurrentUser
from youtube.apps.comment.schemas import CommentCreateSchema, CommentReadSchema
from youtube.apps.comment.service import CommentService

comment_router = APIRouter(prefix='/comments', tags=['comments'], route_class=DishkaRoute)


@comment_router.post(
    '/',
    status_code=status.HTTP_201_CREATED,
    response_model=CommentReadSchema,
)
async def create_comment(
    data: CommentCreateSchema,
    comment_service: FromDishka[CommentService],
    current_user: FromDishka[CurrentUser],
) -> CommentReadSchema:
    return await comment_service.create(data, user_id=current_user.id)


@comment_router.get(
    '/video/{video_id}',
    status_code=status.HTTP_200_OK,
    response_model=list[CommentReadSchema],
)
async def get_video_comments(
    video_id: UUID,
    comment_service: FromDishka[CommentService],
) -> list[CommentReadSchema]:
    return await comment_service.get_by_video(video_id)


@comment_router.delete(
    '/{comment_id}',
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    comment_id: UUID,
    current_user: FromDishka[CurrentUser],
    comment_service: FromDishka[CommentService],
) -> None:
    await comment_service.delete_comment(comment_id, current_user.id)


@comment_router.get(
    '/{comment_id}/replies',
    status_code=status.HTTP_200_OK,
    response_model=list[CommentReadSchema],
)
async def get_replies(
    comment_id: UUID,
    comment_service: FromDishka[CommentService],
) -> list[CommentReadSchema]:
    return await comment_service.get_replies(comment_id)

