import pytest
import uuid6 as uuid

from youtube.apps.video.repository import VideoRepository
from youtube.apps.video.schemas import (
    VideoCreateSchema,
)
from youtube.apps.user.models import User
from youtube.db import Base, make_async_engine


@pytest.fixture(autouse=True)
async def setup_db(settings):
    async_engine = make_async_engine(settings.db.dsn)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_video_reactions(session_manager):
    # 1. Create a user
    user = User(
        username='testuser',
        email='test@example.com',
        hashed_password='password',
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    async with session_manager.get_session() as session:
        session.add(user)
        await session.commit()

    # 2. Create a video
    video_repo = VideoRepository(session_manager)
    video_data = VideoCreateSchema(
        source_url='https://v4.hentai-hub.net/hentai/123-test.html',
        external_id='123',
        russian_title='Тестовое видео',
        poster_url='https://example.com/poster.jpg',
    )
    created_video = await video_repo.create(video_data)

    # 3. Check initial state
    fetched = await video_repo.get_by_slug_with_progress(created_video.slug, user.id)
    assert fetched.likes_count == 0
    assert fetched.dislikes_count == 0
    assert fetched.user_reaction is None

    # 4. Toggle like (add reaction)
    likes_count, dislikes_count, reaction = await video_repo.toggle_reaction(created_video.slug, user.id, is_like=True)
    assert likes_count == 1
    assert dislikes_count == 0
    assert reaction is True

    # Check updated state
    fetched = await video_repo.get_by_slug_with_progress(created_video.slug, user.id)
    assert fetched.likes_count == 1
    assert fetched.dislikes_count == 0
    assert fetched.user_reaction is True

    # 5. Toggle like again (remove reaction)
    likes_count, dislikes_count, reaction = await video_repo.toggle_reaction(created_video.slug, user.id, is_like=True)
    assert likes_count == 0
    assert dislikes_count == 0
    assert reaction is None

    # Check updated state
    fetched = await video_repo.get_by_slug_with_progress(created_video.slug, user.id)
    assert fetched.likes_count == 0
    assert fetched.dislikes_count == 0
    assert fetched.user_reaction is None

    # 6. Toggle dislike (add reaction)
    likes_count, dislikes_count, reaction = await video_repo.toggle_reaction(created_video.slug, user.id, is_like=False)
    assert likes_count == 0
    assert dislikes_count == 1
    assert reaction is False

    # Check updated state
    fetched = await video_repo.get_by_slug_with_progress(created_video.slug, user.id)
    assert fetched.likes_count == 0
    assert fetched.dislikes_count == 1
    assert fetched.user_reaction is False

    # 7. Toggle like while disliked (switch reaction)
    likes_count, dislikes_count, reaction = await video_repo.toggle_reaction(created_video.slug, user.id, is_like=True)
    assert likes_count == 1
    assert dislikes_count == 0
    assert reaction is True

    # Check updated state
    fetched = await video_repo.get_by_slug_with_progress(created_video.slug, user.id)
    assert fetched.likes_count == 1
    assert fetched.dislikes_count == 0
    assert fetched.user_reaction is True
