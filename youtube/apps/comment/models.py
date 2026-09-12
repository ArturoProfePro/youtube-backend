from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from youtube.apps.user.models import User
from youtube.db import Base
from youtube.models import TimestampMixin

if TYPE_CHECKING:
    from youtube.apps.video.models import Video


class Comment(Base, TimestampMixin):
    __tablename__ = 'comments'

    text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    content: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    video_id: Mapped[UUID] = mapped_column(sa.ForeignKey('video.id', ondelete='CASCADE'), index=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(sa.ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)

    likes_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0, server_default='0')
    dislikes_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0, server_default='0')

    user: Mapped[User] = relationship('User', lazy='selectin')
    video: Mapped['Video'] = relationship('Video', back_populates='comments', lazy='noload')


class CommentLike(Base, TimestampMixin):
    __tablename__ = 'comment_likes'

    comment_id: Mapped[UUID] = mapped_column(sa.ForeignKey('comments.id', ondelete='CASCADE'), nullable=False)
    user_id: Mapped[UUID] = mapped_column(sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
