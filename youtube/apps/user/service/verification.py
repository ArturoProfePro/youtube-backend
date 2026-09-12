import secrets

from youtube.apps.user.repository import UserRepository
from youtube.apps.user.schemas import UserUpdateSchema
from youtube.repositories import CacheRepositoryProtocol
from youtube.settings import CoreVerificationSettingsSchema

from youtube.apps.user.exceptions import VerificationCodeInvalidError


class EmailVerificationService:
    def __init__(
        self,
        repository: UserRepository,
        cache_repository: CacheRepositoryProtocol,
        settings: CoreVerificationSettingsSchema,
    ):
        self.repository = repository
        self.cache_repository = cache_repository

        self.cache_prefix = settings.cache_prefix
        self.code_ttl = settings.code_ttl
        self.max_attempts = settings.max_attempts

    async def generate_and_store_code(self, email: str) -> str:
        code = f'{secrets.randbelow(1_000_000):06d}'
        code_key = f'{self.cache_prefix}:{email}:code'
        attempts_key = f'{self.cache_prefix}:{email}:attempts'

        await self.cache_repository.set(code_key, code, expire=self.code_ttl)
        await self.cache_repository.incr(attempts_key, 0)
        await self.cache_repository.expire(attempts_key, self.code_ttl)

        return code

    async def verify(self, email: str, code: str) -> None:
        code_key = f'{self.cache_prefix}:{email}:code'
        attempts_key = f'{self.cache_prefix}:{email}:attempts'

        attempts = int(await self.cache_repository.get(attempts_key) or 0)

        stored_code = await self.cache_repository.get(code_key)
        if stored_code is None:
            raise VerificationCodeInvalidError()

        if attempts >= self.max_attempts:
            raise VerificationCodeInvalidError()
        if stored_code != code:
            await self.cache_repository.incr(attempts_key, 1)
            await self.cache_repository.expire(attempts_key, self.code_ttl)
            raise VerificationCodeInvalidError()

        await self.cache_repository.clear(key=code_key)
        await self.cache_repository.clear(key=attempts_key)
        user = await self.repository.get_by_email(email)
        await self.repository.update(UserUpdateSchema(id=user.id, is_verified=True))

    async def verify_by_token(self, token: str):
        """Verify email using a JWT token stored on the user row."""
        user = await self.repository.get_model_by_token(token)
        if user is None:
            raise VerificationCodeInvalidError()
        await self.repository.update(
            UserUpdateSchema(id=user.id, is_verified=True, verification_token=None)
        )
        return user
