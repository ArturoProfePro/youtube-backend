from datetime import datetime, timedelta, timezone
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, BackgroundTasks, File, Form, Response, UploadFile, status

from youtube.apps.user.depends import CurrentUser, SessionId
from youtube.apps.user.schemas import (
    RegisterUserSchema,
    SendVerificationRequestSchema,
    UserCredentialsSchema,
    UserReadSchema,
    VerifyEmailRequestSchema,
)
from youtube.apps.user.service import AuthService, EmailVerificationService, UserService
from youtube.apps.video.schemas import VideoListItemResponseSchema, VideoReadSchema
from youtube.apps.video.schemas.watch_history import WatchHistorySchema
from youtube.apps.video.service import VideoViewService
from youtube.depends import Pagination
from youtube.schemas import PaginationResultSchema
from youtube.services.email_sender import EmailSender
from youtube.utils.avatar import validate_and_convert_avatar

user_router = APIRouter(prefix='/user', tags=['user'], route_class=DishkaRoute)


@user_router.post(
    '/login',
    status_code=status.HTTP_202_ACCEPTED,
)
async def login(
    response: Response,
    form_data: UserCredentialsSchema,
    auth_service: FromDishka[AuthService],
) -> None:
    session_id = await auth_service.login_user(form_data)
    response.set_cookie(
        key='session_id',
        value=session_id,
        httponly=True,
        max_age=60 * 60 * 24 * 15,
        path='/',
        samesite='lax',
    )


@user_router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response, session_id: FromDishka[SessionId | None], auth_service: FromDishka[AuthService]
) -> None:
    if not session_id:
        return None
    await auth_service.logout(session_id)
    past_utc = datetime.now(timezone.utc) - timedelta(days=1)

    expires_str = past_utc.strftime('%a, %d %b %Y %H:%M:%S GMT')

    response.set_cookie(
        key='session_id',
        value='',
        expires=expires_str,
        max_age=0,
        path='/',
        samesite='lax',
        secure=True,
        httponly=True,
    )


@user_router.post(
    '/register',
    status_code=status.HTTP_201_CREATED,
)
async def register(response: Response, form_data: RegisterUserSchema, auth_service: FromDishka[AuthService]) -> None:
    session_id = await auth_service.register_user(form_data)
    response.set_cookie(key='session_id', value=session_id, httponly=True, max_age=60 * 60 * 24 * 15)


@user_router.get('/me', status_code=status.HTTP_200_OK)
async def get_user(current_user: FromDishka[CurrentUser]) -> UserReadSchema:
    return UserReadSchema.model_validate(current_user)


@user_router.get('/user/watch-history', response_model=PaginationResultSchema[VideoListItemResponseSchema])
async def get_video_watch_history(
    pagination: Pagination,
    video_view_service: FromDishka[VideoViewService],
    current_user: FromDishka[CurrentUser],
) -> PaginationResultSchema[VideoReadSchema]:
    return await video_view_service.get_watch_history(current_user, pagination.to_pagination_schema())


@user_router.get('/user/user-progress')
async def get_user_progress(
    video_id: UUID,
    current_user: FromDishka[CurrentUser],
    video_view_service: FromDishka[VideoViewService],
):
    return await video_view_service.get_user_progress(current_user, video_id)


@user_router.get('/send-verification', status_code=status.HTTP_200_OK)
async def send_verification(
    data: SendVerificationRequestSchema,
    background_tasks: BackgroundTasks,
    email_sender: FromDishka[EmailSender],
    verification_service: FromDishka[EmailVerificationService],
) -> None:
    code: str = await verification_service.generate_and_store_code(data.email)
    background_tasks.add_task(email_sender.send_verification_code, data.email, code)


@user_router.post('/verify-email', status_code=status.HTTP_200_OK)
async def verify_email(
    data: VerifyEmailRequestSchema,
    verification_service: FromDishka[EmailVerificationService],
) -> None:
    await verification_service.verify(data.email, data.code)


@user_router.patch('/me', status_code=status.HTTP_200_OK)
async def update_profile(
    current_user: FromDishka[CurrentUser],
    user_service: FromDishka[UserService],
    username: str | None = Form(None),
    email: str | None = Form(None),
    old_password: str | None = Form(None),
    new_password: str | None = Form(None),
    file: UploadFile | None = File(None),
) -> UserReadSchema:
    avatar_content = None
    avatar_filename = None
    if file and file.filename:
        avatar_content = validate_and_convert_avatar(file)
        avatar_filename = file.filename

    return await user_service.update_profile(
        user_id=current_user.id,
        username=username,
        email=email,
        avatar_content=avatar_content,
        avatar_filename=avatar_filename,
        old_password=old_password,
        new_password=new_password,
    )
