#!/usr/bin/env python3
"""
Keygen script to generate cryptographically secure keys for JWT and application secrets.
Usage:
    python scripts/keygen.py
    python scripts/keygen.py --update-env
"""

import argparse
import re
import secrets
from pathlib import Path


def generate_keys():
    return {
        "SECRET_KEY": secrets.token_hex(32),
        "AUTH__JWT_ACCESS_SECRET": secrets.token_hex(32),
        "AUTH__JWT_REFRESH_SECRET": secrets.token_hex(32),
    }


def update_env_file(env_path: Path, keys: dict[str, str]):
    if not env_path.exists():
        print(f"Warning: {env_path} does not exist.")
        return

    content = env_path.read_text(encoding="utf-8")

    for key, value in keys.items():
        pattern = rf"^({re.escape(key)}\s*=\s*).*$"
        if re.search(pattern, content, flags=re.MULTILINE):
            content = re.sub(pattern, rf"\g<1>{value}", content, flags=re.MULTILINE)
        else:
            if key == "AUTH__JWT_ACCESS_SECRET":
                old_pat = r"^(AUTH__JWT_SECRET\s*=\s*).*$"
                if re.search(old_pat, content, flags=re.MULTILINE):
                    content = re.sub(old_pat, rf"AUTH__JWT_ACCESS_SECRET={value}", content, flags=re.MULTILINE)
                    continue
            if key == "AUTH__JWT_REFRESH_SECRET":
                old_pat = r"^(AUTH__REFRESH_JWT_SECRET\s*=\s*).*$"
                if re.search(old_pat, content, flags=re.MULTILINE):
                    content = re.sub(old_pat, rf"AUTH__JWT_REFRESH_SECRET={value}", content, flags=re.MULTILINE)
                    continue
            content += f"\n{key}={value}\n"

    env_path.write_text(content, encoding="utf-8")
    print(f"Updated secrets in {env_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate cryptographic keys for JWT and app secrets.")
    parser.add_argument("--update-env", action="store_true", help="Update .env file with new keys")
    parser.add_argument("--env-file", default=".env", help="Path to .env file (default: .env)")
    args = parser.parse_args()

    keys = generate_keys()

    print("=" * 60)
    print("Generated cryptographic secret keys (256-bit):")
    print("=" * 60)
    for key, val in keys.items():
        print(f"{key}={val}")
    print("=" * 60)

    if args.update_env:
        env_path = Path(args.env_file)
        update_env_file(env_path, keys)


if __name__ == "__main__":
    main()
