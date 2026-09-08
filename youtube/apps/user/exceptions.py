from typing import Self

from youtube.exceptions import (
    BusinessLogicException,
    ModelAlreadyExistsError,
    NotAuthenticatedError,
    ValidationError,
)


class InvalidCredentialsError(BusinessLogicException):
    """
    Error raised when invalid credentials are provided.
    """

    def __init__(self, *args, custom_message: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_message = custom_message

    @property
    def message(self: Self) -> str:
        return self.custom_message or 'Invalid credentials'



class UserAlreadyExistsError(ModelAlreadyExistsError):
    """
    Error raised when  user with that username or email already exists.
    """

    @property
    def message(self: Self) -> str:
        return f'User with {self.field} already exists'


class UserBannedError(BusinessLogicException):
    """
    Error raised when is_active is false.
    """

    @property
    def message(self: Self) -> str:
        return 'User is banned'


class VerificationCodeInvalidError(BusinessLogicException):
    """
    Error raised when verification code is invalid.
    """

    @property
    def message(self: Self) -> str:
        return 'Verification code is invalid'


class PasswordValidationError(ValidationError):
    """
    Error raised when password validation fails.
    """

    pass


class SessionExpiredError(NotAuthenticatedError):
    """
    Error raised when user with that token is not found.
    """

    @property
    def message(self: Self) -> str:
        return 'Session expired'


class SessionInvalidError(NotAuthenticatedError):
    @property
    def message(self: Self) -> str:
        return 'Session invalid'
