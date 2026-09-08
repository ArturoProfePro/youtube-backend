from typing import override, Self
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from youtube.apps.video.models import Playlist, PlaylistVideo
from youtube.apps.video.schemas.playlist import (
    PlaylistCreateSchema,
    PlaylistReadSchema,
    PlaylistUpdateSchema,
)
from youtube.db import SessionManagerProtocol
from youtube.exceptions import ModelNotFoundError
from youtube.repositories.crud import DbCrudRepository


class PlaylistRepository(DbCrudRepository[Playlist, PlaylistReadSchema, PlaylistCreateSchema, PlaylistUpdateSchema]):
    @classmethod
    @override
    def select(cls):
        return (
            super()
            .select()
            .options(
                selectinload(Playlist.videos).selectinload(PlaylistVideo.video),
            )
        )

    async def create_playlist(self, create_object: PlaylistCreateSchema, user_id: UUID) -> PlaylistReadSchema:
        async with self.session_manager.get_session() as s:
            playlist = Playlist(
                title=create_object.title,
                description=create_object.description,
                is_private=create_object.is_private,
                user_id=user_id,
            )
            s.add(playlist)
            await s.flush()
            await s.refresh(playlist, ['videos'])
            return self.model_validate(playlist)

    async def get_by_id(self, playlist_id: UUID) -> PlaylistReadSchema:
        return await self.get(playlist_id)

    async def get_user_playlists(self, user_id: UUID) -> list[PlaylistReadSchema]:
        async with self.session_manager.get_session() as session:
            stmt = (
                self.select()
                .where(Playlist.user_id == user_id)
                .order_by(Playlist.updated_at.desc())
            )
            result = await session.execute(stmt)
            playlists = result.scalars().all()
            return [self.model_validate(p) for p in playlists]

    async def update_playlist(self, playlist_id: UUID, update_object: PlaylistUpdateSchema) -> PlaylistReadSchema:
        async with self.session_manager.get_session() as s:
            stmt = self.select().where(Playlist.id == playlist_id)
            playlist = (await s.execute(stmt)).scalar_one_or_none()
            if playlist is None:
                raise ModelNotFoundError(Playlist, model_id=playlist_id)

            update_data = update_object.model_dump(exclude_unset=True)
            for key, val in update_data.items():
                setattr(playlist, key, val)

            await s.flush()
            await s.refresh(playlist, ['videos'])
            return self.model_validate(playlist)

    async def delete_playlist(self, playlist_id: UUID) -> None:
        await self.delete([playlist_id])

    async def add_video(self, playlist_id: UUID, video_id: UUID, position: int | None = None) -> PlaylistReadSchema:
        async with self.session_manager.get_session() as session:
            if position is None:
                max_pos_stmt = sa.select(sa.func.coalesce(sa.func.max(PlaylistVideo.position), -1)).where(
                    PlaylistVideo.playlist_id == playlist_id
                )
                max_pos = (await session.execute(max_pos_stmt)).scalar_one()
                position = max_pos + 1

            pv = PlaylistVideo(playlist_id=playlist_id, video_id=video_id, position=position)
            session.add(pv)
            await session.flush()

            stmt = self.select().where(Playlist.id == playlist_id)
            result = await session.execute(stmt)
            playlist = result.scalar_one()
            return self.model_validate(playlist)

    async def remove_video(self, playlist_id: UUID, video_id: UUID) -> PlaylistReadSchema:
        async with self.session_manager.get_session() as session:
            stmt = sa.select(PlaylistVideo).where(
                PlaylistVideo.playlist_id == playlist_id,
                PlaylistVideo.video_id == video_id,
            )
            result = await session.execute(stmt)
            pv = result.scalar_one_or_none()
            if pv is None:
                raise ModelNotFoundError(PlaylistVideo, message='Video not found in playlist')
            await session.delete(pv)
            await session.flush()

            stmt = self.select().where(Playlist.id == playlist_id)
            result = await session.execute(stmt)
            playlist = result.scalar_one()
            return self.model_validate(playlist)

    async def reorder_video(self, playlist_id: UUID, video_id: UUID, new_position: int) -> PlaylistReadSchema:
        async with self.session_manager.get_session() as session:
            stmt = sa.select(PlaylistVideo).where(
                PlaylistVideo.playlist_id == playlist_id,
                PlaylistVideo.video_id == video_id,
            )
            result = await session.execute(stmt)
            pv = result.scalar_one_or_none()
            if pv is None:
                raise ModelNotFoundError(PlaylistVideo, message='Video not found in playlist')

            pv.position = new_position
            await session.flush()

            stmt = self.select().where(Playlist.id == playlist_id)
            result = await session.execute(stmt)
            playlist = result.scalar_one()
            return self.model_validate(playlist)

    async def get_owner_id(self, playlist_id: UUID) -> UUID:
        async with self.session_manager.get_session() as session:
            stmt = sa.select(Playlist.user_id).where(Playlist.id == playlist_id)
            result = await session.execute(stmt)
            owner_id = result.scalar_one_or_none()
            if owner_id is None:
                raise ModelNotFoundError(Playlist, model_id=playlist_id)
            return owner_id

    async def is_private(self, playlist_id: UUID) -> bool:
        async with self.session_manager.get_session() as session:
            stmt = sa.select(Playlist.is_private).where(Playlist.id == playlist_id)
            result = await session.execute(stmt)
            val = result.scalar_one_or_none()
            if val is None:
                raise ModelNotFoundError(Playlist, model_id=playlist_id)
            return val
