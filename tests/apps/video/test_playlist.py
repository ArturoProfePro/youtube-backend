import pytest

from youtube.apps.user.models import User
from youtube.apps.video.repository import VideoRepository, PlaylistRepository
from youtube.apps.video.schemas import VideoCreateSchema
from youtube.apps.video.schemas.playlist import PlaylistCreateSchema, PlaylistUpdateSchema
from youtube.db import Base, make_async_engine


@pytest.fixture(autouse=True)
async def setup_db(settings):
    async_engine = make_async_engine(settings.db.dsn)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _create_user(session_manager, username='testuser'):
    user = User(
        username=username,
        email=f'{username}@example.com',
        hashed_password='password',
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    async with session_manager.get_session() as session:
        session.add(user)
        await session.commit()
    return user


async def _create_video(video_repo, external_id='123'):
    return await video_repo.create(
        VideoCreateSchema(
            source_url=f'https://example.com/{external_id}.html',
            external_id=external_id,
            russian_title=f'Видео {external_id}',
            poster_url='https://example.com/poster.jpg',
        )
    )


async def test_create_playlist(session_manager):
    user = await _create_user(session_manager)
    repo = PlaylistRepository(session_manager)

    create_data = PlaylistCreateSchema(title='Мой плейлист', description='Описание', is_private=False)
    playlist = await repo.create_playlist(create_data, user.id)
    assert playlist.title == 'Мой плейлист'
    assert playlist.description == 'Описание'
    assert playlist.is_private is False
    assert playlist.user_id == user.id
    assert playlist.videos == []


async def test_add_and_remove_video(session_manager):
    user = await _create_user(session_manager)
    video_repo = VideoRepository(session_manager)
    repo = PlaylistRepository(session_manager)

    video1 = await _create_video(video_repo, '1')
    video2 = await _create_video(video_repo, '2')

    create_data = PlaylistCreateSchema(title='Плейлист', description=None, is_private=True)
    playlist = await repo.create_playlist(create_data, user.id)

    # Add videos
    playlist = await repo.add_video(playlist.id, video1.id)
    assert len(playlist.videos) == 1
    assert playlist.videos[0].position == 0

    playlist = await repo.add_video(playlist.id, video2.id)
    assert len(playlist.videos) == 2
    assert playlist.videos[1].position == 1

    # Remove first video
    playlist = await repo.remove_video(playlist.id, video1.id)
    assert len(playlist.videos) == 1
    assert playlist.videos[0].video.id == video2.id


async def test_reorder_video(session_manager):
    user = await _create_user(session_manager)
    video_repo = VideoRepository(session_manager)
    repo = PlaylistRepository(session_manager)

    v1 = await _create_video(video_repo, '10')
    v2 = await _create_video(video_repo, '20')
    v3 = await _create_video(video_repo, '30')

    create_data = PlaylistCreateSchema(title='Ordering', description=None, is_private=True)
    playlist = await repo.create_playlist(create_data, user.id)
    await repo.add_video(playlist.id, v1.id)
    await repo.add_video(playlist.id, v2.id)
    playlist = await repo.add_video(playlist.id, v3.id)

    assert [pv.video.id for pv in playlist.videos] == [v1.id, v2.id, v3.id]

    # Move v3 to position 0
    playlist = await repo.reorder_video(playlist.id, v3.id, 0)
    # v3 should now have position 0
    v3_entry = next(pv for pv in playlist.videos if pv.video.id == v3.id)
    assert v3_entry.position == 0


async def test_get_user_playlists(session_manager):
    user = await _create_user(session_manager)
    repo = PlaylistRepository(session_manager)

    await repo.create_playlist(PlaylistCreateSchema(title='First', description=None, is_private=False), user.id)
    await repo.create_playlist(PlaylistCreateSchema(title='Second', description=None, is_private=True), user.id)

    playlists = await repo.get_user_playlists(user.id)
    assert len(playlists) == 2
    titles = {p.title for p in playlists}
    assert titles == {'First', 'Second'}


async def test_update_playlist(session_manager):
    user = await _create_user(session_manager)
    repo = PlaylistRepository(session_manager)

    playlist = await repo.create_playlist(PlaylistCreateSchema(title='Old Title', description='Old desc', is_private=True), user.id)
    updated = await repo.update_playlist(playlist.id, PlaylistUpdateSchema(id=playlist.id, title='New Title', description=None, is_private=False))
    assert updated.title == 'New Title'
    assert updated.is_private is False


async def test_delete_playlist(session_manager):
    user = await _create_user(session_manager)
    repo = PlaylistRepository(session_manager)

    playlist = await repo.create_playlist(PlaylistCreateSchema(title='To Delete', description=None, is_private=True), user.id)
    await repo.delete_playlist(playlist.id)

    playlists = await repo.get_user_playlists(user.id)
    assert len(playlists) == 0


async def test_owner_check(session_manager):
    user = await _create_user(session_manager)
    repo = PlaylistRepository(session_manager)

    playlist = await repo.create_playlist(PlaylistCreateSchema(title='Test', description=None, is_private=True), user.id)
    owner_id = await repo.get_owner_id(playlist.id)
    assert owner_id == user.id

    is_priv = await repo.is_private(playlist.id)
    assert is_priv is True
