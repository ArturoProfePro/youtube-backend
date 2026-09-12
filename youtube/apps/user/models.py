import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from youtube.db import Base
from youtube.models import TimestampMixin

if TYPE_CHECKING:
    from youtube.apps.video.models import Video, VideoLike, WatchHistory, Playlist


class User(Base, TimestampMixin):
    __tablename__ = 'user'

    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    channel: Mapped['Channel | None'] = relationship(
        'Channel',
        back_populates='user',
        uselist=False,
        lazy='selectin',
        cascade='all, delete-orphan',
    )
    subscriptions: Mapped[list['Subscription']] = relationship(
        'Subscription',
        back_populates='user',
        foreign_keys='Subscription.user_id',
        lazy='selectin',
        cascade='all, delete-orphan',
    )
    likes: Mapped[list['VideoLike']] = relationship(
        'VideoLike',
        back_populates='user',
        foreign_keys='VideoLike.user_id',
        lazy='selectin',
        cascade='all, delete-orphan',
    )
    watch_history: Mapped[list['WatchHistory']] = relationship(
        'WatchHistory',
        back_populates='user',
        foreign_keys='WatchHistory.user_id',
        lazy='selectin',
        cascade='all, delete-orphan',
    )
    playlists: Mapped[list['Playlist']] = relationship(
        'Playlist',
        back_populates='user',
        foreign_keys='Playlist.user_id',
        lazy='selectin',
        cascade='all, delete-orphan',
    )


class Channel(Base, TimestampMixin):
    __tablename__ = 'channel'

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('user.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default='', server_default='')
    avatar: Mapped[str] = mapped_column(String(1024), default='', server_default='')
    banner: Mapped[str] = mapped_column(String(1024), default='', server_default='')
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')

    user: Mapped['User'] = relationship('User', back_populates='channel', lazy='selectin')
    videos: Mapped[list['Video']] = relationship(
        'Video',
        back_populates='channel',
        lazy='selectin',
        cascade='all, delete-orphan',
    )
    subscribers: Mapped[list['Subscription']] = relationship(
        'Subscription',
        back_populates='channel',
        foreign_keys='Subscription.channel_id',
        lazy='selectin',
        cascade='all, delete-orphan',
    )


class Subscription(Base, TimestampMixin):
    __tablename__ = 'subscription'

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    channel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('channel.id', ondelete='CASCADE'), nullable=False)

    user: Mapped['User'] = relationship('User', back_populates='subscriptions', foreign_keys=[user_id], lazy='selectin')
    channel: Mapped['Channel'] = relationship('Channel', back_populates='subscribers', foreign_keys=[channel_id], lazy='selectin')

    __table_args__ = (UniqueConstraint('user_id', 'channel_id', name='uq_user_channel_subscription'),)
