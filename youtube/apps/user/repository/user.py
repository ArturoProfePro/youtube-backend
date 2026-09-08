import sqlalchemy
from uuid import UUID
from youtube.schemas import BasicAuthSchema
from youtube.exceptions import ModelNotFoundError  # noqa: I001
from youtube.repositories import DbCrudRepository
from youtube.apps.user.schemas import (
    UserReadSchema,
    UserCreateSchema,
    UserUpdateSchema,
    UserInDbSchema,
    UserCredentialsSchema,
)
from youtube.apps.user.models import User


class UserRepository(
    DbCrudRepository[
        User,
        UserReadSchema,
        UserCreateSchema,
        UserUpdateSchema,
    ]
):
    """
    Repository protocol for operations on users.
    """

    async def get_by_login(self, login: str) -> UserInDbSchema | None:
        """
        Login a user.
        """
        async with self.session_manager.get_session() as s:
            stmt = self.select().where((User.email == login) | (User.username == login))
            result = await s.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None:
                return None
            return UserInDbSchema.model_validate(user)

    async def get_hashed_password(self, id: UUID) -> str:
        """
        Get a user by id.
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
