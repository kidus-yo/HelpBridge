from datetime import datetime, timedelta, timezone

from django.test import TestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.test import APIRequestFactory, force_authenticate

from platforms.authentication import PlatformContextAuthentication
from platforms.models import PlatformIntegration
from platforms.services.context import (
    PlatformContextError,
    issue_platform_context_token,
    parse_and_validate_token,
)
from platforms.tenant import resolve_institution_id
from platforms.tests.factories import context_token, make_institution, make_integration, make_platform, staff_user


class PlatformContextTests(TestCase):
    def setUp(self):
        self.integration = make_integration()

    def test_valid_token_roundtrip(self):
        token = context_token(
            self.integration,
            context_type="course",
            context_id="course-1",
            preferred_language="am",
        )
        context = parse_and_validate_token(token)
        self.assertEqual(context.institution_id, self.integration.institution_id)
        self.assertEqual(context.platform_id, self.integration.platform_id)
        self.assertEqual(context.user_ref, "learner-anon-1")
        self.assertEqual(context.context_type, "course")
        self.assertEqual(context.preferred_language, "am")
        self.assertEqual(context.token_audience, "helpbridge")
        self.assertEqual(context.token_issuer, self.integration.platform.slug)

    def test_rejects_tampered_signature(self):
        token = context_token(self.integration)
        body, _, sig = token.partition(".")
        with self.assertRaises(PlatformContextError):
            parse_and_validate_token(f"{body}.{'a' * len(sig)}")

    def test_rejects_expired_token(self):
        token = issue_platform_context_token(
            integration=self.integration,
            user_ref="x",
            ttl_seconds=-10,
        )
        with self.assertRaises(PlatformContextError) as ctx:
            parse_and_validate_token(token)
        self.assertEqual(ctx.exception.code, "expired_token")

    def test_rejects_scope_escalation(self):
        with self.assertRaises(PlatformContextError):
            issue_platform_context_token(
                integration=self.integration,
                user_ref="x",
                scopes=["admin"],
            )

    def test_inactive_integration_cannot_issue(self):
        self.integration.status = PlatformIntegration.Status.REVOKED
        self.integration.save()
        with self.assertRaises(PlatformContextError):
            context_token(self.integration)

    def test_authentication_class_sets_request_context(self):
        token = context_token(self.integration)
        factory = APIRequestFactory()
        request = factory.get("/api/v1/platform-context/", HTTP_AUTHORIZATION=f"Bearer {token}")
        user, _ = PlatformContextAuthentication().authenticate(request)
        self.assertTrue(user.is_anonymous)
        self.assertEqual(request.platform_context.institution_id, self.integration.institution_id)

    def test_authentication_rejects_bad_token(self):
        factory = APIRequestFactory()
        request = factory.get("/api/v1/platform-context/", HTTP_AUTHORIZATION="Bearer not-a-token")
        with self.assertRaises(AuthenticationFailed):
            PlatformContextAuthentication().authenticate(request)

    def test_client_institution_id_cannot_override_context(self):
        other = make_institution(slug="other", name="Other")
        factory = APIRequestFactory()
        request = factory.get("/")
        request.platform_context = parse_and_validate_token(context_token(self.integration))
        request.user = None
        with self.assertRaises(PermissionDenied):
            resolve_institution_id(request, other.id)


class ProductionDatabaseSettingTests(TestCase):
    def setUp(self):
        self.integration = make_integration()

    @override_settings()
    def test_signing_key_is_not_an_api_key(self):
        token = context_token(self.integration)
        self.assertNotIn(self.integration.raw_api_key, token)
        self.assertFalse(self.integration.raw_api_key.startswith("eyJ"))
