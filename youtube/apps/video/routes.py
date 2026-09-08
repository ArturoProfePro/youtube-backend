from uuid import UUID
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from youtube.apps.user.types import CurrentUser
from youtube.apps.video.schemas import (
    VideoListItemResponseSchema,
    VideoPageResponseSchema,
    VideoReadSchema,
    VideoTagReadSchema,
    VideoReactionResponseSchema,
)
from youtube.apps.video.schemas.watch_history import WatchHistorySchema
from youtube.apps.video.service import VideoService, VideoTagService, VideoViewService
from youtube.depends import Pagination, Sorting
from youtube.schemas.pagination import PaginationResultSchema

router = APIRouter(prefix='', route_class=DishkaRoute, tags=['video'])


@router.get('/videos', response_model=PaginationResultSchema[VideoListItemResponseSchema])
async def get_videos(
    pagination: Pagination,
    sorting: Sorting,
    video_service: FromDishka[VideoService],
    current_user: FromDishka[CurrentUser | None],
    search: str | None = None,
) -> PaginationResultSchema[VideoReadSchema]:
    user_id = current_user.id if current_user else None
    return await video_service.get_videos(
        pagination=pagination.to_pagination_schema(),
        search=search,
        sorting=sorting,
        user_id=user_id,
    )


@router.post('/videos', response_model=list[VideoListItemResponseSchema])
async def get_videos_by_ids(
    video_ids: list[UUID],
    video_service: FromDishka[VideoService],
) -> list[VideoReadSchema]:
    return await video_service.get_videos_by_ids(video_ids)


@router.get('/video/{video_slug}', response_model=VideoPageResponseSchema)
async def get_video_by_slug(
    video_slug: str,
    video_service: FromDishka[VideoService],
    current_user: FromDishka[CurrentUser | None],
) -> VideoReadSchema:
    user_id = current_user.id if current_user else None
    return await video_service.get_video_by_slug(video_slug, user_id)


@router.get('/tags', response_model=list[VideoTagReadSchema])
async def get_all_tags(tag_service: FromDishka[VideoTagService]) -> list[VideoTagReadSchema]:
    return await tag_service.get_all()


@router.get('/tag/{tag_slug}/videos', response_model=PaginationResultSchema[VideoListItemResponseSchema])
async def get_videos_by_tag(
    tag_slug: str,
    pagination: Pagination,
    sorting: Sorting,
    video_service: FromDishka[VideoService],
    current_user: FromDishka[CurrentUser | None],
    search: str | None = None,
) -> PaginationResultSchema[VideoReadSchema]:
    user_id = current_user.id if current_user else None
    return await video_service.get_videos_by_tag(
        pagination=pagination.to_pagination_schema(),
        search=search,
        sorting=sorting,
        tag_slug=tag_slug,
        user_id=user_id,
    )


@router.post('/video/{video_slug}/view')
async def register_video_view(
    video_slug: str,
    video_view_service: FromDishka[VideoViewService],
):
    return await video_view_service.increment_views(video_slug)


@router.post('/video/view')
async def add_video_watch_history(
    watch_history: WatchHistorySchema,
    current_user: FromDishka[CurrentUser],
    video_view_service: FromDishka[VideoViewService],
):
    await video_view_service.add_to_watch_history(current_user, watch_history)


@router.post('/video/{video_slug}/like', response_model=VideoReactionResponseSchema)
async def toggle_like(
    video_slug: str,
    current_user: FromDishka[CurrentUser],
    video_service: FromDishka[VideoService],
) -> VideoReactionResponseSchema:
    likes, dislikes, reaction = await video_service.toggle_like(video_slug, current_user.id)
    return VideoReactionResponseSchema(
        likes_count=likes,
        dislikes_count=dislikes,
        user_reaction=reaction,
    )


@router.post('/video/{video_slug}/dislike', response_model=VideoReactionResponseSchema)
async def toggle_dislike(
    video_slug: str,
    current_user: FromDishka[CurrentUser],
    video_service: FromDishka[VideoService],
) -> VideoReactionResponseSchema:
    likes, dislikes, reaction = await video_service.toggle_dislike(video_slug, current_user.id)
    return VideoReactionResponseSchema(
        likes_count=likes,
        dislikes_count=dislikes,
        user_reaction=reaction,
    )
