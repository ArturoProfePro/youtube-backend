from typing import Final

from argon2 import PasswordHasher

_ph = PasswordHasher()


def generate_hash(data: str) -> str:
    return _ph.hash(data)


def verify_hash(hash: str, data: str):
    _ph.verify(hash, data)


DUMMY_HASH: Final[str] = (
    '$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$Q29ycmVjdEhhc2hGb3JEdW1teVBhc3N3b3Jk'  # Твой реальный формат хэша
)


def dummy_hash(data: str):
    try:
        verify_hash(hash=DUMMY_HASH, data=data)
    except Exception:
        pass
