from uuid import UUID
from youtube.apps.video.schemas import VideoReadSchema
from youtube.apps.user.types import CurrentUser
from youtube.apps.video.repository import VideoRepository
from youtube.apps.video.repository.watch_history import UserWatchHistoryRepository
from youtube.apps.video.schemas.watch_history import WatchHistorySchema
from youtube.schemas.pagination import PaginationResultSchema, PaginationSchema


class VideoViewService:
    def __init__(
        self,
        video_repo: VideoRepository,
        user_watch_history_repo: UserWatchHistoryRepository,
    ) -> None:
        self.video_repo = video_repo
        self.user_watch_history_repo = user_watch_history_repo

    async def increment_views(self, video_slug: str) -> None:
        await self.video_repo.increment_views(video_slug)

    async def add_to_watch_history(self, current_user: CurrentUser, watch_history: WatchHistorySchema) -> None:
        await self.user_watch_history_repo.add(current_user.id, watch_history)

    async def get_watch_history(
        self, current_user: CurrentUser, pagination: PaginationSchema
    ) -> PaginationResultSchema[VideoReadSchema]:
        videos = await self.user_watch_history_repo.get(current_user.id, pagination)
        video_ids: list[UUID] = [video_id.video_id for video_id in videos]

        video_results = await self.video_repo.get_by_ids_with_progress(video_ids)

        return PaginationResultSchema(objects=video_results, count=len(video_results))

    async def get_user_progress(self, current_user: CurrentUser, video_id: UUID) -> WatchHistorySchema | None:
        return await self.user_watch_history_repo.get_user_progress(current_user.id, video_id)
