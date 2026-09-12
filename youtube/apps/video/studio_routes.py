"""
Studio routes: /studio/videos  (all require auth)
  GET    /studio/videos        — paginated list for current author
  GET    /studio/videos/{id}
  POST   /studio/videos
  PUT    /studio/videos/{id}
  DELETE /studio/videos/{id}
"""
from uuid import UUID

import sqlalchemy as sa
from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Optional, List

from youtube.apps.user.types import CurrentUser
from youtube.db import SessionManagerProtocol

studio_router = APIRouter(prefix='/studio/videos', tags=['studio'], route_class=DishkaRoute)


class VideoFormData(BaseModel):
    title: str
    description: Optional[str] = None
    thumbnailUrl: str = ''
    videoFileName: str = ''
    maxResolution: str = '1080p'
    tags: List[str] = []
    isPublic: bool = True


def _studio_video_to_dict(v) -> dict:
    channel_dict = None
    if v.channel:
        ch = v.channel
        channel_dict = {
            'id': str(ch.id), 'slug': ch.slug, 'avatar': ch.avatar or '', 'isVerified': ch.is_verified
        }
    comments = [
        {
            'id': str(c.id),
            'text': c.text or c.content or '',
            'createdAt': c.created_at.isoformat() if c.created_at else '',
            'videoId': str(c.video_id),
            'user': {'id': str(c.user.id), 'username': c.user.username} if c.user else {},
        }
        for c in (v.comments or [])
    ]
    return {
        'id': str(v.id),
        'publicId': v.public_id,
        'title': v.title or v.russian_title or '',
        'description': v.description,
        'thumbnailUrl': v.thumbnail_url or v.poster_url or '',
        'videoFileName': v.video_file_name or '',
        'maxResolution': v.max_resolution or '1080p',
        'views': (v.views or 0) + (v.views_count or 0),
        'isPublic': v.is_public,
        'createdAt': v.created_at.isoformat() if v.created_at else '',
        'channel': channel_dict,
        'likes': [{'userId': str(lk.user_id)} for lk in (v.likes or [])],
        'comments': comments,
        'tags': list(v.tags_list or []),
    }


