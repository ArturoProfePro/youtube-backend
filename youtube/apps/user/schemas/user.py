from pydantic import EmailStr

from youtube.schemas import BaseSchema, CreateSchema, ReadSchema, UpdateSchema


class BaseUserSchema(BaseSchema):
    """
    Base user schema.
    """

    username: str
    email: EmailStr
    is_active: bool
    is_superuser: bool
    is_verified: bool
    avatar: str | None = None


class UserReadSchema(ReadSchema, BaseUserSchema):
    """
    User read schema.
    """

    pass


class UserCreateSchema(BaseUserSchema, CreateSchema):
    """
    User create schema.
    """

    hashed_password: str


class UserUpdateSchema(UpdateSchema):
    """
    User update schema.
    """

    username: str | None = None
    email: EmailStr | None = None
    hashed_password: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    is_verified: bool | None = None
    avatar: str | None = None


class UserInDbSchema(BaseUserSchema, ReadSchema):
    """
    User authentication data schema.
    """

    hashed_password: str
