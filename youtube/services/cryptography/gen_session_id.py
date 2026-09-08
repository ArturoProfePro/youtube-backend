import secrets


def generate_session_id(length: int = 32) -> str:
    return secrets.token_urlsafe(length)
