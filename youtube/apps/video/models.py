import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from youtube.apps.user.models import User, Channel
from youtube.db import Base
from youtube.models import CreatedAtMixin, TimestampMixin
from youtube.utils.slugify import generate_slug

if TYPE_CHECKING:
    from youtube.apps.comment.models import Comment


video_tags_association = sa.Table(
    'video_tags_association',
    Base.metadata,
    sa.Column('video_id', sa.ForeignKey('video.id', ondelete='CASCADE'), primary_key=True),
    sa.Column('tag_id', sa.ForeignKey('video_tag.id', ondelete='CASCADE'), primary_key=True),
)


class Video(Base, TimestampMixin):
    """
    SQLAlchemy model representing a video.
    """

    __tablename__ = 'video'

    public_id: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: uuid.uuid4().hex[:12],
    )
    title: Mapped[str] = mapped_column(sa.String(512), nullable=False, default='')
    slug: Mapped[str] = mapped_column(sa.String(512), nullable=False, unique=True, default=lambda: uuid.uuid4().hex[:12])
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    thumbnail_url: Mapped[str] = mapped_column(sa.String(1024), default='', server_default='')
    video_file_name: Mapped[str] = mapped_column(sa.String(512), default='', server_default='')
    max_resolution: Mapped[str] = mapped_column(sa.String(50), default='1080p', server_default='1080p')
    views: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    is_public: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default='true')
    tags_list: Mapped[list[str]] = mapped_column(sa.JSON, default=list, server_default='[]')

    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        sa.ForeignKey('channel.id', ondelete='CASCADE'),
        nullable=True,
    )

    # Legacy / parser compatibility fields
    source_url: Mapped[str] = mapped_column(sa.String(1024), nullable=False, default='', server_default='')
    external_id: Mapped[str] = mapped_column(sa.String(255), nullable=False, default='', server_default='')
    russian_title: Mapped[str] = mapped_column(sa.String(512), nullable=False, default='', server_default='')
    official_title: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    other_titles: Mapped[list[str]] = mapped_column(sa.JSON, default=list, server_default='[]')
    poster_url: Mapped[str] = mapped_column(sa.String(1024), nullable=False, default='', server_default='')
    is_censored: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default='false')
    duration: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    studio: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    translation_types: Mapped[list[str]] = mapped_column(sa.JSON, default=list, server_default='[]')
    likes_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    dislikes_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')
    views_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default='0')

    channel: Mapped[Channel | None] = relationship(
        'Channel',
        back_populates='videos',
        lazy='selectin',
    )
    likes: Mapped[list['VideoLike']] = relationship(
        'VideoLike',
        back_populates='video',
        cascade='all, delete-orphan',
        lazy='selectin',
    )
    comments: Mapped[list['Comment']] = relationship(
        'Comment',
        back_populates='video',
        cascade='all, delete-orphan',
        lazy='selectin',
    )
    watch_history: Mapped[list['WatchHistory']] = relationship(
        'WatchHistory',
        back_populates='video',
        cascade='all, delete-orphan',
        lazy='selectin',
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


@event.listens_for(Video, 'before_insert')
@event.listens_for(Video, 'before_update')
def video_before_insert(mapper, connection, target: Video):
    if not target.public_id:
        target.public_id = uuid.uuid4().hex[:12]
    if not target.title and target.russian_title:
        target.title = target.russian_title
    if not target.russian_title and target.title:
        target.russian_title = target.title
    if not target.thumbnail_url and target.poster_url:
        target.thumbnail_url = target.poster_url
    if not target.poster_url and target.thumbnail_url:
        target.poster_url = target.thumbnail_url
    if not target.slug:
        slug_src = target.title or target.russian_title or target.public_id
        target.slug = generate_slug(slug_src) or target.public_id
    if target.views and not target.views_count:
        target.views_count = target.views
    elif target.views_count and not target.views:
        target.views = target.views_count


class VideoLike(Base, CreatedAtMixin):
    """
    SQLAlchemy model representing a like on a video.
    """

    __tablename__ = 'video_likes'

    video_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('video.id', ondelete='CASCADE'),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
    )
    is_like: Mapped[bool] = mapped_column(
        sa.Boolean,
        default=True,
        server_default='true',
    )

    user: Mapped[User] = relationship('User', back_populates='likes', lazy='selectin')
    video: Mapped[Video] = relationship('Video', back_populates='likes', lazy='selectin')

    __table_args__ = (sa.UniqueConstraint('video_id', 'user_id', name='uq_video_like_user'),)


class WatchHistory(Base, TimestampMixin):
    __tablename__ = 'watch_history'

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('video.id', ondelete='CASCADE'),
        nullable=False,
    )
    progress_seconds: Mapped[int] = mapped_column(default=0, nullable=False)

    user: Mapped[User] = relationship('User', back_populates='watch_history', lazy='selectin')
    video: Mapped[Video] = relationship('Video', back_populates='watch_history', lazy='selectin')

    __table_args__ = (
        sa.UniqueConstraint(
            'user_id',
            'video_id',
            name='uq_watch_history_user_video',
        ),
    )


class TagCategory(Base):
    __tablename__ = 'tag_category'

    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)

    tags: Mapped[list['VideoTag']] = relationship(
        'VideoTag',
        back_populates='category',
        cascade='all, delete-orphan',
        lazy='selectin',
    )


class VideoTag(Base):
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
    __tablename__ = 'playlist'

    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False, default='', server_default='')
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_private: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default='true')
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
    )

    user: Mapped[User] = relationship('User', back_populates='playlists', lazy='selectin')
    videos: Mapped[list['PlaylistVideo']] = relationship(
        'PlaylistVideo',
        back_populates='playlist',
        cascade='all, delete-orphan',
        order_by='PlaylistVideo.position',
        lazy='selectin',
    )


@event.listens_for(Playlist, 'before_insert')
@event.listens_for(Playlist, 'before_update')
def playlist_before_insert(mapper, connection, target: Playlist):
    if not target.name and target.title:
        target.name = target.title
    if not target.title and target.name:
        target.title = target.name


class PlaylistVideo(Base, CreatedAtMixin):
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
