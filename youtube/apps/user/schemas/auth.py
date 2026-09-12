from typing import Annotated

from pydantic import AfterValidator, EmailStr, Field, SecretStr

from youtube.apps.user.exceptions import PasswordValidationError
from youtube.schemas import BaseSchema

from .user import UserReadSchema


def validate_password_rules(value: SecretStr) -> SecretStr:
    raw = value.get_secret_value()

    if not any(char.isupper() for char in raw):
        raise PasswordValidationError(
            custom_message='Password must contain at least one uppercase letter', field='password'
        )
    if not any(char.islower() for char in raw):
        raise PasswordValidationError(
            custom_message='Password must contain at least one lowercase letter', field='password'
        )
    if not any(char.isdigit() for char in raw):
        raise PasswordValidationError(custom_message='Password must contain at least one digit', field='password')

    if len(raw) < 8:
        raise PasswordValidationError(custom_message='Password must be at least 8 characters long', field='password')

    return value


StrongPassword = Annotated[
    SecretStr,
    Field(min_length=8, max_length=30),
    AfterValidator(validate_password_rules),
]


class RegisterUserSchema(BaseSchema):
    """
    User register schema.
    """

    username: str
    email: EmailStr
    password: StrongPassword


class UserCredentialsSchema(BaseSchema):
    """
    Authentication schema.
    """

    login: str
    password: StrongPassword


class TokenAuthSchema(BaseSchema):
    """
    Token authentication schema.
    """

    access_token: str
    token_type: str


class TokenAuthResponseSchema(TokenAuthSchema):
    """
    Token authentication response schema.
    """

    user: UserReadSchema


class ChangePasswordSchema(BaseSchema):
    """
    Schema for changing user password.
    """

    old_password: StrongPassword
    new_password: StrongPassword
