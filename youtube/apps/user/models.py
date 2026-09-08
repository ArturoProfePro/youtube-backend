from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from youtube.db import Base
from youtube.models import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = 'user'

    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True)
