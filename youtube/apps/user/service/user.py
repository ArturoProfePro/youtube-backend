import uuid
from typing import Optional
from uuid import UUID

import sqlalchemy as sa

from youtube.apps.user.repository import AuthSessionRepository, UserRepository
from youtube.apps.user.schemas import UserReadSchema, UserUpdateSchema
from youtube.repositories import StorageRepositoryProtocol


class UserService:
    def __init__(self, repository: UserRepository, storage_repository: StorageRepositoryProtocol) -> None:
        self.repository = repository
        self.storage_repository = storage_repository

    async def update_avatar(self, user_id: uuid.UUID, avatar_content: bytes, filename: str) -> str:
        user = await self.repository.get(user_id)
        if user.avatar:
            try:
                await self.storage_repository.delete(user.avatar)
            except Exception:
                pass
        unique_id = uuid.uuid4()
        avatar_path = f'avatars/{user_id}/{unique_id}.webp'
        await self.storage_repository.write(avatar_path, avatar_content)
        return avatar_path

    async def update_profile(
        self,
        user_id: uuid.UUID,
        username: str | None = None,
        email: str | None = None,
        avatar_content: bytes | None = None,
        avatar_filename: str | None = None,
        old_password: str | None = None,
        new_password: str | None = None,
        channel_data: dict | None = None,
    ) -> UserReadSchema:
        from youtube.services.cryptography.hasher import generate_hash, verify_hash
        import asyncio
        from youtube.apps.user.exceptions import InvalidCredentialsError, UserAlreadyExistsError

        if email:
            existing = await self.repository.get_by_login(email)
            if existing and existing.id != user_id:
                raise UserAlreadyExistsError(field='email')
        if username:
            existing = await self.repository.get_by_login(username)
            if existing and existing.id != user_id:
                raise UserAlreadyExistsError(field='username')

        update_data: dict = {}
        if username is not None:
            update_data['username'] = username
        if email is not None:
            update_data['email'] = email

        if avatar_content is not None and avatar_filename is not None:
            avatar_path = await self.update_avatar(user_id, avatar_content, avatar_filename)
            update_data['avatar'] = avatar_path

        if new_password is not None:
            if not old_password:
                raise InvalidCredentialsError(custom_message='Old password is required to set a new password')
            hashed_password = await self.repository.get_hashed_password(user_id)
            try:
                await asyncio.to_thread(verify_hash, hash=hashed_password, data=old_password)
            except Exception:
                raise InvalidCredentialsError() from None
            new_hashed_password = generate_hash(new_password)
            update_data['hashed_password'] = new_hashed_password

        if update_data:
            update_data['id'] = user_id
            await self.repository.update(UserUpdateSchema(**update_data))

        # Update channel if channel_data provided
        if channel_data:
            await self._update_channel(user_id, channel_data)

        return await self.repository.get(user_id)

    async def _update_channel(self, user_id: UUID, channel_data: dict) -> None:
        from youtube.apps.user.models import Channel
        from youtube.db import SessionManagerProtocol
        user = await self.repository.get_model_by_id(user_id)
        if user is None or user.channel is None:
            return

        ch = user.channel
        async with self.repository.session_manager.get_session() as s:
            stmt = sa.select(Channel).where(Channel.id == ch.id)
            result = await s.execute(stmt)
            channel = result.scalar_one_or_none()
            if channel is None:
                return
            if 'avatar' in channel_data and channel_data['avatar']:
                channel.avatar = channel_data['avatar']
            if 'banner' in channel_data and channel_data['banner']:
                channel.banner = channel_data['banner']
            if 'slug' in channel_data and channel_data['slug']:
                channel.slug = channel_data['slug']
            if 'description' in channel_data:
                channel.description = channel_data['description']

    async def toggle_like(self, user_id: UUID, video_public_id: str) -> bool:
        """Toggle like on a video. Returns True if liked, False if unliked."""
        from youtube.apps.video.models import Video, VideoLike

        async with self.repository.session_manager.get_session() as s:
            # Find video by publicId
            video_stmt = sa.select(Video).where(Video.public_id == video_public_id)
            result = await s.execute(video_stmt)
            video = result.scalar_one_or_none()
            if video is None:
                return False

            # Check existing like
            like_stmt = sa.select(VideoLike).where(
                VideoLike.user_id == user_id,
                VideoLike.video_id == video.id,
            )
            result = await s.execute(like_stmt)
            existing_like = result.scalar_one_or_none()

            if existing_like is not None:
                await s.delete(existing_like)
                return False
            else:
                new_like = VideoLike(user_id=user_id, video_id=video.id, is_like=True)
                s.add(new_like)
                return True

    async def get_watch_history(self, user_id: UUID) -> list[dict]:
        """Get user watch history as list of {video: ...} dicts."""
        from youtube.apps.video.models import Video, WatchHistory
        from youtube.apps.video.schemas.video import VideoListItemResponseSchema

        async with self.repository.session_manager.get_session() as s:
            stmt = (
                sa.select(WatchHistory)
                .where(WatchHistory.user_id == user_id)
                .order_by(WatchHistory.updated_at.desc() if hasattr(WatchHistory, 'updated_at') else WatchHistory.created_at.desc())
            )
            result = await s.execute(stmt)
            history_rows = result.scalars().all()

            items = []
            for row in history_rows:
                v = row.video
                if v is None:
                    continue
                channel_dict = None
                if v.channel:
                    ch = v.channel
                    channel_dict = {
                        'id': str(ch.id),
                        'slug': ch.slug,
                        'avatar': ch.avatar or '',
                        'isVerified': ch.is_verified,
                    }
                video_dict = {
                    'id': str(v.id),
                    'publicId': v.public_id,
                    'title': v.title or v.russian_title,
                    'thumbnailUrl': v.thumbnail_url or v.poster_url or '',
                    'videoFileName': v.video_file_name or '',
                    'maxResolution': v.max_resolution or '1080p',
                    'views': v.views or v.views_count or 0,
                    'isPublic': v.is_public,
                    'createdAt': v.created_at.isoformat() if v.created_at else '',
                    'channel': channel_dict,
                    'likes': [],
                    'comments': [],
                }
                items.append({'video': video_dict})
            return items

    async def add_to_watch_history(self, user_id: UUID, video_public_id: str) -> None:
        """Add a video to watch history (upsert)."""
        from youtube.apps.video.models import Video, WatchHistory

        async with self.repository.session_manager.get_session() as s:
            video_stmt = sa.select(Video).where(Video.public_id == video_public_id)
            result = await s.execute(video_stmt)
            video = result.scalar_one_or_none()
            if video is None:
                return

            history_stmt = sa.select(WatchHistory).where(
                WatchHistory.user_id == user_id,
                WatchHistory.video_id == video.id,
            )
            result = await s.execute(history_stmt)
            existing = result.scalar_one_or_none()
            if existing is None:
                new_entry = WatchHistory(user_id=user_id, video_id=video.id)
                s.add(new_entry)

    async def clear_watch_history(self, user_id: UUID) -> None:
        """Delete all watch history for user."""
        from youtube.apps.video.models import WatchHistory

        async with self.repository.session_manager.get_session() as s:
            stmt = sa.delete(WatchHistory).where(WatchHistory.user_id == user_id)
            await s.execute(stmt)
