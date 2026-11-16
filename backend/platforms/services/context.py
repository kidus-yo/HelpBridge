"""Trusted platform context for HelpBridge integrations.

The browser must never receive private integration secrets. A JavaScript embed
script is not authentication. LMS/job-portal servers mint short-lived signed
tokens using a hashed API key; HelpBridge validates issuer, audience, expiry,
signature, and scopes server-side.

The LLM must not invent tenant context. Other apps should call
`get_platform_context(request)` after DRF authentication has run.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from django.conf import settings
from django.utils.dateparse import parse_datetime

from common.languages import is_supported_language
from platforms.models import PlatformIntegration

CONTEXT_TYPES = ("course", "job", "application", "general", "support")
DEFAULT_SCOPES = [
    "courses:read",
    "knowledge:read",
]
TOKEN_AUDIENCE = "helpbridge"


class PlatformContextError(Exception):
    def __init__(self, message: str, code: str = "invalid_context"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PlatformContext:
    platform_id: UUID
    platform_type: str
    institution_id: UUID
    user_ref: str
    context_type: str
    context_id: str | None
    scopes: tuple[str, ...]
    preferred_language: str
    token_issuer: str
    token_audience: str
    token_expiry: datetime
    integration_id: UUID

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes or "admin" in self.scopes


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _signing_key() -> bytes:
    key = getattr(settings, "PLATFORM_CONTEXT_SIGNING_KEY", "") or settings.SECRET_KEY
    return key.encode("utf-8")


def _sign(body: str) -> str:
    digest = hmac.new(_signing_key(), body.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def issue_platform_context_token(
    *,
    integration: PlatformIntegration,
    user_ref: str,
    context_type: str = "general",
    context_id: str | None = None,
    scopes: list[str] | None = None,
    preferred_language: str = "en",
    ttl_seconds: int | None = None,
) -> str:
    if integration.status != PlatformIntegration.Status.ACTIVE:
        raise PlatformContextError("Integration is not active.", "inactive_integration")
    if not integration.platform.is_active or not integration.institution.is_active:
        raise PlatformContextError("Platform or institution is inactive.", "inactive_tenant")
    if context_type not in CONTEXT_TYPES:
        raise PlatformContextError("Unsupported context type.", "invalid_context_type")
    if not user_ref or len(user_ref) > 128:
        raise PlatformContextError("user_ref is required and must be pseudonymous.", "invalid_user_ref")
    if not is_supported_language(preferred_language):
        raise PlatformContextError("Unsupported preferred language.", "unsupported_language")
    language = preferred_language

    permitted = set(integration.permitted_scopes or DEFAULT_SCOPES)
    requested = list(scopes or permitted)
    if not set(requested).issubset(permitted):
        raise PlatformContextError("Requested scopes exceed permitted scopes.", "invalid_scopes")

    ttl = ttl_seconds or getattr(settings, "PLATFORM_CONTEXT_TTL_SECONDS", 900)
    now = datetime.now(timezone.utc)
    payload = {
        "iss": integration.platform.slug,
        "aud": TOKEN_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
        "platform_id": str(integration.platform_id),
        "platform_type": integration.platform.platform_type,
        "institution_id": str(integration.institution_id),
        "integration_id": str(integration.id),
        "user_ref": user_ref,
        "context_type": context_type,
        "context_id": context_id,
        "scopes": requested,
        "preferred_language": language,
    }
    body = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    return f"{body}.{_sign(body)}"


def parse_and_validate_token(token: str) -> PlatformContext:
    if not token or "." not in token:
        raise PlatformContextError("Malformed platform context token.", "malformed_token")
    body, _, signature = token.partition(".")
    expected = _sign(body)
    if not hmac.compare_digest(signature, expected):
        raise PlatformContextError("Invalid platform context signature.", "invalid_signature")

    try:
        payload: dict[str, Any] = json.loads(_b64url_decode(body))
    except (ValueError, json.JSONDecodeError) as exc:
        raise PlatformContextError("Malformed platform context payload.", "malformed_token") from exc

    if payload.get("aud") != TOKEN_AUDIENCE:
        raise PlatformContextError("Invalid token audience.", "invalid_audience")

    exp = payload.get("exp")
    now = datetime.now(timezone.utc)
    if not isinstance(exp, int) or datetime.fromtimestamp(exp, tz=timezone.utc) <= now:
        raise PlatformContextError("Platform context token has expired.", "expired_token")

    try:
        integration = (
            PlatformIntegration.objects.select_related("platform", "institution")
            .get(id=payload.get("integration_id"))
        )
    except PlatformIntegration.DoesNotExist as exc:
        raise PlatformContextError("Unknown integration.", "unknown_integration") from exc

    if integration.status != PlatformIntegration.Status.ACTIVE:
        raise PlatformContextError("Integration is not active.", "inactive_integration")
    if str(integration.platform_id) != str(payload.get("platform_id")):
        raise PlatformContextError("Token platform does not match integration.", "platform_mismatch")
    if str(integration.institution_id) != str(payload.get("institution_id")):
        raise PlatformContextError("Token institution does not match integration.", "institution_mismatch")
    if payload.get("iss") != integration.platform.slug:
        raise PlatformContextError("Invalid token issuer.", "invalid_issuer")

    scopes = tuple(payload.get("scopes") or [])
    permitted = set(integration.permitted_scopes or [])
    if not set(scopes).issubset(permitted):
        raise PlatformContextError("Token scopes are not permitted.", "invalid_scopes")

    context_type = payload.get("context_type") or "general"
    if context_type not in CONTEXT_TYPES:
        raise PlatformContextError("Unsupported context type.", "invalid_context_type")
    preferred_language = payload.get("preferred_language")
    if not is_supported_language(preferred_language):
        raise PlatformContextError("Unsupported preferred language.", "unsupported_language")

    expiry = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    return PlatformContext(
        platform_id=integration.platform_id,
        platform_type=integration.platform.platform_type,
        institution_id=integration.institution_id,
        user_ref=str(payload.get("user_ref") or ""),
        context_type=context_type,
        context_id=payload.get("context_id"),
        scopes=scopes,
        preferred_language=preferred_language,
        token_issuer=payload.get("iss") or "",
        token_audience=payload.get("aud") or "",
        token_expiry=expiry,
        integration_id=integration.id,
    )


def get_platform_context(request) -> PlatformContext | None:
    """Documented interface for other developers after authentication."""
    return getattr(request, "platform_context", None)


def parse_datetime_or_none(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = parse_datetime(value)
    return parsed
