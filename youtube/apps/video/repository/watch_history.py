import json
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from youtube.apps.video.models import WatchHistory
from youtube.apps.video.schemas.watch_history import WatchHistorySchema
from youtube.db import SessionManagerProtocol
from youtube.repositories import CacheRepositoryProtocol
from youtube.schemas.pagination import PaginationResultSchema, PaginationSchema


class UserWatchHistoryRepository:
    def __init__(self, session_manager: SessionManagerProtocol) -> None:
        self.session_manager = session_manager

    async def add(self, user_id: UUID, watch_history: WatchHistorySchema) -> None:
        async with self.session_manager.get_session() as s:
            stmt = insert(WatchHistory).values(
                user_id=user_id,
                video_id=watch_history.video_id,
                progress_seconds=watch_history.progress_seconds,
            )

            stmt = stmt.on_conflict_do_update(
                index_elements=['user_id', 'video_id'],
                set_={
                    'progress_seconds': stmt.excluded.progress_seconds,
                    'updated_at': func.now(),
                },
            )

            await s.execute(stmt)

    async def get(self, user_id: UUID, pagination: PaginationSchema) -> list[WatchHistorySchema]:
        async with self.session_manager.get_session() as s:
            statement = (
                select(WatchHistory)
                .where(WatchHistory.user_id == user_id)
                .order_by(WatchHistory.created_at.desc())
                .limit(pagination.limit)
                .offset(pagination.offset)
            )
            watch_history = await s.execute(statement)
            objects = [WatchHistorySchema.model_validate(watch) for watch in watch_history.scalars().all()]
            return objects

    async def get_user_progress(self, user_id: UUID, video_id: UUID) -> WatchHistorySchema | None:
        async with self.session_manager.get_session() as s:
            statement = (
                select(WatchHistory).where(WatchHistory.user_id == user_id).where(WatchHistory.video_id == video_id)
            )
            result = await s.execute(statement)
            db_obj = result.scalar_one_or_none()
            if db_obj is None:
                return None
            return WatchHistorySchema.model_validate(db_obj)
