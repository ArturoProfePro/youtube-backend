from typing import Optional
import datetime as dt

from pydantic import BaseModel

from youtube.apps.video.schemas.tags import VideoTagCreateSchema, VideoTagReadSchema
from youtube.schemas import CreateSchema, ReadSchema, UpdateSchema


class VideoDirectSourceBaseSchema(BaseModel):
    quality: str
    source_url: str
    video_type: str = 'mp4'
    voiceover: str = 'subs'


class VideoDirectSourceCreateSchema(VideoDirectSourceBaseSchema, CreateSchema):
    pass


class VideoDirectSourceReadSchema(VideoDirectSourceBaseSchema, ReadSchema):
    pass


class VideoExternalPlayerBaseSchema(BaseModel):
    title: str
    embed_url: str
    quality: str | None = None
    player_type: str = 'subs'
    voiceover: str | None = None


class VideoExternalPlayerCreateSchema(VideoExternalPlayerBaseSchema, CreateSchema):
    pass


class VideoExternalPlayerReadSchema(VideoExternalPlayerBaseSchema, ReadSchema):
    pass


class VideoBaseSchema(BaseModel):
    external_id: str
    source_url: str
    russian_title: str
    official_title: str | None = None
    poster_url: str
    is_censored: bool = False
    other_titles: list[str] = []
    description: str | None = None
    duration: int | None = None
    studio: str | None = None
    year: int | None = None
    translation_types: list[str] = []


class VideoReadSchema(ReadSchema, VideoBaseSchema):
    created_at: dt.datetime
    updated_at: dt.datetime
    tags: list[VideoTagReadSchema] = []
    direct_sources: list[VideoDirectSourceReadSchema] = []
    external_players: list[VideoExternalPlayerReadSchema] = []
    slug: str
    views_count: int = 0
    likes_count: int = 0
    dislikes_count: int = 0
    user_progress: Optional[int] = None
    user_reaction: Optional[bool] = None


class VideoPageResponseSchema(ReadSchema):
    russian_title: str
    official_title: str | None = None
    views_count: int = 0
    likes_count: int = 0
    dislikes_count: int = 0
    user_progress: Optional[int] = None
    user_reaction: Optional[bool] = None
    poster_url: str
    is_censored: bool = False
    other_titles: list[str] = []
    description: str | None = None
    duration: int | None = None
    studio: str | None = None
    year: int | None = None
    translation_types: list[str] = []
    created_at: dt.datetime
    updated_at: dt.datetime
    tags: list[VideoTagReadSchema] = []
    direct_sources: list[VideoDirectSourceReadSchema] = []
    external_players: list[VideoExternalPlayerReadSchema] = []


class VideoListItemResponseSchema(ReadSchema):
    russian_title: str
    official_title: str | None = None
    poster_url: str
    slug: str
    views_count: int = 0
    likes_count: int = 0
    dislikes_count: int = 0
    user_progress: Optional[int] = None
    user_reaction: Optional[bool] = None


class VideoCreateSchema(CreateSchema, VideoBaseSchema):
    tags: list[VideoTagCreateSchema] = []
    direct_sources: list[VideoDirectSourceCreateSchema] = []
    external_players: list[VideoExternalPlayerCreateSchema] = []


class VideoUpdateSchema(UpdateSchema):
    source_url: str | None = None
    external_id: str | None = None
    russian_title: str | None = None
    official_title: str | None = None
    other_titles: list[str] | None = None
    description: str | None = None
    poster_url: str | None = None
    is_censored: bool | None = None
    duration: int | None = None
    studio: str | None = None
    year: int | None = None
    translation_types: list[str] | None = None

    tags: list[VideoTagCreateSchema] | None = None
    direct_sources: list[VideoDirectSourceCreateSchema] | None = None
    external_players: list[VideoExternalPlayerCreateSchema] | None = None


class VideoReactionResponseSchema(BaseModel):
    likes_count: int
    dislikes_count: int
    user_reaction: Optional[bool] = None
