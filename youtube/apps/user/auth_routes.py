"""
Auth routes: /auth
  POST /auth/register
  POST /auth/login
  POST /auth/access-token  (refresh)
  POST /auth/logout
"""

import secrets
from datetime import datetime, timedelta, timezone

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, BackgroundTasks, Header, Request, Response, status

from youtube.apps.user.depends import _extract_token
from youtube.apps.user.service import AuthService, EmailVerificationService, UserService
from youtube.apps.user.types import CurrentUser
from youtube.exceptions import NotAuthenticatedError
from youtube.schemas_api import (
    IAuthResponse,
    IEmailVerificationRequest,
    IResendEmailRequest,
    IUser,
)
from youtube.services.email_sender import EmailSender

auth_router = APIRouter(prefix='/auth', tags=['auth'], route_class=DishkaRoute)

_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def _set_tokens(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key='accessToken',
        value=access_token,
        httponly=True,
        max_age=_COOKIE_MAX_AGE,
        path='/',
        samesite='strict',
    )
    response.set_cookie(
        key='refreshToken',
        value=refresh_token,
        httponly=True,
        max_age=_COOKIE_MAX_AGE,
        path='/',
        samesite='strict',
    )


def _clear_tokens(response: Response) -> None:
    past = datetime.now(timezone.utc) - timedelta(days=1)
    expires_str = past.strftime('%a, %d %b %Y %H:%M:%S GMT')
    for key in ('accessToken', 'refreshToken'):
        response.set_cookie(
            key=key,
            value='',
            expires=expires_str,
            max_age=0,
            path='/',
            samesite='strict',
            httponly=True,
        )


class _AuthBody:
    """Simple body for login/register."""

    def __init__(self, email: str, password: str, username: str | None = None) -> None:
        self.email = email
        self.password = password
        self.username = username


from pydantic import BaseModel, EmailStr


class AuthBody(BaseModel):
    email: EmailStr
    password: str
    username: str | None = None
    passwordConfirmation: str | None = None
    password_confirmation: str | None = None

    model_config = {'extra': 'ignore'}


@auth_router.post('/register', status_code=status.HTTP_200_OK, response_model=IAuthResponse)
async def register(
    body: AuthBody,
    response: Response,
    request: Request,
    auth_service: FromDishka[AuthService],
    background_tasks: BackgroundTasks,
    email_sender: FromDishka[EmailSender],
    verification_service: FromDishka[EmailVerificationService],
) -> IAuthResponse:
    """Register a new user. Returns IAuthResponse with accessToken."""
    username = body.username or body.email.split('@')[0]
    verification_token = secrets.token_urlsafe(32)
    user, access_token, refresh_token = await auth_service.register_jwt(
        email=body.email,
        password=body.password,
        username=username,
        verification_token=verification_token,
    )

    # Send verification email in background without blocking response
    async def _send_verification():
        try:
            code = await verification_service.generate_and_store_code(body.email)
            verify_link = f'http://localhost:3000/verify-email?token={verification_token}'
            await email_sender.send_verification_code(body.email, code or verification_token, verify_link)
        except Exception as e:
            import logging
            logging.warning(f'Failed to send verification email: {e}')

    background_tasks.add_task(_send_verification)

    _set_tokens(response, access_token, refresh_token)
    return IAuthResponse(
        user=IUser(id=str(user.id), username=user.username, email=user.email),
        accessToken=access_token,
    )


@auth_router.post('/login', status_code=status.HTTP_200_OK, response_model=IAuthResponse)
async def login(
    body: AuthBody,
    response: Response,
    auth_service: FromDishka[AuthService],
) -> IAuthResponse:
    """Login user. Returns IAuthResponse with accessToken."""
    user, access_token, refresh_token = await auth_service.login_jwt(
        email=body.email,
        password=body.password,
    )
    _set_tokens(response, access_token, refresh_token)
    return IAuthResponse(
        user=IUser(id=str(user.id), username=user.username, email=user.email),
        accessToken=access_token,
    )


@auth_router.post('/access-token', status_code=status.HTTP_200_OK, response_model=IAuthResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    auth_service: FromDishka[AuthService],
) -> IAuthResponse:
    """Refresh access token using refresh token from cookie."""
    refresh_token = request.cookies.get('refreshToken')
    if not refresh_token:
        raise NotAuthenticatedError()

    user, access_token, new_refresh = await auth_service.refresh_jwt(refresh_token)
    _set_tokens(response, access_token, new_refresh)
    return IAuthResponse(
        user=IUser(id=str(user.id), username=user.username, email=user.email),
        accessToken=access_token,
    )


@auth_router.post('/logout', status_code=status.HTTP_200_OK)
async def logout(response: Response) -> bool:
    """Invalidate tokens by clearing cookies."""
    _clear_tokens(response)
    return True


# ── Email verification ────────────────────────────────────────────────────────

verify_router = APIRouter(tags=['verify'], route_class=DishkaRoute)


@verify_router.post('/verify-email', status_code=status.HTTP_200_OK)
async def verify_email(
    body: IEmailVerificationRequest,
    verification_service: FromDishka[EmailVerificationService],
) -> dict:
    """Confirm email using a token/code. Returns message and user."""
    user = await verification_service.verify_by_token(body.token)
    if user:
        return {
            'message': 'Email verified successfully',
            'user': {'id': str(user.id), 'username': user.username, 'email': user.email},
        }
    return {'message': 'Email verified successfully', 'user': None}


@verify_router.post('/resend-verification', status_code=status.HTTP_200_OK)
async def resend_verification(
    body: IResendEmailRequest,
    background_tasks: BackgroundTasks,
    email_sender: FromDishka[EmailSender],
    verification_service: FromDishka[EmailVerificationService],
) -> dict:
    """Resend verification email."""
    code = await verification_service.generate_and_store_code(body.email)
    background_tasks.add_task(email_sender.send_verification_code, body.email, code)
    return {'message': 'Verification email sent'}
