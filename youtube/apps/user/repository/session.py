from youtube.settings import CoreAuthSettingsSchema
from uuid import UUID

from youtube.repositories import CacheRepositoryProtocol
from youtube.apps.user.exceptions import SessionInvalidError


class AuthSessionRepository:
    """
    Repository for managing authentication sessions.
    """

    def __init__(self, cache_repo: CacheRepositoryProtocol, settings: CoreAuthSettingsSchema) -> None:
        self.cache_repo = cache_repo
        self.settings = settings

    async def _make_key(self, session_id: str) -> str:
        return f'{self.settings.session_prefix}:{session_id}'

    async def create(self, session_id: str, user_id: UUID) -> None:
        await self.cache_repo.set(await self._make_key(session_id), str(user_id), expire=self.settings.session_ttl)

    async def get_and_refresh(self, session_id: str) -> UUID:
        key = await self._make_key(session_id)
        user_id_str = await self.cache_repo.get(key)
        if user_id_str is None:
            raise SessionInvalidError()
        await self.cache_repo.expire(key, self.settings.session_ttl)
        return UUID(user_id_str.decode() if isinstance(user_id_str, bytes) else user_id_str)

    async def delete(self, session_id: str) -> None:
        await self.cache_repo.clear(key=await self._make_key(session_id))
