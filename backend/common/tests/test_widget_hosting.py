from django.contrib.staticfiles import finders
from django.test import TestCase, override_settings


class WidgetHostingTests(TestCase):
    def test_widget_is_discoverable_as_a_static_asset(self):
        self.assertIsNotNone(finders.find("widget/bridge.js"))

    @override_settings(CORS_ALLOWED_ORIGINS=["https://lms.example"])
    def test_allowed_host_can_make_widget_preflight_request(self):
        response = self.client.options(
            "/api/v1/chat/sessions/",
            HTTP_ORIGIN="https://lms.example",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            response["Access-Control-Allow-Origin"],
            "https://lms.example",
        )
        self.assertIn("Authorization", response["Access-Control-Allow-Headers"])
        self.assertNotIn("Access-Control-Allow-Credentials", response)

    @override_settings(CORS_ALLOWED_ORIGINS=["https://lms.example"])
    def test_unlisted_host_does_not_receive_cors_access(self):
        response = self.client.options(
            "/api/v1/chat/sessions/",
            HTTP_ORIGIN="https://attacker.example",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )

        self.assertNotIn("Access-Control-Allow-Origin", response)
