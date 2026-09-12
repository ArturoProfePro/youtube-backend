"""
Video public routes: /video — properly wired to VideoService
Channel routes: /channels — wired to ChannelService
"""
from uuid import UUID

import sqlalchemy as sa
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status
from pydantic import BaseModel

from youtube.apps.user.types import CurrentUser
from youtube.apps.video.models import Video, VideoLike
from youtube.apps.user.models import Channel, Subscription
from youtube.apps.video.service.public import VideoPublicService, ChannelService


public_video_router = APIRouter(prefix='/video', tags=['video'], route_class=DishkaRoute)
channel_router = APIRouter(prefix='/channels', tags=['channels'], route_class=DishkaRoute)


def _video_to_dict(v) -> dict:
    channel_dict = None
    if v.channel:
        ch = v.channel
        channel_dict = {
            'id': str(ch.id),
            'slug': ch.slug,
            'description': ch.description or '',
            'isVerified': ch.is_verified,
            'avatar': ch.avatar or '',
            'banner': ch.banner or '',
        }
    likes = []
    if hasattr(v, 'likes') and v.likes:
        likes = [{'userId': str(lk.user_id)} for lk in v.likes]
    return {
        'id': str(v.id),
        'publicId': v.public_id,
        'title': v.title or v.russian_title or '',
        'description': v.description,
        'thumbnailUrl': v.thumbnail_url or v.poster_url or '',
        'videoFileName': v.video_file_name or '',
        'maxResolution': v.max_resolution or '1080p',
        'views': v.views or v.views_count or 0,
        'isPublic': v.is_public,
        'createdAt': v.created_at.isoformat() if hasattr(v, 'created_at') and v.created_at else '',
        'channel': channel_dict,
        'likes': likes,
        'comments': [],
    }


def _channel_to_dict(ch, include_videos=True) -> dict:
    owner_dict = None
    if ch.user:
        u = ch.user
        owner_dict = {'id': str(u.id), 'username': u.username, 'email': u.email}
    videos = []
    if include_videos and ch.videos:
        videos = [_video_to_dict(v) for v in ch.videos if v.is_public]
    subs = []
    if ch.subscribers:
        subs = [{'id': str(s.user_id)} for s in ch.subscribers]
    return {
        'id': str(ch.id),
        'slug': ch.slug,
        'description': ch.description or '',
        'isVerified': ch.is_verified,
        'avatar': ch.avatar or '',
        'banner': ch.banner or '',
        'owner': owner_dict,
        'videos': videos,
        'subscriptions': subs,
        'createdAt': ch.created_at.isoformat() if hasattr(ch, 'created_at') and ch.created_at else '',
    }


# ── Video endpoints ───────────────────────────────────────────────────────────

@public_video_router.get('', status_code=status.HTTP_200_OK)
async def list_videos(
    video_service: FromDishka[VideoPublicService],
    searchTerm: str | None = None,
) -> list[dict]:
    """List public videos, optionally filtered by searchTerm."""
    return await video_service.get_all(search_term=searchTerm)


@public_video_router.get('/trendingVideos', status_code=status.HTTP_200_OK)
async def trending_videos(
    video_service: FromDishka[VideoPublicService],
) -> list[dict]:
    """Most viewed videos."""
    return await video_service.get_trending()


@public_video_router.get('/videoGames', status_code=status.HTTP_200_OK)
async def video_games(
    video_service: FromDishka[VideoPublicService],
) -> list[dict]:
    """Videos tagged as Games."""
    return await video_service.get_by_category('games')


@public_video_router.get('/explore', status_code=status.HTTP_200_OK)
async def explore_videos(
    video_service: FromDishka[VideoPublicService],
    userId: str | None = None,
    page: int = 1,
    limit: int = 10,
    excludeIds: str | None = None,
) -> dict:
    """Explore / recommendation feed with pagination."""
    exclude_list = [e.strip() for e in excludeIds.split(',')] if excludeIds else []
    return await video_service.get_explore(page=page, limit=limit, user_id=userId, exclude_ids=exclude_list)


@public_video_router.post('/by-publicId/{publicId}', status_code=status.HTTP_200_OK)
async def video_by_public_id(
    publicId: str,
    video_service: FromDishka[VideoPublicService],
) -> dict:
    """Get full video info + similar videos by publicId."""
    return await video_service.get_by_public_id(publicId)


@public_video_router.put('/update-views-count/{publicId}', status_code=status.HTTP_200_OK)
async def update_views(
    publicId: str,
    video_service: FromDishka[VideoPublicService],
) -> dict:
    """Increment video views count."""
    await video_service.increment_views(publicId)
    return {'success': True}


# ── Channel endpoints ─────────────────────────────────────────────────────────

@channel_router.get('', status_code=status.HTTP_200_OK)
async def list_channels(
    channel_service: FromDishka[ChannelService],
) -> list[dict]:
    """List all channels."""
    return await channel_service.get_all()


@channel_router.post('/by-slug/{slug}', status_code=status.HTTP_200_OK)
async def channel_by_slug(
    slug: str,
    channel_service: FromDishka[ChannelService],
) -> dict:
    """Get channel info by slug."""
    return await channel_service.get_by_slug(slug)


@channel_router.patch('/toggle-subscribe/{slug}', status_code=status.HTTP_200_OK)
async def toggle_subscribe(
    slug: str,
    current_user: FromDishka[CurrentUser],
    channel_service: FromDishka[ChannelService],
) -> dict:
    """Subscribe/unsubscribe from channel by slug (auth required)."""
    return await channel_service.toggle_subscribe(slug, current_user.id)
