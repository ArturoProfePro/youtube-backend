from dishka.integrations.fastapi import inject
import uuid
from dishka import Provider, Scope, provide
from fastapi import Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from youtube.apps.user.repository import AuthSessionRepository, UserRepository
from youtube.apps.user.service import AuthService, EmailVerificationService, UserService
from youtube.apps.user.types import CurrentUser
from youtube.db import SessionManagerProtocol
from youtube.exceptions import NotAuthenticatedError
from youtube.repositories import CacheRepositoryProtocol, StorageRepositoryProtocol
from youtube.settings import CoreAuthSettingsSchema, CoreVerificationSettingsSchema

_bearer_scheme = HTTPBearer(auto_error=False)


def _extract_token(request: Request) -> str | None:
    """Extract JWT from Authorization header or accessToken cookie."""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.lower().startswith('bearer '):
        return auth_header[7:]
    # fallback to cookie
    return request.cookies.get('accessToken')


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
        self,
        repository: UserRepository,
        session_repository: AuthSessionRepository,
        settings: CoreAuthSettingsSchema,
    ) -> AuthService:
        return AuthService(
            repository=repository,
            access_secret_key=settings.access_secret,
            refresh_secret_key=settings.refresh_secret,
            session_repository=session_repository,
        )


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
    def get_access_token(self, request: Request) -> str | None:
        return _extract_token(request)

    @provide
    async def get_current_user(
        self,
        token: str | None,
        auth_service: AuthService,
    ) -> CurrentUser:
        if token is None:
            raise NotAuthenticatedError()
        return CurrentUser(await auth_service.authenticate_jwt(token))

    @provide
    async def get_current_user_or_none(
        self,
        token: str | None,
        auth_service: AuthService,
    ) -> CurrentUser | None:
        if token is None:
            return None
        try:
            return CurrentUser(await auth_service.authenticate_jwt(token))
        except (NotAuthenticatedError, Exception):
            return None


provider = AuthProvider()
