import asyncio
from uuid import UUID
from typing import Optional

from argon2.exceptions import VerificationError, VerifyMismatchError
import jwt

from youtube.apps.user.exceptions import (
    InvalidCredentialsError,
    SessionExpiredError,
    UserAlreadyExistsError,
    UserBannedError,
)
from youtube.apps.user.models import User
from youtube.apps.user.repository import AuthSessionRepository, UserRepository
from youtube.apps.user.schemas import (
    ChangePasswordSchema,
    RegisterUserSchema,
    UserCreateSchema,
    UserCredentialsSchema,
    UserReadSchema,
    UserUpdateSchema,
)
from youtube.exceptions import NotAuthenticatedError
from youtube.services.cryptography.gen_session_id import generate_session_id
from youtube.services.cryptography.hasher import dummy_hash, generate_hash, verify_hash
from youtube.services.jwt_auth import create_access_token, create_refresh_token, decode_token


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        access_secret_key: str = 'yoursecretkeyherewhichisthirtytwobyteslong',
        refresh_secret_key: str | None = None,
        secret_key: str | None = None,
        session_repository: Optional[AuthSessionRepository] = None,
    ) -> None:
        self.repository = repository
        self.access_secret_key = secret_key or access_secret_key
        self.refresh_secret_key = refresh_secret_key or self.access_secret_key
        self.session_repository = session_repository

    @property
    def secret_key(self) -> str:
        return self.access_secret_key

    async def register_jwt(
        self,
        email: str,
        password: str,
        username: str | None = None,
        verification_token: str | None = None,
    ) -> tuple[User, str, str]:
        existing_user = await self.repository.get_model_by_email(email)
        if existing_user is not None:
            raise UserAlreadyExistsError(field='email')

        if username is None:
            username = email.split('@')[0]

        # Check username
        by_login = await self.repository.get_by_login(username)
        if by_login is not None:
            username = f"{username}_{generate_session_id(4)}"

        hashed_password = generate_hash(password)
        user = await self.repository.create_user_with_channel(
            username=username,
            email=email,
            hashed_password=hashed_password,
            verification_token=verification_token,
        )

        access_token = create_access_token(str(user.id), user.email, self.access_secret_key)
        refresh_token = create_refresh_token(str(user.id), self.refresh_secret_key)
        return user, access_token, refresh_token

    async def login_jwt(self, email: str, password: str) -> tuple[User, str, str]:
        user = await self.repository.get_model_by_email(email)
        if user is None:
            await asyncio.to_thread(dummy_hash, password)
            raise InvalidCredentialsError()

        hashed = str(user.hashed_password)
        try:
            await asyncio.to_thread(verify_hash, hash=hashed, data=password)
        except (VerifyMismatchError, VerificationError, ValueError):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise UserBannedError()

        access_token = create_access_token(str(user.id), user.email, self.access_secret_key)
        refresh_token = create_refresh_token(str(user.id), self.refresh_secret_key)
        return user, access_token, refresh_token

    async def refresh_jwt(self, refresh_token_str: str) -> tuple[User, str, str]:
        try:
            payload = decode_token(refresh_token_str, self.refresh_secret_key)
        except jwt.PyJWTError:
            raise NotAuthenticatedError()

        if payload.get('type') != 'refresh':
            raise NotAuthenticatedError()

        user_id_str = payload.get('sub')
        if not user_id_str:
            raise NotAuthenticatedError()

        user = await self.repository.get_model_by_id(UUID(user_id_str))
        if user is None or not user.is_active:
            raise NotAuthenticatedError()

        access_token = create_access_token(str(user.id), user.email, self.access_secret_key)
        new_refresh_token = create_refresh_token(str(user.id), self.refresh_secret_key)
        return user, access_token, new_refresh_token

    async def authenticate_jwt(self, token: str) -> UserReadSchema:
        try:
            payload = decode_token(token, self.access_secret_key)
        except jwt.PyJWTError:
            raise NotAuthenticatedError()

        user_id_str = payload.get('sub')
        if not user_id_str:
            raise NotAuthenticatedError()

        user = await self.repository.get_model_by_id(UUID(user_id_str))
        if user is None:
            raise NotAuthenticatedError()
        if not user.is_active:
            raise UserBannedError()
        return UserReadSchema.model_validate(user)


    # Legacy session compatibility methods
    async def register_user(self, user: RegisterUserSchema) -> str:
        if await self.repository.get_by_login(user.email):
            raise UserAlreadyExistsError(field='email')
        if await self.repository.get_by_login(user.username):
            raise UserAlreadyExistsError(field='username')

        hashed_password = generate_hash(user.password.get_secret_value())
        session_id = await asyncio.to_thread(generate_session_id, 32)

        new_user = await self.repository.create_user_with_channel(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password,
        )
        if self.session_repository:
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
        if self.session_repository:
            await self.session_repository.create(session_id, user.id)
        return session_id

    async def authenticate_user(self, session_id: str) -> UserReadSchema:
        if not self.session_repository:
            raise SessionExpiredError()
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
        if self.session_repository:
            await self.session_repository.delete(session_id)
