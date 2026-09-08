from youtube.apps.user.models import User
import uuid

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from youtube.db import Base
from youtube.models import TimestampMixin, CreatedAtMixin
from youtube.utils.slugify import generate_slug


video_tags_association = sa.Table(
    'video_tags_association',
    Base.metadata,
    sa.Column('video_id', sa.ForeignKey('video.id', ondelete='CASCADE'), primary_key=True),
    sa.Column('tag_id', sa.ForeignKey('video_tag.id', ondelete='CASCADE'), primary_key=True),
)


class Video(Base, TimestampMixin):
    """
    SQLAlchemy model representing a parsed video.
    """

    __tablename__ = 'video'

    slug: Mapped[str] = mapped_column(sa.String(512), nullable=False, unique=True)
    source_url: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    external_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)

    russian_title: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    official_title: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    other_titles: Mapped[list[str]] = mapped_column(sa.JSON, default=list, server_default='[]')
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    poster_url: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    is_censored: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default='false')

    duration: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    studio: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    translation_types: Mapped[list[str]] = mapped_column(sa.JSON, default=list, server_default='[]')

    likes_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    dislikes_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    views_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')

    likes: Mapped[list['VideoLike']] = relationship(
        'VideoLike',
        back_populates='video',
        cascade='all, delete-orphan',
        lazy='raise',
    )

    watch_history: Mapped[list['WatchHistory']] = relationship(
        'WatchHistory',
        back_populates='video',
        cascade='all, delete-orphan',
        lazy='raise',
    )

    tags: Mapped[list['VideoTag']] = relationship(
        'VideoTag',
        back_populates='videos',
        secondary=video_tags_association,
        lazy='selectin',
    )
    direct_sources: Mapped[list['VideoDirectSource']] = relationship(
        'VideoDirectSource',
        back_populates='video',
        cascade='all, delete-orphan',
        lazy='selectin',
    )
    external_players: Mapped[list['VideoExternalPlayer']] = relationship(
        'VideoExternalPlayer',
        back_populates='video',
        cascade='all, delete-orphan',
        lazy='selectin',
    )

    __table_args__ = (sa.UniqueConstraint('slug', 'source_url', 'external_id', name='uq_video_source_external'),)


@event.listens_for(Video, 'before_insert')
@event.listens_for(Video, 'before_update')
def video_before_insert(mapper, connection, target: Video):
    if target.slug:
        return
    slug: str = target.russian_title
    if target.official_title:
        slug = f'{slug}-{target.official_title}'
    target.slug = generate_slug(slug)


class VideoLike(Base, CreatedAtMixin):
    """
    SQLAlchemy model representing a like on a video.
    """

    __tablename__ = 'video_likes'
    video_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('video.id', ondelete='CASCADE'),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    )
    is_like: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True,
        server_default='true',
    )

    user: Mapped[User] = relationship('User', lazy='joined')
    video: Mapped[Video] = relationship('Video', back_populates='likes')


class WatchHistory(Base, TimestampMixin):
    __tablename__ = 'watch_history'

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True,
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('video.id', ondelete='CASCADE'),
        primary_key=True,
    )

    progress_seconds: Mapped[int] = mapped_column(default=0, nullable=False)

    user: Mapped[User] = relationship('User', lazy='joined')
    video: Mapped[Video] = relationship('Video', back_populates='watch_history')

    __table_args__ = (
        sa.UniqueConstraint(
            'user_id',
            'video_id',
            name='uq_watch_history_user_video',
        ),
    )


class TagCategory(Base):
    """
    SQLAlchemy model representing a tag category.
    """

    __tablename__ = 'tag_category'

    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)

    tags: Mapped[list['VideoTag']] = relationship(
        'VideoTag',
        back_populates='category',
        cascade='all, delete-orphan',
        lazy='selectin',
    )


class VideoTag(Base):
    """
    SQLAlchemy model representing a tag associated with a video.
    """

    __tablename__ = 'video_tag'

    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(sa.ForeignKey('tag_category.id', ondelete='CASCADE'))

    category: Mapped[TagCategory] = relationship('TagCategory', back_populates='tags')

    videos: Mapped[list[Video]] = relationship(
        'Video',
        back_populates='tags',
        secondary=video_tags_association,
        lazy='raise',
    )

    __table_args__ = (sa.UniqueConstraint('name', 'category_id', name='uq_video_tag_name_category'),)


@event.listens_for(VideoTag, 'before_insert')
@event.listens_for(VideoTag, 'before_update')
def video_tag_before_insert(mapper, connection, target: VideoTag):
    if not target.slug and target.name:
        target.slug = generate_slug(target.name)


class VideoDirectSource(Base):
    """
    SQLAlchemy model representing a direct video streaming source.
    """

    __tablename__ = 'video_direct_source'

    video_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('video.id', ondelete='CASCADE'),
        nullable=False,
    )
    quality: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    source_url: Mapped[str] = mapped_column(sa.String(2048), nullable=False)
    video_type: Mapped[str] = mapped_column(sa.String(50), default='mp4', server_default='mp4')
    voiceover: Mapped[str] = mapped_column(sa.String(100), default='subs', server_default='subs')

    video: Mapped[Video] = relationship('Video', back_populates='direct_sources')


class VideoExternalPlayer(Base):
    """
    SQLAlchemy model representing an external embedded video player.
    """

    __tablename__ = 'video_external_player'

    video_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('video.id', ondelete='CASCADE'),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    embed_url: Mapped[str] = mapped_column(sa.String(2048), nullable=False)
    quality: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    player_type: Mapped[str] = mapped_column(sa.String(100), default='subs', server_default='subs')
    voiceover: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)

    video: Mapped[Video] = relationship('Video', back_populates='external_players')


class Playlist(Base, TimestampMixin):
    """
    SQLAlchemy model representing a user's video playlist.
    """

    __tablename__ = 'playlist'

    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_private: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default='true')
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
    )

    user: Mapped[User] = relationship('User', lazy='raise')
    videos: Mapped[list['PlaylistVideo']] = relationship(
        'PlaylistVideo',
        back_populates='playlist',
        cascade='all, delete-orphan',
        order_by='PlaylistVideo.position',
        lazy='selectin',
    )


class PlaylistVideo(Base, CreatedAtMixin):
    """
    SQLAlchemy association model representing a video in a playlist with its position.
    """

    __tablename__ = 'playlist_video'

    playlist_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('playlist.id', ondelete='CASCADE'),
        nullable=False,
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('video.id', ondelete='CASCADE'),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')

    playlist: Mapped[Playlist] = relationship('Playlist', back_populates='videos')
    video: Mapped[Video] = relationship('Video', lazy='selectin')

    __table_args__ = (
        sa.UniqueConstraint('playlist_id', 'video_id', name='uq_playlist_video_playlist_video'),
    )
