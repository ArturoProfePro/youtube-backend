import pytest

from youtube.apps.video.repository import VideoRepository
from youtube.apps.video.schemas import (
    VideoCreateSchema,
    VideoDirectSourceCreateSchema,
    VideoExternalPlayerCreateSchema,
    VideoTagCreateSchema,
)
from youtube.apps.video.schemas.tags import TagCategoryCreateSchema
from youtube.db import Base, make_async_engine
from youtube.apps.parser.repository import DbVideoParserRepository
from youtube.apps.parser.schemas import CategoryDTO, DirectSourceDTO, ExternalPlayerDTO, ParsedVideoDTO, TagDTO


@pytest.fixture(autouse=True)
async def setup_db(settings):
    async_engine = make_async_engine(settings.db.dsn)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_video_repository_create_and_get(session_manager):
    repo = VideoRepository(session_manager)

    video_data = VideoCreateSchema(
        source_url='https://example.com/video.mp4',
        external_id='123',
        russian_title='Тестовое видео',
        poster_url='https://example.com/poster.jpg',
        tags=[
            VideoTagCreateSchema(category=TagCategoryCreateSchema(name='Категория'), name='Тег1'),
            VideoTagCreateSchema(category=TagCategoryCreateSchema(name='Категория'), name='Тег2'),
        ],
        direct_sources=[
            VideoDirectSourceCreateSchema(
                quality='720p',
                source_url='https://example.com/stream.mp4',
            )
        ],
        external_players=[
            VideoExternalPlayerCreateSchema(
                title='Moon',
                embed_url='https://example.com/embed',
            )
        ],
    )

    created = await repo.create(video_data)
    assert created.id is not None
    assert created.russian_title == 'Тестовое видео'
    assert len(created.tags) == 2
    assert {t.name for t in created.tags} == {'Тег1', 'Тег2'}
    assert len(created.direct_sources) == 1
    assert len(created.external_players) == 1

    # Fetch from db to verify persistence
    fetched = await repo.get(created.id)
    assert fetched.id == created.id
    assert fetched.russian_title == 'Тестовое видео'
    assert len(fetched.tags) == 2
    assert len(fetched.direct_sources) == 1
    assert len(fetched.external_players) == 1


async def test_db_video_parser_repository(session_manager):
    video_repo = VideoRepository(session_manager)
    parser_repo = DbVideoParserRepository(video_repo)

    video_dto = ParsedVideoDTO(
        source_url='https://v4.hentai-hub.net/hentai/2891.html',
        external_id='2891',
        russian_title='Test Video',
        poster_url='https://example.com/poster.jpg',
        tags=[TagDTO(category=CategoryDTO(name='cat'), name='tag')],
        direct_sources=[DirectSourceDTO(quality='480p', source_url='https://src.mp4')],
        external_players=[ExternalPlayerDTO(title='ext', embed_url='https://embed')],
    )

    await parser_repo.save(video_dto)

    saved = await parser_repo.get_all()
    assert len(saved) == 1
    assert saved[0].russian_title == 'Test Video'
    assert len(saved[0].tags) == 1
    assert saved[0].tags[0].name == 'tag'
    assert len(saved[0].direct_sources) == 1
    assert len(saved[0].external_players) == 1


async def test_db_video_parser_repository_shared_tags(session_manager):
    video_repo = VideoRepository(session_manager)
    parser_repo = DbVideoParserRepository(video_repo)

    video1 = ParsedVideoDTO(
        source_url='https://v4.hentai-hub.net/hentai/1.html',
        external_id='1',
        russian_title='Video 1',
        poster_url='https://example.com/poster1.jpg',
        tags=[TagDTO(category=CategoryDTO(name='Genre'), name='Action')],
    )
    video2 = ParsedVideoDTO(
        source_url='https://v4.hentai-hub.net/hentai/2.html',
        external_id='2',
        russian_title='Video 2',
        poster_url='https://example.com/poster2.jpg',
        tags=[TagDTO(category=CategoryDTO(name='Genre'), name='Action')],
    )

    await parser_repo.save(video1)
    await parser_repo.save(video2)

    saved = await parser_repo.get_all()
    assert len(saved) == 2

    # Check both have the tag
    assert len(saved[0].tags) == 1
    assert saved[0].tags[0].name == 'Action'
    assert saved[0].tags[0].category.name == 'Genre'

    assert len(saved[1].tags) == 1
    assert saved[1].tags[0].name == 'Action'
    assert saved[1].tags[0].category.name == 'Genre'


async def test_video_repository_get_all(session_manager):
    video_repo = VideoRepository(session_manager)
    videos = await video_repo.get_all()
    assert len(videos) == 0

    video_data = [
        VideoCreateSchema(
            source_url='https://v4.hentai-hub.net/hentai/123-test.html',
            external_id='123',
            russian_title='Тестовое видео',
            poster_url='https://example.com/poster.jpg',
            tags=[
                VideoTagCreateSchema(category=TagCategoryCreateSchema(name='Категория'), name='Тег1'),
                VideoTagCreateSchema(category=TagCategoryCreateSchema(name='Категория'), name='Тег2'),
            ],
            direct_sources=[
                VideoDirectSourceCreateSchema(
                    quality='720p',
                    source_url='https://example.com/stream.mp4',
                )
            ],
            external_players=[
                VideoExternalPlayerCreateSchema(
                    title='Moon',
                    embed_url='https://example.com/embed',
                )
            ],
        ),
        VideoCreateSchema(
            source_url='https://v4.hentai-hub.net/hentai/456-test.html',
            external_id='456',
            russian_title='Тестовое видео',
            poster_url='https://example.com/poster.jpg',
            tags=[
                VideoTagCreateSchema(category=TagCategoryCreateSchema(name='Категория'), name='Тег3'),
                VideoTagCreateSchema(category=TagCategoryCreateSchema(name='Категория'), name='Тег4'),
            ],
            direct_sources=[
                VideoDirectSourceCreateSchema(
                    quality='720p',
                    source_url='https://example.com/1/stream.mp4',
                )
            ],
            external_players=[
                VideoExternalPlayerCreateSchema(
                    title='Moon',
                    embed_url='https://example.com/1/embed',
                )
            ],
        ),
    ]
    for video in video_data:
        await video_repo.save_video(video)

    videos = await video_repo.get_all()
    assert len(videos) == 2
    assert videos[0].russian_title == 'Тестовое видео'
    assert videos[0].poster_url == 'https://example.com/poster.jpg'
    assert {t.name for t in videos[0].tags} == {'Тег1', 'Тег2'}
    assert len(videos[0].direct_sources) == 1
    assert videos[0].direct_sources[0].quality == '720p'
    assert videos[0].direct_sources[0].source_url == 'https://example.com/stream.mp4'
    assert len(videos[0].external_players) == 1
    assert videos[0].external_players[0].title == 'Moon'
    assert videos[0].external_players[0].embed_url == 'https://example.com/embed'

    assert videos[1].russian_title == 'Тестовое видео'
    assert videos[1].poster_url == 'https://example.com/poster.jpg'
    assert {t.name for t in videos[1].tags} == {'Тег3', 'Тег4'}
    assert len(videos[1].direct_sources) == 1
    assert videos[1].direct_sources[0].quality == '720p'
    assert videos[1].direct_sources[0].source_url == 'https://example.com/1/stream.mp4'
    assert len(videos[1].external_players) == 1
    assert videos[1].external_players[0].title == 'Moon'
    assert videos[1].external_players[0].embed_url == 'https://example.com/1/embed'
