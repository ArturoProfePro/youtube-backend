from youtube.schemas import BaseSchema
from uuid import UUID


class WatchHistorySchema(BaseSchema):
    video_id: UUID

    progress_seconds: int
