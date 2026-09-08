import secrets
from slugify import slugify


def generate_slug(title: str) -> str:
    base = slugify(title)
    suffix = secrets.token_hex(2)
    return f'{base}-{suffix}'
