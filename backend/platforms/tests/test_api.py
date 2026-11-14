from django.test import TestCase
from rest_framework.test import APIClient

from platforms.tests.factories import context_token, make_integration, staff_user


class PlatformApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = staff_user()
        self.integration = make_integration()

    def test_health_is_public(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.data["status"], {"ok", "degraded"})

    def test_unauthenticated_institution_list_is_rejected(self):
        response = self.client.get("/api/v1/institutions/")
        self.assertIn(response.status_code, {401, 403})

    def test_staff_can_create_platform_and_institution(self):
        self.client.force_authenticate(self.staff)
        platform = self.client.post(
            "/api/v1/platforms/",
            {
                "name": "Job Board",
                "slug": "jobs",
                "platform_type": "job_portal",
                "description": "Inclusive jobs",
            },
            format="json",
        )
        self.assertEqual(platform.status_code, 201)
        institution = self.client.post(
            "/api/v1/institutions/",
            {
                "name": "Mercy Corps",
                "slug": "mercy-corps",
                "institution_type": "ngo",
            },
            format="json",
        )
        self.assertEqual(institution.status_code, 201)
        created = self.client.post(
            "/api/v1/platform-integrations/",
            {
                "platform": platform.data["id"],
                "institution": institution.data["id"],
                "name": "prod",
                "permitted_scopes": ["courses:read", "knowledge:read"],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.data["api_key"].startswith("hb_"))
        listed = self.client.get(f"/api/v1/platform-integrations/")
        self.assertNotEqual(listed.status_code, 200)
        detail = self.client.get(f"/api/v1/institutions/{institution.data['id']}/")
        self.assertNotIn("api_key", detail.data)
        self.assertNotIn("api_key_hash", detail.data)

    def test_api_key_mints_context_token_and_browser_never_needs_secret(self):
        response = self.client.post(
            "/api/v1/platform-context/tokens/",
            {"user_ref": "anon-42", "context_type": "course", "preferred_language": "om"},
            format="json",
            HTTP_AUTHORIZATION=f"Api-Key {self.integration.raw_api_key}",
        )
        self.assertEqual(response.status_code, 201)
        token = response.data["token"]
        me = self.client.get(
            "/api/v1/platform-context/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["user_ref"], "anon-42")
        self.assertEqual(me.data["preferred_language"], "om")
        self.assertNotIn(self.integration.raw_api_key, str(me.data))

    def test_invalid_inputs_are_rejected(self):
        self.client.force_authenticate(self.staff)
        bad = self.client.post(
            "/api/v1/platforms/",
            {"name": "X", "slug": "x", "platform_type": "not-a-type"},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)

    def test_platform_context_sees_only_own_institution(self):
        other = make_integration(
            platform=self.integration.platform,
            institution=__import__("platforms.tests.factories", fromlist=["make_institution"]).make_institution(
                slug="other-inst", name="Other Inst"
            ),
        )
        token = context_token(self.integration)
        listed = self.client.get("/api/v1/institutions/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(listed.status_code, 200)
        ids = [row["id"] for row in listed.data]
        self.assertEqual(ids, [str(self.integration.institution_id)])
        self.assertNotIn(str(other.institution_id), ids)
