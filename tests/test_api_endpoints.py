import pytest
from unittest.mock import patch, AsyncMock
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from youtube.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
def mock_email():
    with patch("youtube.services.email_sender.EmailSender.send_verification_code", new_callable=AsyncMock) as m:
        yield m


@pytest.mark.asyncio
async def test_register_success(mock_email):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        uid = uuid4().hex[:6]
        email = f"user_{uid}@test.com"
        payload = {
            "email": email,
            "password": "Password123!",
            "passwordConfirmation": "Password123!",
        }
        res = await ac.post("/auth/register", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()
        assert "accessToken" in data
        assert data["user"]["email"] == email
        assert data["user"]["username"] == f"user_{uid}"
        assert "accessToken" in res.cookies
        assert "refreshToken" in res.cookies


@pytest.mark.asyncio
async def test_register_duplicate_email(mock_email):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        uid = uuid4().hex[:6]
        email = f"dup_{uid}@test.com"
        payload = {"email": email, "password": "Password123!"}
        
        # First register
        res1 = await ac.post("/auth/register", json=payload)
        assert res1.status_code == 200

        # Duplicate register
        res2 = await ac.post("/auth/register", json=payload)
        assert res2.status_code == 409
        err = res2.json()
        assert "message" in err
        assert "already exists" in err["message"]


@pytest.mark.asyncio
async def test_login_success(mock_email):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        uid = uuid4().hex[:6]
        email = f"login_{uid}@test.com"
        password = "Password123!"
        
        # Register first
        await ac.post("/auth/register", json={"email": email, "password": password})

        # Login
        res = await ac.post("/auth/login", json={"email": email, "password": password})
        assert res.status_code == 200
        data = res.json()
        assert "accessToken" in data
        assert data["user"]["email"] == email
        assert "accessToken" in res.cookies
        assert "refreshToken" in res.cookies


@pytest.mark.asyncio
async def test_login_invalid_password(mock_email):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        uid = uuid4().hex[:6]
        email = f"wrong_{uid}@test.com"
        
        # Register
        await ac.post("/auth/register", json={"email": email, "password": "Password123!"})

        # Wrong password
        res = await ac.post("/auth/login", json={"email": email, "password": "WrongPassword1!"})
        assert res.status_code in (400, 401)
        err = res.json()
        assert "message" in err


@pytest.mark.asyncio
async def test_email_verification_flow(mock_email):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        uid = uuid4().hex[:6]
        email = f"verify_{uid}@test.com"
        
        # Register
        res = await ac.post("/auth/register", json={"email": email, "password": "Password123!"})
        assert res.status_code == 200
        user_id = res.json()["user"]["id"]

        # Find user's verification token from DB
        from youtube.db import make_async_session_factory
        from youtube.settings import AppSettingsSchema
        from youtube.apps.user.models import User
        import sqlalchemy as sa

        db_dsn = AppSettingsSchema().db.dsn
        async with make_async_session_factory(db_dsn)() as session:
            stmt = sa.select(User).where(User.email == email)
            user = (await session.execute(stmt)).scalar_one()
            token = user.verification_token

        assert token is not None

        # Verify email with token
        verify_res = await ac.post("/verify-email", json={"token": token})
        assert verify_res.status_code == 200
        v_data = verify_res.json()
        assert v_data["message"] == "Email verified successfully"
        assert v_data["user"]["id"] == user_id


@pytest.mark.asyncio
async def test_resend_verification(mock_email):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post("/resend-verification", json={"email": "any@example.com"})
        assert res.status_code == 200
        assert res.json()["message"] == "Verification email sent"


@pytest.mark.asyncio
async def test_full_jwt_flow(mock_email):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Health check
        res = await ac.get("/health")
        assert res.status_code == 200

        # 2. Register
        uid = uuid4().hex[:6]
        test_email = f"tester_{uid}@example.com"
        test_user = f"tester_{uid}"
        register_payload = {
            "email": test_email,
            "password": "Password123!",
            "username": test_user,
        }
        res = await ac.post("/auth/register", json=register_payload)
        assert res.status_code == 200, res.text
        data = res.json()
        assert "accessToken" in data
        assert data["user"]["email"] == test_email
        assert data["user"]["username"] == test_user
        access_token = data["accessToken"]

        # 3. Access profile (protected)
        res = await ac.get(
            "/user/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert res.status_code == 200, res.text
        profile = res.json()
        assert profile["email"] == test_email
        assert profile["channel"] is not None
        assert profile["channel"]["slug"].startswith("tester-")

        # 4. Refresh token
        refresh_cookie = res.cookies.get("refreshToken") or ac.cookies.get("refreshToken")
        if refresh_cookie:
            res = await ac.post("/auth/access-token")
            assert res.status_code == 200
            new_data = res.json()
            assert "accessToken" in new_data

        # 5. Public videos list
        res = await ac.get("/video")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

        # 6. Channels list
        res = await ac.get("/channels")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

        # 7. Playlists list
        res = await ac.get(
            "/playlists",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert res.status_code == 200
        assert isinstance(res.json(), list)

        # 8. Create playlist
        res = await ac.post(
            "/playlists",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"title": "My Test Playlist"}
        )
        assert res.status_code == 200
        pl = res.json()
        assert pl["name"] == "My Test Playlist"

        # 9. Studio videos
        res = await ac.get(
            "/studio/videos",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert res.status_code == 200
        studio_data = res.json()
        assert "videos" in studio_data

        # 10. Logout
        res = await ac.post("/auth/logout")
        assert res.status_code == 200
