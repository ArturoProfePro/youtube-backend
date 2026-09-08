from youtube.db import SessionManagerProtocol
from dishka import Provider, Scope, provide
from youtube.apps.comment.repository import CommentRepository
from youtube.apps.comment.service import CommentService


class CommentProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def get_comment_repository(self, session_manager: SessionManagerProtocol) -> CommentRepository:
        return CommentRepository(session_manager=session_manager)

    @provide
    def get_comment_service(self, repository: CommentRepository) -> CommentService:
        return CommentService(repository=repository)


provider = CommentProvider()