@studio_router.get('', status_code=status.HTTP_200_OK)
async def get_studio_videos(
    current_user: FromDishka[CurrentUser],
    session_manager: FromDishka[SessionManagerProtocol],
    page: int = 1,
    limit: int = 10,
    searchTerm: str | None = None,
) -> dict:
    from youtube.apps.video.models import Video
    from youtube.apps.user.models import Channel

    async with session_manager.get_session() as s:
        # Find current user's channel
        ch_stmt = sa.select(Channel).where(Channel.user_id == current_user.id)
        ch_result = await s.execute(ch_stmt)
        channel = ch_result.scalar_one_or_none()
        if channel is None:
            return {'page': page, 'limit': limit, 'totalCount': 0, 'totalPages': 0, 'videos': []}

        stmt = sa.select(Video).where(Video.channel_id == channel.id)
        if searchTerm:
            stmt = stmt.where(
                (Video.title.ilike(f'%{searchTerm}%')) | (Video.description.ilike(f'%{searchTerm}%'))
            )

        count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
        total = (await s.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(Video.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await s.execute(stmt)
        videos = result.scalars().all()
        total_pages = (total + limit - 1) // limit if total > 0 else 0
        return {
            'page': page,
            'limit': limit,
            'totalCount': total,
            'totalPages': total_pages,
            'videos': [_studio_video_to_dict(v) for v in videos],
        }


@studio_router.get('/{video_id}', status_code=status.HTTP_200_OK)
async def get_studio_video(
    video_id: UUID,
    current_user: FromDishka[CurrentUser],
    session_manager: FromDishka[SessionManagerProtocol],
) -> dict:
    from youtube.apps.video.models import Video
    from youtube.apps.user.models import Channel
    from youtube.exceptions import ModelNotFoundError, PermissionDeniedError

    async with session_manager.get_session() as s:
        ch_stmt = sa.select(Channel).where(Channel.user_id == current_user.id)
        ch_result = await s.execute(ch_stmt)
        channel = ch_result.scalar_one_or_none()

        stmt = sa.select(Video).where(Video.id == video_id)
        result = await s.execute(stmt)
        video = result.scalar_one_or_none()
        if video is None:
            raise ModelNotFoundError(Video, model_id=video_id)
        if channel is None or video.channel_id != channel.id:
            raise PermissionDeniedError()
        return _studio_video_to_dict(video)


@studio_router.post('', status_code=status.HTTP_201_CREATED)
async def create_studio_video(
    body: VideoFormData,
    current_user: FromDishka[CurrentUser],
    session_manager: FromDishka[SessionManagerProtocol],
) -> dict:
    import uuid as uuid_mod
    from youtube.apps.video.models import Video
    from youtube.apps.user.models import Channel
    from youtube.exceptions import PermissionDeniedError

    async with session_manager.get_session() as s:
        ch_stmt = sa.select(Channel).where(Channel.user_id == current_user.id)
        ch_result = await s.execute(ch_stmt)
        channel = ch_result.scalar_one_or_none()
        if channel is None:
            raise PermissionDeniedError()

        public_id = uuid_mod.uuid4().hex[:12]
        video = Video(
            public_id=public_id,
            title=body.title,
            russian_title=body.title,
            description=body.description,
            thumbnail_url=body.thumbnailUrl,
            poster_url=body.thumbnailUrl,
            video_file_name=body.videoFileName,
            max_resolution=body.maxResolution,
            is_public=body.isPublic,
            tags_list=body.tags,
            channel_id=channel.id,
            source_url='',
            external_id=public_id,
        )
        s.add(video)
        await s.flush()
        return _studio_video_to_dict(video)


@studio_router.put('/{video_id}', status_code=status.HTTP_200_OK)
async def update_studio_video(
    video_id: UUID,
    body: VideoFormData,
    current_user: FromDishka[CurrentUser],
    session_manager: FromDishka[SessionManagerProtocol],
) -> dict:
    from youtube.apps.video.models import Video
    from youtube.apps.user.models import Channel
    from youtube.exceptions import ModelNotFoundError, PermissionDeniedError

    async with session_manager.get_session() as s:
        ch_stmt = sa.select(Channel).where(Channel.user_id == current_user.id)
        ch_result = await s.execute(ch_stmt)
        channel = ch_result.scalar_one_or_none()

        stmt = sa.select(Video).where(Video.id == video_id)
        result = await s.execute(stmt)
        video = result.scalar_one_or_none()
        if video is None:
            raise ModelNotFoundError(Video, model_id=video_id)
        if channel is None or video.channel_id != channel.id:
            raise PermissionDeniedError()

        video.title = body.title
        video.russian_title = body.title
        video.description = body.description
        video.thumbnail_url = body.thumbnailUrl
        video.poster_url = body.thumbnailUrl
        video.video_file_name = body.videoFileName
        video.max_resolution = body.maxResolution
        video.is_public = body.isPublic
        video.tags_list = body.tags
        return _studio_video_to_dict(video)


@studio_router.delete('/{video_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_studio_video(
    video_id: UUID,
    current_user: FromDishka[CurrentUser],
    session_manager: FromDishka[SessionManagerProtocol],
) -> None:
    from youtube.apps.video.models import Video
    from youtube.apps.user.models import Channel
    from youtube.exceptions import ModelNotFoundError, PermissionDeniedError

    async with session_manager.get_session() as s:
        ch_stmt = sa.select(Channel).where(Channel.user_id == current_user.id)
        ch_result = await s.execute(ch_stmt)
        channel = ch_result.scalar_one_or_none()

        stmt = sa.select(Video).where(Video.id == video_id)
        result = await s.execute(stmt)
        video = result.scalar_one_or_none()
        if video is None:
            raise ModelNotFoundError(Video, model_id=video_id)
        if channel is None or video.channel_id != channel.id:
            raise PermissionDeniedError()

        await s.delete(video)
