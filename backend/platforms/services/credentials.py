from __future__ import annotations

import hashlib
import hmac
import secrets

from django.contrib.auth.hashers import check_password, make_password

API_KEY_PREFIX = "hb_"


def generate_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(raw_key: str) -> str:
    return make_password(raw_key)


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    return check_password(raw_key, stored_hash)


def key_prefix(raw_key: str) -> str:
    return raw_key[:12]


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(left.encode()).digest(),
        hashlib.sha256(right.encode()).digest(),
    )
