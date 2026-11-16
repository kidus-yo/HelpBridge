"""End-to-End Plugin Integration Tests.
ALX Digital Bridge Accessibility Hackathon 2026 - Track 3

Verifies:
1. Static asset delivery of bridge.js
2. CORS headers on preflight OPTIONS and cross-origin API calls
3. Platform context token authentication and rejection
4. End-to-end conversation flow and evidence-grounded responses
5. Accessibility preferences synchronization
6. Error handling and failure boundaries
"""

import os
from pathlib import Path
from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import TestCase
from rest_framework.test import APIClient

from chat.models import ChatSession, Message
from accessibility.models import AccessibilityPreference
from platforms.tests.factories import context_token, make_integration


class PluginIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.integration = make_integration()

    def test_static_asset_bridge_js_discovery(self):
        """Verifies that bridge.js is discoverable by Django staticfiles."""
        result = finders.find("bridge.js")
        self.assertIsNotNone(result, "bridge.js must be found in STATICFILES_DIRS")
        self.assertTrue(os.path.exists(result))

        with open(result, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify key plugin interfaces and WCAG components exist
        self.assertIn("window.DigitalBridgeAssistant", content)
        self.assertIn("#digital-bridge-root", content)
        self.assertIn("db-live-announcer", content)
        self.assertIn("role=\"dialog\"", content)
        self.assertIn("aria-modal=\"true\"", content)
        self.assertIn("Authorization", content)

    def test_cors_preflight_options_for_chat_sessions(self):
        """External host platforms require CORS headers on OPTIONS preflights."""
        response = self.client.options(
            "/api/v1/chat/sessions/",
            HTTP_ORIGIN="http://localhost:3000",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="Authorization,Content-Type,X-HelpBridge-Context",
        )
        self.assertEqual(response.status_code, 200)
        allow_origin = response.headers.get("Access-Control-Allow-Origin")
        self.assertTrue(
            allow_origin in ("*", "http://localhost:3000"),
            f"Expected CORS allow origin header, got: {allow_origin}",
        )
        allow_methods = response.headers.get("Access-Control-Allow-Methods", "")
        self.assertIn("POST", allow_methods)

    def test_cors_headers_on_post_request(self):
        """Cross-origin POST requests from host pages must include CORS headers."""
        response = self.client.post(
            "/api/v1/chat/sessions/",
            {
                "channel": "web",
                "course_id": "course-va-101",
                "institution_id": "inst-default",
                "preferred_language": "en",
            },
            format="json",
            HTTP_ORIGIN="http://localhost:3000",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue("Access-Control-Allow-Origin" in response.headers)

    def test_plugin_session_with_valid_platform_token(self):
        """A host providing a signed PlatformContextToken securely binds tenant context."""
        token = context_token(
            self.integration,
            user_ref="learner-host-007",
            context_type="course",
            context_id="course-va-101",
            preferred_language="am",
        )

        response = self.client.post(
            "/api/v1/chat/sessions/",
            {
                "channel": "web",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        data = response.data
        self.assertEqual(data["preferred_language"], "am")
        self.assertEqual(data["course_id"], "course-va-101")
        self.assertEqual(data["institution_id"], str(self.integration.institution.id))

        # Check default accessibility preferences created in sync
        pref = AccessibilityPreference.objects.get(session_id=data["id"])
        self.assertEqual(pref.preferred_language, "am")

    def test_plugin_session_with_tampered_token_rejected(self):
        """Invalid or tampered tokens must fail with HTTP 401 Unauthorized."""
        response = self.client.post(
            "/api/v1/chat/sessions/",
            {"channel": "web"},
            format="json",
            HTTP_AUTHORIZATION="Bearer invalid.tampered.token.payload",
        )
        self.assertIn(response.status_code, {401, 403})

    def test_plugin_session_guest_fallback(self):
        """When no token is provided, the widget functions in guest mode with safe defaults."""
        response = self.client.post(
            "/api/v1/chat/sessions/",
            {
                "channel": "web",
                "course_id": "course-va-101",
                "institution_id": "inst-default",
                "preferred_language": "en",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["preferred_language"], "en")
        self.assertEqual(response.data["channel"], "web")

    def test_end_to_end_messaging_and_citations(self):
        """Learner message triggers AI grounding and returns structured citations."""
        # 1. Create session
        session_resp = self.client.post(
            "/api/v1/chat/sessions/",
            {"channel": "web", "preferred_language": "en"},
            format="json",
        )
        self.assertEqual(session_resp.status_code, 201)
        session_id = session_resp.data["id"]

        # 2. Send message
        msg_resp = self.client.post(
            f"/api/v1/chat/sessions/{session_id}/messages/",
            {"content": "How do I communicate with my client professionally?", "language": "en"},
            format="json",
        )
        self.assertEqual(msg_resp.status_code, 200)
        data = msg_resp.data

        self.assertIn("assistant_message", data)
        self.assertIn("learner_message", data)
        self.assertIn("citations", data)
        self.assertIn("grounded", data)

        # Check assistant message has content and metadata
        ast_msg = data["assistant_message"]
        self.assertTrue(len(ast_msg["content"]) > 0)
        self.assertIn("metadata", ast_msg)

        # Verify database persistence
        db_messages = Message.objects.filter(session_id=session_id).order_by("created_at")
        self.assertEqual(db_messages.count(), 2)
        self.assertEqual(db_messages[0].sender_type, "learner")
        self.assertEqual(db_messages[1].sender_type, "assistant")

    def test_accessibility_preference_patch_and_get(self):
        """Host and widget can update accessibility modes and query them."""
        session_resp = self.client.post(
            "/api/v1/chat/sessions/",
            {"channel": "web", "preferred_language": "en"},
            format="json",
        )
        session_id = session_resp.data["id"]

        # Patch preferences
        patch_resp = self.client.patch(
            f"/api/v1/accessibility/preferences/{session_id}/",
            {
                "high_contrast": True,
                "simple_mode": True,
                "text_size": "large",
                "preferred_language": "am",
            },
            format="json",
        )
        self.assertEqual(patch_resp.status_code, 200)
        self.assertTrue(patch_resp.data["high_contrast"])
        self.assertTrue(patch_resp.data["simple_mode"])
        self.assertEqual(patch_resp.data["text_size"], "large")
        self.assertEqual(patch_resp.data["preferred_language"], "am")

        # Session language must be synchronized
        session = ChatSession.objects.get(id=session_id)
        self.assertEqual(session.preferred_language, "am")

        # GET preferences
        get_resp = self.client.get(f"/api/v1/accessibility/preferences/{session_id}/")
        self.assertEqual(get_resp.status_code, 200)
        self.assertTrue(get_resp.data["high_contrast"])

    def test_failure_scenarios(self):
        """Failure and boundary cases are handled gracefully."""
        # Empty message
        session_resp = self.client.post(
            "/api/v1/chat/sessions/",
            {"channel": "web"},
            format="json",
        )
        session_id = session_resp.data["id"]

        empty_resp = self.client.post(
            f"/api/v1/chat/sessions/{session_id}/messages/",
            {"content": "   "},
            format="json",
        )
        self.assertEqual(empty_resp.status_code, 400)

        # Non-existent session
        bad_session_resp = self.client.post(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000/messages/",
            {"content": "Hello?"},
            format="json",
        )
        self.assertEqual(bad_session_resp.status_code, 404)

        # Oversized message (> 4000 characters)
        oversized = "a" * 4001
        large_resp = self.client.post(
            f"/api/v1/chat/sessions/{session_id}/messages/",
            {"content": oversized},
            format="json",
        )
        self.assertEqual(large_resp.status_code, 400)
