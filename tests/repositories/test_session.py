from uuid import uuid4, UUID
from youtube.apps.user.repository.session import AuthSessionRepository
import pytest
from redis.asyncio import Redis
import fakeredis

CACHE_DATA = {}


@pytest.mark.parametrize(
    'cache_repository',
    [('in_memory', CACHE_DATA), ('redis', CACHE_DATA)],
    indirect=True,
)
class TestAuthSessionRepositories:
    """
    Cache repository tests.
    """

    @pytest.fixture
    def session_repo(redis):
        return AuthSessionRepository(redis=redis, settings=CoreAuthSettingsSchema())

    @pytest.mark.asyncio
    async def test_create_session_success(session_repo: AuthSessionRepository, redis: Redis):
        token = 'test_token_123'
        user_id = uuid4()

        await session_repo.create(token, user_id)

        raw_data = await redis.get(f'test_session:{token}')
        assert raw_data is not None
        assert raw_data.decode() == str(user_id)

        ttl = await redis.ttl(f'test_session:{token}')
        assert 0 < ttl <= 100

    @pytest.mark.asyncio
    async def test_get_and_refresh_valid_session(session_repo: AuthSessionRepository):
        token = 'valid_token'
        user_id = uuid4()

        await session_repo.create(token, user_id)
        retrieved_id = await session_repo.get_and_refresh(token)

        assert retrieved_id == user_id
        assert isinstance(retrieved_id, UUID)

    @pytest.mark.asyncio
    async def test_get_and_refresh_nonexistent_session_returns_none(session_repo: AuthSessionRepository):
        result = await session_repo.get_and_refresh('non_existent_token')
        assert result is None

    @pytest.mark.asyncio
    async def test_get_and_refresh_extends_ttl(
        session_repo: AuthSessionRepository, redis: fakeredis.aioredis.FakeRedis
    ):
        token = 'sliding_ttl_token'
        user_id = uuid4()

        await session_repo.create(token, user_id)
        key = f'test_session:{token}'

        # Искусственно уменьшаем TTL ключа
        await redis.expire(key, 10)
        assert await redis.ttl(key) <= 10

        # Вызов get_and_refresh должен сбросить TTL обратно до 100
        await session_repo.get_and_refresh(token)
        assert await redis.ttl(key) == 100

    @pytest.mark.asyncio
    async def test_delete_session(session_repo: AuthSessionRepository, redis: Redis):
        token = 'token_to_delete'
        user_id = uuid4()

        await session_repo.create(token, user_id)
        await session_repo.delete(token)

        assert await redis.get(f'test_session:{token}') is None
        assert await session_repo.get_and_refresh(token) is None
