import datetime as dt
from typing import Optional
from pydantic import BaseModel
from uuid import UUID

from youtube.apps.video.schemas.video import VideoListItemResponseSchema
from youtube.schemas import ReadSchema, UpdateSchema


class PlaylistVideoReadSchema(ReadSchema):
    video: VideoListItemResponseSchema
    position: int
    created_at: dt.datetime


class PlaylistBaseSchema(BaseModel):
    title: str
    description: Optional[str] = None
    is_private: bool = True


class PlaylistCreateSchema(PlaylistBaseSchema):
    pass


class PlaylistUpdateSchema(UpdateSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    is_private: Optional[bool] = None


class PlaylistUpdateDataSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_private: Optional[bool] = None


class PlaylistReadSchema(ReadSchema, PlaylistBaseSchema):
    id: UUID
    user_id: UUID
    created_at: dt.datetime
    updated_at: dt.datetime
    videos: list[PlaylistVideoReadSchema] = []


class AddVideoToPlaylistSchema(BaseModel):
    video_slug: str
    position: Optional[int] = None
