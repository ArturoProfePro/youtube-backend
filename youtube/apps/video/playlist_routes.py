from uuid import UUID
from typing import Optional, List, Any
import sqlalchemy as sa

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status, HTTPException
from pydantic import BaseModel

from youtube.apps.user.types import CurrentUser
from youtube.apps.video.models import Playlist, PlaylistVideo, Video
from youtube.apps.video.public_routes import _video_to_dict
from youtube.db import SessionManagerProtocol
from youtube.exceptions import ModelNotFoundError, PermissionDeniedError

router = APIRouter(prefix='/playlists', route_class=DishkaRoute, tags=['playlists'])


class CreatePlaylistBody(BaseModel):
    title: Optional[str] = None
    name: Optional[str] = None
    videoPublicId: Optional[str] = None


class ToggleVideoBody(BaseModel):
    videoId: str  # Can be publicId or UUID string


def _format_playlist(pl: Playlist) -> dict:
    videos = []
    if pl.videos:
        for pv in pl.videos:
            if pv.video:
                videos.append(_video_to_dict(pv.video))
    return {
        'id': str(pl.id),
        'name': pl.name or pl.title,
        'userId': str(pl.user_id),
        'createdAt': pl.created_at.isoformat() if hasattr(pl, 'created_at') and pl.created_at else '',
        'videos': videos,
    }


@router.get('', status_code=status.HTTP_200_OK)
@router.get('/my', status_code=status.HTTP_200_OK)
async def get_user_playlists(
    current_user: FromDishka[CurrentUser],
    session_manager: FromDishka[SessionManagerProtocol],
) -> List[dict]:
    """Get current user's playlists."""
    async with session_manager.get_session() as s:
        stmt = (
            sa.select(Playlist)
            .where(Playlist.user_id == current_user.id)
            .order_by(Playlist.created_at.desc())
        )
        result = await s.execute(stmt)
        playlists = result.scalars().all()
        return [_format_playlist(pl) for pl in playlists]


@router.get('/{playlist_id}', status_code=status.HTTP_200_OK)
async def get_playlist_by_id(
    playlist_id: UUID,
    session_manager: FromDishka[SessionManagerProtocol],
) -> dict:
    """Get playlist by ID."""
    async with session_manager.get_session() as s:
        stmt = sa.select(Playlist).where(Playlist.id == playlist_id)
        result = await s.execute(stmt)
        playlist = result.scalar_one_or_none()
        if playlist is None:
            raise ModelNotFoundError(Playlist, model_id=playlist_id)
        return _format_playlist(playlist)


@router.post('', status_code=status.HTTP_200_OK)
async def create_playlist(
    body: CreatePlaylistBody,
    current_user: FromDishka[CurrentUser],
    session_manager: FromDishka[SessionManagerProtocol],
) -> dict:
    """Create a new playlist and optionally add an initial video."""
    title = body.title or body.name or 'New Playlist'
    async with session_manager.get_session() as s:
        pl = Playlist(
            title=title,
            name=title,
            user_id=current_user.id,
            is_private=False,
        )
        s.add(pl)
        await s.flush()

        if body.videoPublicId:
            # Look up video by public_id or uuid
            vid_stmt = sa.select(Video).where(
                (Video.public_id == body.videoPublicId) |
                (sa.cast(Video.id, sa.String) == body.videoPublicId)
            )
            vid_result = await s.execute(vid_stmt)
            video = vid_result.scalar_one_or_none()
            if video:
                pv = PlaylistVideo(playlist_id=pl.id, video_id=video.id, position=0)
                s.add(pv)
                await s.flush()

        # Reload with relationships
        stmt = sa.select(Playlist).where(Playlist.id == pl.id)
        result = await s.execute(stmt)
        created_pl = result.scalar_one()
        return _format_playlist(created_pl)


@router.post('/{playlist_id}/toggle-video', status_code=status.HTTP_200_OK)
async def toggle_video_in_playlist(
    playlist_id: UUID,
    body: ToggleVideoBody,
    current_user: FromDishka[CurrentUser],
    session_manager: FromDishka[SessionManagerProtocol],
) -> dict:
    """Toggle a video in the playlist (add if not present, remove if present)."""
    async with session_manager.get_session() as s:
        stmt = sa.select(Playlist).where(Playlist.id == playlist_id)
        result = await s.execute(stmt)
        pl = result.scalar_one_or_none()
        if pl is None:
            raise ModelNotFoundError(Playlist, model_id=playlist_id)
        if pl.user_id != current_user.id:
            raise PermissionDeniedError()

        vid_stmt = sa.select(Video).where(
            (Video.public_id == body.videoId) |
            (sa.cast(Video.id, sa.String) == body.videoId)
        )
        vid_result = await s.execute(vid_stmt)
        video = vid_result.scalar_one_or_none()
        if video is None:
            raise ModelNotFoundError(Video, model_id=body.videoId)

        pv_stmt = sa.select(PlaylistVideo).where(
            PlaylistVideo.playlist_id == pl.id,
            PlaylistVideo.video_id == video.id,
        )
        pv_result = await s.execute(pv_stmt)
        pv = pv_result.scalar_one_or_none()

        if pv is not None:
            await s.delete(pv)
            action = 'removed'
        else:
            new_pv = PlaylistVideo(playlist_id=pl.id, video_id=video.id, position=len(pl.videos))
            s.add(new_pv)
            action = 'added'

        await s.flush()
        # Reload
        reloaded = (await s.execute(sa.select(Playlist).where(Playlist.id == pl.id))).scalar_one()
        res = _format_playlist(reloaded)
        res['action'] = action
        return res


@router.delete('/{playlist_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: UUID,
    current_user: FromDishka[CurrentUser],
    session_manager: FromDishka[SessionManagerProtocol],
) -> None:
    async with session_manager.get_session() as s:
        stmt = sa.select(Playlist).where(Playlist.id == playlist_id)
        result = await s.execute(stmt)
        pl = result.scalar_one_or_none()
        if pl is None:
            raise ModelNotFoundError(Playlist, model_id=playlist_id)
        if pl.user_id != current_user.id:
            raise PermissionDeniedError()
        await s.delete(pl)
