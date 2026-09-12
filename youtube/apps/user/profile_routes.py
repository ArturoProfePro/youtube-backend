"""
User routes: /user  (all require auth)
  GET  /user/profile
  PUT  /user/profile
  PATCH /user/profile/likes
Watch-history: /watch-history
  GET  /watch-history
  POST /watch-history
  DELETE /watch-history
"""

from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, BackgroundTasks, File, Form, Response, UploadFile, status
from pydantic import BaseModel

from youtube.apps.user.service import AuthService, EmailVerificationService, UserService
from youtube.apps.user.types import CurrentUser
from youtube.apps.video.service import VideoViewService
from youtube.depends import Pagination
from youtube.schemas_api import IResponseUser, ISettings, IToggleLikeRequest, IUser
from youtube.services.email_sender import EmailSender
from youtube.apps.user.models import User, Channel, Subscription
from youtube.apps.video.models import VideoLike, WatchHistory, Video

user_router = APIRouter(prefix='/user', tags=['user'], route_class=DishkaRoute)


def _build_response_user(user) -> IResponseUser:
    channel_dict = None
    channel = getattr(user, 'channel', None)
    if channel:
        ch = channel
        channel_dict = {
            'id': str(ch.id),
            'slug': ch.slug,
            'description': ch.description or '',
            'avatar': ch.avatar or '',
            'banner': ch.banner or '',
            'isVerified': ch.is_verified,
        }

    subscriptions = []
    user_subs = getattr(user, 'subscriptions', None)
    if user_subs:
        for sub in user_subs:
            ch = getattr(sub, 'channel', None)
            if ch:
                subscriptions.append({
                    'id': str(sub.id),
                    'userId': str(sub.user_id),
                    'channelId': str(sub.channel_id),
                    'createdAt': sub.created_at.isoformat() if hasattr(sub, 'created_at') and sub.created_at else '',
                    'channel': {
                        'id': str(ch.id),
                        'slug': ch.slug,
                        'description': ch.description or '',
                        'avatar': ch.avatar or '',
                        'banner': ch.banner or '',
                        'isVerified': ch.is_verified,
                    },
                })

    likes = []
    user_likes = getattr(user, 'likes', None)
    if user_likes:
        for like in user_likes:
            likes.append({
                'id': str(like.video_id) + str(like.user_id),
                'videoId': str(like.video_id),
                'userId': str(like.user_id),
            })

    return IResponseUser(
        id=str(user.id),
        username=user.username,
        email=user.email,
        channel=channel_dict,
        subscriptions=subscriptions,
        likes=likes,
        watchHistory=[],
        subscribedVideos=[],
    )


@user_router.get('/profile', status_code=status.HTTP_200_OK, response_model=IResponseUser)
async def get_profile(
    current_user: FromDishka[CurrentUser],
    user_service: FromDishka[UserService],
) -> IResponseUser:
    """Get current user profile with subscriptions and likes."""
    user_model = await user_service.repository.get_model_by_id(current_user.id)
    return _build_response_user(user_model or current_user)


class UpdateProfileBody(BaseModel):
    email: str | None = None
    username: str | None = None
    password: str | None = None
    channel: dict | None = None


@user_router.put('/profile', status_code=status.HTTP_200_OK)
async def update_profile(
    body: UpdateProfileBody,
    current_user: FromDishka[CurrentUser],
    user_service: FromDishka[UserService],
) -> bool:
    """Update user profile and channel settings."""
    await user_service.update_profile(
        user_id=current_user.id,
        username=body.username,
        email=body.email,
        channel_data=body.channel,
    )
    return True


@user_router.patch('/profile/likes', status_code=status.HTTP_200_OK)
async def toggle_like(
    body: IToggleLikeRequest,
    current_user: FromDishka[CurrentUser],
    user_service: FromDishka[UserService],
) -> dict:
    """Toggle like on a video by videoId (publicId)."""
    result = await user_service.toggle_like(current_user.id, body.videoId)
    return {'success': True, 'liked': result}


# ── Watch History ─────────────────────────────────────────────────────────────

watch_history_router = APIRouter(prefix='/watch-history', tags=['watch-history'], route_class=DishkaRoute)


class AddHistoryBody(BaseModel):
    videoId: str


@watch_history_router.get('', status_code=status.HTTP_200_OK)
async def get_watch_history(
    current_user: FromDishka[CurrentUser],
    user_service: FromDishka[UserService],
) -> list[dict]:
    """Get current user's watch history."""
    return await user_service.get_watch_history(current_user.id)


@watch_history_router.post('', status_code=status.HTTP_200_OK)
async def add_to_watch_history(
    body: AddHistoryBody,
    current_user: FromDishka[CurrentUser],
    user_service: FromDishka[UserService],
) -> dict:
    """Add a video to watch history by publicId."""
    await user_service.add_to_watch_history(current_user.id, body.videoId)
    return {'success': True, 'message': 'Added to history'}


@watch_history_router.delete('', status_code=status.HTTP_200_OK)
async def clear_watch_history(
    current_user: FromDishka[CurrentUser],
    user_service: FromDishka[UserService],
) -> dict:
    """Clear all user watch history."""
    await user_service.clear_watch_history(current_user.id)
    return {'success': True, 'message': 'History cleared'}
