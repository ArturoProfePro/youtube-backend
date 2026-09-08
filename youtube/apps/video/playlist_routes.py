from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter
from pydantic import BaseModel

from youtube.apps.user.types import CurrentUser
from youtube.apps.video.schemas.playlist import (
    AddVideoToPlaylistSchema,
    PlaylistCreateSchema,
    PlaylistReadSchema,
    PlaylistUpdateDataSchema,
)
from youtube.apps.video.service.playlist import PlaylistService

router = APIRouter(prefix='/playlists', route_class=DishkaRoute, tags=['playlists'])


@router.post('/', response_model=PlaylistReadSchema)
async def create_playlist(
    data: PlaylistCreateSchema,
    current_user: FromDishka[CurrentUser],
    playlist_service: FromDishka[PlaylistService],
) -> PlaylistReadSchema:
    return await playlist_service.create_playlist(current_user.id, data)


@router.get('/my', response_model=list[PlaylistReadSchema])
async def get_my_playlists(
    current_user: FromDishka[CurrentUser],
    playlist_service: FromDishka[PlaylistService],
) -> list[PlaylistReadSchema]:
    return await playlist_service.get_my_playlists(current_user.id)


@router.get('/{playlist_id}', response_model=PlaylistReadSchema)
async def get_playlist(
    playlist_id: UUID,
    current_user: FromDishka[CurrentUser | None],
    playlist_service: FromDishka[PlaylistService],
) -> PlaylistReadSchema:
    user_id = current_user.id if current_user else None
    return await playlist_service.get_playlist(playlist_id, user_id)


@router.patch('/{playlist_id}', response_model=PlaylistReadSchema)
async def update_playlist(
    playlist_id: UUID,
    data: PlaylistUpdateDataSchema,
    current_user: FromDishka[CurrentUser],
    playlist_service: FromDishka[PlaylistService],
) -> PlaylistReadSchema:
    return await playlist_service.update_playlist(playlist_id, current_user.id, data)


@router.delete('/{playlist_id}', status_code=204)
async def delete_playlist(
    playlist_id: UUID,
    current_user: FromDishka[CurrentUser],
    playlist_service: FromDishka[PlaylistService],
) -> None:
    await playlist_service.delete_playlist(playlist_id, current_user.id)


@router.post('/{playlist_id}/videos', response_model=PlaylistReadSchema)
async def add_video_to_playlist(
    playlist_id: UUID,
    data: AddVideoToPlaylistSchema,
    current_user: FromDishka[CurrentUser],
    playlist_service: FromDishka[PlaylistService],
) -> PlaylistReadSchema:
    return await playlist_service.add_video(playlist_id, current_user.id, data.video_slug, data.position)


@router.delete('/{playlist_id}/videos/{video_slug}', response_model=PlaylistReadSchema)
async def remove_video_from_playlist(
    playlist_id: UUID,
    video_slug: str,
    current_user: FromDishka[CurrentUser],
    playlist_service: FromDishka[PlaylistService],
) -> PlaylistReadSchema:
    return await playlist_service.remove_video(playlist_id, current_user.id, video_slug)


class ReorderSchema(BaseModel):
    position: int


@router.patch('/{playlist_id}/videos/{video_slug}/position', response_model=PlaylistReadSchema)
async def reorder_video_in_playlist(
    playlist_id: UUID,
    video_slug: str,
    data: ReorderSchema,
    current_user: FromDishka[CurrentUser],
    playlist_service: FromDishka[PlaylistService],
) -> PlaylistReadSchema:
    return await playlist_service.reorder_video(playlist_id, current_user.id, video_slug, data.position)
