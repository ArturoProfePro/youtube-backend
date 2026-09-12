from uuid import UUID
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from youtube.exceptions import ModelNotFoundError
from youtube.repositories import DbCrudRepository
from youtube.apps.user.schemas import (
    UserReadSchema,
    UserCreateSchema,
    UserUpdateSchema,
    UserInDbSchema,
)
from youtube.apps.user.models import User, Channel, Subscription
from youtube.utils.slugify import generate_slug


class UserRepository(
    DbCrudRepository[
        User,
        UserReadSchema,
        UserCreateSchema,
        UserUpdateSchema,
    ]
):
    """
    Repository for operations on users.
    """

    async def get_by_login(self, login: str) -> UserInDbSchema | None:
        """
        Get user by email or username.
        """
        async with self.session_manager.get_session() as s:
            stmt = self.select().where((User.email == login) | (User.username == login))
            result = await s.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None:
                return None
            return UserInDbSchema.model_validate(user)

    async def get_model_by_email(self, email: str) -> Optional[User]:
        async with self.session_manager.get_session() as s:
            stmt = (
                sa.select(User)
                .where(User.email == email)
                .options(selectinload(User.channel))
            )
            result = await s.execute(stmt)
            return result.scalar_one_or_none()

    async def get_model_by_id(self, user_id: UUID) -> Optional[User]:
        async with self.session_manager.get_session() as s:
            stmt = (
                sa.select(User)
                .where(User.id == user_id)
                .options(
                    selectinload(User.channel),
                    selectinload(User.subscriptions).selectinload(Subscription.channel),
                    selectinload(User.likes),
                    selectinload(User.watch_history),
                )
            )
            result = await s.execute(stmt)
            return result.scalar_one_or_none()

    async def get_model_by_token(self, token: str) -> Optional[User]:
        async with self.session_manager.get_session() as s:
            stmt = (
                sa.select(User)
                .where(User.verification_token == token)
                .options(selectinload(User.channel))
            )
            result = await s.execute(stmt)
            return result.scalar_one_or_none()

    async def get_hashed_password(self, id: UUID) -> str:
        """
        Get a user's hashed password by id.
        """
        async with self.session_manager.get_session() as s:
            user = await s.get_one(User, id)
            return str(user.hashed_password)

    async def get_by_email(self, email: str) -> UserReadSchema:
        """
        Get a user by email.
        """
        async with self.session_manager.get_session() as s:
            stmt = self.select().where(User.email == email)
            result = await s.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None:
                raise ModelNotFoundError(User, model_id=email)
            return UserReadSchema.model_validate(user)

    async def create_user_with_channel(
        self,
        username: str,
        email: str,
        hashed_password: str,
        verification_token: str | None = None,
    ) -> User:
        """
        Create a new user and an associated default channel.
        """
        async with self.session_manager.get_session() as s:
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                is_active=True,
                is_superuser=False,
                is_verified=False,
                verification_token=verification_token,
            )
            s.add(user)
            await s.flush()

            # Generate channel slug
            slug = generate_slug(username) or f'user-{str(user.id)[:8]}'
            # Verify slug uniqueness
            check_stmt = sa.select(Channel).where(Channel.slug == slug)
            existing_channel = (await s.execute(check_stmt)).scalar_one_or_none()
            if existing_channel:
                slug = f'{slug}-{str(user.id)[:4]}'

            channel = Channel(
                user_id=user.id,
                slug=slug,
                description='',
                avatar='',
                banner='',
                is_verified=False,
            )
            s.add(channel)
            await s.flush()

            # Refresh user with channel loaded
            stmt = (
                sa.select(User)
                .where(User.id == user.id)
                .options(selectinload(User.channel))
            )
            res = await s.execute(stmt)
            return res.scalar_one()
