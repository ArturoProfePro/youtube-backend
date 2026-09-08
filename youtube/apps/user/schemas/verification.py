from pydantic import EmailStr, Field

from youtube.schemas import BaseSchema


class SendVerificationRequestSchema(BaseSchema):
    """
    Verification request schema.
    """

    email: EmailStr


class VerifyEmailRequestSchema(BaseSchema):
    """
    Verify email request schema.
    """

    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r'^\d{6}$')
