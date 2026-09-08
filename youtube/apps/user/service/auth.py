from uuid import UUID
import asyncio

from argon2.exceptions import VerificationError, VerifyMismatchError

from youtube.apps.user.exceptions import (
    InvalidCredentialsError,
    SessionExpiredError,
    UserAlreadyExistsError,
    UserBannedError,
)
from youtube.apps.user.repository import AuthSessionRepository, UserRepository
from youtube.apps.user.schemas import (
    RegisterUserSchema,
    UserCreateSchema,
    UserCredentialsSchema,
    UserReadSchema,
    ChangePasswordSchema,
    UserUpdateSchema,
)
from youtube.services.cryptography.gen_session_id import generate_session_id
from youtube.services.cryptography.hasher import dummy_hash, generate_hash, verify_hash


class AuthService:
    def __init__(self, repository: UserRepository, session_repository: AuthSessionRepository) -> None:
        self.repository = repository
        self.session_repository = session_repository

    async def register_user(self, user: RegisterUserSchema) -> str:
        if await self.repository.get_by_login(user.email):
            raise UserAlreadyExistsError(field='email')
        if await self.repository.get_by_login(user.username):
            raise UserAlreadyExistsError(field='username')

        hashed_password = generate_hash(user.password.get_secret_value())
        session_id = await asyncio.to_thread(generate_session_id, 32)

        new_user = await self.repository.create(
            UserCreateSchema(
                username=user.username,
                email=user.email,
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=False,
                is_verified=False,
            )
        )
        await self.session_repository.create(session_id, new_user.id)
        return session_id

    async def login_user(self, auth: UserCredentialsSchema) -> str:
        user = await self.repository.get_by_login(auth.login)
        if user is None:
            await asyncio.to_thread(dummy_hash, auth.password.get_secret_value())
            raise InvalidCredentialsError() from None

        password = await self.repository.get_hashed_password(user.id)
        try:
            await asyncio.to_thread(verify_hash, hash=password, data=auth.password.get_secret_value())
        except (VerifyMismatchError, VerificationError, ValueError):
            raise InvalidCredentialsError() from None

        session_id = await asyncio.to_thread(generate_session_id, 32)

        await self.session_repository.create(session_id, user.id)
        return session_id

    async def authenticate_user(self, session_id: str) -> UserReadSchema:
        user_id = await self.session_repository.get_and_refresh(session_id)

        user = await self.repository.get(user_id)
        if user.is_active is False:
            raise UserBannedError()
        return UserReadSchema.model_validate(user)

    async def change_password(self, user_id: str, data: ChangePasswordSchema) -> None:
        user = await self.repository.get(UUID(user_id))
        password = await self.repository.get_hashed_password(user.id)

        try:
            await asyncio.to_thread(verify_hash, hash=password, data=data.old_password.get_secret_value())
        except (VerifyMismatchError, VerificationError, ValueError):
            raise InvalidCredentialsError() from None

        new_hashed_password = generate_hash(data.new_password.get_secret_value())
        await self.repository.update(UserUpdateSchema(id=user.id, hashed_password=new_hashed_password))

    async def logout(self, session_id: str) -> None:
        await self.session_repository.delete(session_id)
