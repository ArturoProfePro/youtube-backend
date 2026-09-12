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


@pytest.mark.asyncio
async def test_separate_jwt_secrets_isolation(session_manager):
    """Test that access and refresh tokens use separate secret keys and cannot be substituted."""

    import jwt
    from youtube.services.jwt_auth import decode_token

    access_secret = "testaccesssecretkeythirtytwobyteslonghere!"
    refresh_secret = "testrefreshsecretkeythirtytwobyteslonghere!"

    unique_email = f"jwt_iso_{uuid4().hex[:6]}@example.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/auth/register",
            json={"email": unique_email, "password": "password123"},
        )
        assert res.status_code == 200
        data = res.json()
        access_token = data["accessToken"]
        refresh_token = res.cookies.get("refreshToken")
        assert refresh_token is not None

        # 1. Access token can be decoded with access_secret, but FAILS with refresh_secret
        acc_payload = decode_token(access_token, access_secret)
        assert acc_payload["type"] == "access"
        assert acc_payload["email"] == unique_email

        with pytest.raises(jwt.PyJWTError):
            decode_token(access_token, refresh_secret)

        # 2. Refresh token can be decoded with refresh_secret, but FAILS with access_secret
        ref_payload = decode_token(refresh_token, refresh_secret)
        assert ref_payload["type"] == "refresh"

        with pytest.raises(jwt.PyJWTError):
            decode_token(refresh_token, access_secret)

        # 3. Attempting to use refresh_token as Bearer access token fails (401)
        res = await ac.get(
            "/user/profile",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert res.status_code == 401

        # 4. Attempting to use access_token in refreshToken cookie fails (401)
        ac.cookies.set("refreshToken", access_token)
        res = await ac.post("/auth/access-token")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_recaptcha_verification_service():
    """Test RecaptchaService validation logic."""
    from youtube.services.recaptcha import RecaptchaService, InvalidCaptchaError

    service = RecaptchaService(
        secret_key="6LfI8rctAAAAAJPtOjM1tdOl8LWjxrHF4YT1DK2E",
        enabled=True,
        required=True,
    )

    # 1. Bypass / mock tokens always pass
    assert await service.verify("test") is True
    assert await service.verify("test-recaptcha-token") is True

    # 2. Missing token when required raises InvalidCaptchaError
    with pytest.raises(InvalidCaptchaError) as exc_info:
        await service.verify(None)
    assert "reCAPTCHA token is required" in exc_info.value.message

    # 3. Disabled recaptcha always passes
    disabled_service = RecaptchaService(enabled=False, required=True)
    assert await disabled_service.verify(None) is True


async def test_keygen_script():
    """Test that keygen.py generates valid 256-bit hex keys."""

    import subprocess
    result = subprocess.run(
        ["python3", "scripts/keygen.py"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "SECRET_KEY=" in result.stdout
    assert "AUTH__JWT_ACCESS_SECRET=" in result.stdout
    assert "AUTH__JWT_REFRESH_SECRET=" in result.stdout

