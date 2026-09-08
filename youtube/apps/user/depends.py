from dishka.integrations.fastapi import inject
import uuid
from dishka import Provider, Scope, provide
from fastapi import Request, Response

from youtube.apps.user.repository import AuthSessionRepository, UserRepository
from youtube.apps.user.service import AuthService, EmailVerificationService, UserService
from youtube.apps.user.types import CurrentUser, SessionId
from youtube.db import SessionManagerProtocol
from youtube.exceptions import NotAuthenticatedError
from youtube.repositories import CacheRepositoryProtocol, StorageRepositoryProtocol
from youtube.settings import CoreAuthSettingsSchema, CoreVerificationSettingsSchema


class AuthProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def get_user_repository(self, session_manager: SessionManagerProtocol) -> UserRepository:
        return UserRepository(session_manager)

    @provide
    async def get_session_repository(
        self, cache_repo: CacheRepositoryProtocol, settings: CoreAuthSettingsSchema
    ) -> AuthSessionRepository:
        return AuthSessionRepository(cache_repo, settings)

    @provide
    async def get_auth_service(
        self, repository: UserRepository, session_repository: AuthSessionRepository
    ) -> AuthService:
        return AuthService(repository, session_repository)

    @provide
    async def get_email_verification_service(
        self,
        repository: UserRepository,
        cache_repository: CacheRepositoryProtocol,
        settings: CoreVerificationSettingsSchema,
    ) -> EmailVerificationService:
        return EmailVerificationService(
            repository=repository,
            cache_repository=cache_repository,
            settings=settings,
        )
    @provide
    async def get_user_service(
        self,
        repository: UserRepository,
        storage_repository: StorageRepositoryProtocol,
    ) -> UserService:
        return UserService(repository, storage_repository)
    @provide
    def get_session_id(self, request: Request) -> SessionId | None:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return None
        return SessionId(session_id)

    @provide
    async def get_current_user(
        self,
        session_id: SessionId | None,
        auth_service: AuthService,
    ) -> CurrentUser:
        if session_id is None:
            raise NotAuthenticatedError()
        return CurrentUser(await auth_service.authenticate_user(session_id))

    @provide
    async def get_current_user_or_none(
        self,
        session_id: SessionId | None,
        auth_service: AuthService,
    ) -> CurrentUser | None:
        if session_id is None:
            return None
        try:
            return CurrentUser(await auth_service.authenticate_user(session_id))
        except NotAuthenticatedError:
            return None


provider = AuthProvider()
