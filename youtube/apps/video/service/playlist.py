from uuid import UUID

from youtube.apps.video.repository.playlist import PlaylistRepository
from youtube.apps.video.repository.video import VideoRepository
from youtube.apps.video.schemas.playlist import (
    PlaylistCreateSchema,
    PlaylistReadSchema,
    PlaylistUpdateSchema,
    PlaylistUpdateDataSchema,
)
from youtube.exceptions import PermissionDeniedError


class PlaylistService:
    def __init__(self, playlist_repo: PlaylistRepository, video_repo: VideoRepository) -> None:
        self.playlist_repo = playlist_repo
        self.video_repo = video_repo

    async def _check_owner(self, playlist_id: UUID, user_id: UUID) -> None:
        owner_id = await self.playlist_repo.get_owner_id(playlist_id)
        if owner_id != user_id:
            raise PermissionDeniedError()

    async def create_playlist(self, user_id: UUID, data: PlaylistCreateSchema) -> PlaylistReadSchema:
        return await self.playlist_repo.create_playlist(data, user_id)

    async def get_playlist(self, playlist_id: UUID, user_id: UUID | None = None) -> PlaylistReadSchema:
        is_private = await self.playlist_repo.is_private(playlist_id)
        if is_private:
            if user_id is None:
                raise PermissionDeniedError()
            await self._check_owner(playlist_id, user_id)
        return await self.playlist_repo.get_by_id(playlist_id)

    async def get_my_playlists(self, user_id: UUID) -> list[PlaylistReadSchema]:
        return await self.playlist_repo.get_user_playlists(user_id)

    async def update_playlist(
        self, playlist_id: UUID, user_id: UUID, data: PlaylistUpdateDataSchema
    ) -> PlaylistReadSchema:
        await self._check_owner(playlist_id, user_id)
        update_schema = PlaylistUpdateSchema(id=playlist_id, **data.model_dump(exclude_unset=True))
        return await self.playlist_repo.update_playlist(playlist_id, update_schema)

    async def delete_playlist(self, playlist_id: UUID, user_id: UUID) -> None:
        await self._check_owner(playlist_id, user_id)
        await self.playlist_repo.delete_playlist(playlist_id)

    async def add_video(
        self, playlist_id: UUID, user_id: UUID, video_slug: str, position: int | None = None
    ) -> PlaylistReadSchema:
        await self._check_owner(playlist_id, user_id)
        video = await self.video_repo.get_by_slug(video_slug)
        return await self.playlist_repo.add_video(playlist_id, video.id, position)

    async def remove_video(self, playlist_id: UUID, user_id: UUID, video_slug: str) -> PlaylistReadSchema:
        await self._check_owner(playlist_id, user_id)
        video = await self.video_repo.get_by_slug(video_slug)
        return await self.playlist_repo.remove_video(playlist_id, video.id)

    async def reorder_video(
        self, playlist_id: UUID, user_id: UUID, video_slug: str, new_position: int
    ) -> PlaylistReadSchema:
        await self._check_owner(playlist_id, user_id)
        video = await self.video_repo.get_by_slug(video_slug)
        return await self.playlist_repo.reorder_video(playlist_id, video.id, new_position)
