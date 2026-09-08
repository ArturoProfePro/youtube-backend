from typing import Optional
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from youtube.apps.user.models import User
from youtube.db import Base
from youtube.models import TimestampMixin


class Comment(Base, TimestampMixin):
    __tablename__ = 'comments'

    content: Mapped[str] = MappedColumn(sa.Text, nullable=False)

    video_id: Mapped[UUID] = MappedColumn(index=True, nullable=False)
    user_id: Mapped[UUID] = MappedColumn(sa.ForeignKey('user.id'), nullable=False)
    parent_id: Mapped[UUID | None] = MappedColumn(sa.ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)

    likes_count: Mapped[int] = MappedColumn(sa.Integer, nullable=False, default=0)
    dislikes_count: Mapped[int] = MappedColumn(sa.Integer, nullable=False, default=0)

    user: Mapped[User] = relationship('User', lazy='noload')


class CommentLike(Base, TimestampMixin):
    __tablename__ = 'comment_likes'

    comment_id: Mapped[UUID] = MappedColumn(sa.ForeignKey('comments.id'), nullable=False)
    user_id: Mapped[UUID] = MappedColumn(sa.ForeignKey('user.id'), nullable=False)
