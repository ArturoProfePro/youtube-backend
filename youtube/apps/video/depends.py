from dishka import Provider, Scope, provide

from youtube.apps.video.repository import VideoRepository, VideoTagRepository, PlaylistRepository
from youtube.apps.video.repository.watch_history import UserWatchHistoryRepository
from youtube.apps.video.service import VideoService, VideoTagService, VideoViewService, PlaylistService
from youtube.apps.video.service.public import VideoPublicService, ChannelService
from youtube.db import SessionManagerProtocol


class VideoProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_video_repository(self, session_manager: SessionManagerProtocol) -> VideoRepository:
        return VideoRepository(session_manager)

    @provide
    def get_video_service(self, video_repository: VideoRepository) -> VideoService:
        return VideoService(video_repository)

    @provide
    def get_tag_repository(self, session_manager: SessionManagerProtocol) -> VideoTagRepository:
        return VideoTagRepository(session_manager)

    @provide
    def get_tag_service(self, tag_repository: VideoTagRepository) -> VideoTagService:
        return VideoTagService(tag_repository)

    @provide
    def get_user_watch_history_repository(self, session_manager: SessionManagerProtocol) -> UserWatchHistoryRepository:
        return UserWatchHistoryRepository(session_manager)

    @provide
    def get_video_view_service(
        self,
        video_repo: VideoRepository,
        user_watch_history_repo: UserWatchHistoryRepository,
    ) -> VideoViewService:
        return VideoViewService(video_repo, user_watch_history_repo)

    @provide
    def get_playlist_repository(self, session_manager: SessionManagerProtocol) -> PlaylistRepository:
        return PlaylistRepository(session_manager)

    @provide
    def get_playlist_service(
        self,
        playlist_repo: PlaylistRepository,
        video_repo: VideoRepository,
    ) -> PlaylistService:
        return PlaylistService(playlist_repo, video_repo)

    @provide
    def get_video_public_service(self, session_manager: SessionManagerProtocol) -> VideoPublicService:
        return VideoPublicService(session_manager)

    @provide
    def get_channel_service(self, session_manager: SessionManagerProtocol) -> ChannelService:
        return ChannelService(session_manager)


provider = VideoProvider()
