from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from common.contracts import search_course_content
from platforms.tests.factories import context_token, make_institution, make_integration


class RetrievalTests(TestCase):
    def setUp(self):
        self.a = make_integration()
        self.b = make_integration(
            platform=self.a.platform,
            institution=make_institution(slug="ret-b", name="Ret B"),
        )
        self.token_a = context_token(self.a)
        self.token_b = context_token(self.b)
        self.client = APIClient()

    def _seed(self, token, text, language="en", slug="course"):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        course = client.post(
            "/api/v1/courses/",
            {"title": "Course", "slug": slug, "language": language},
            format="json",
        ).data
        payload = SimpleUploadedFile("material.txt", text.encode("utf-8"), content_type="text/plain")
        doc = client.post(
            "/api/v1/documents/",
            {"file": payload, "course_id": course["id"], "language": language},
            format="multipart",
        ).data
        processed = client.post(f"/api/v1/documents/{doc['id']}/process/")
        self.assertEqual(processed.status_code, 200, processed.data)
        return course, doc

    def test_search_filters_by_institution_course_and_language(self):
        course_a, _ = self._seed(self.token_a, "Introduction to virtual assistant remote work in Ethiopia.", slug="a-en")
        self._seed(self.token_a, "የስራ ማመልከቻ ሂደት", language="am", slug="a-am")
        self._seed(self.token_b, "Secret payroll information for institution B", slug="b-en")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.post(
            "/api/v1/knowledge/search/",
            {"query": "virtual assistant remote work", "limit": 5},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["count"], 1)
        for row in response.data["results"]:
            self.assertEqual(row["source"]["document_name"], "material.txt")
            self.assertIn("page", row["source"])
            self.assertNotIn("payroll", row["content"].lower())
            self.assertEqual(row["language"], "en")

        course_filtered = self.client.post(
            "/api/v1/knowledge/search/",
            {"query": "virtual assistant", "course_id": course_a["id"]},
            format="json",
        )
        self.assertEqual(course_filtered.status_code, 200)
        for row in course_filtered.data["results"]:
            self.assertEqual(row["course_id"], course_a["id"])

        amharic = self.client.post(
            "/api/v1/knowledge/search/",
            {"query": "ማመልከቻ", "language": "am"},
            format="json",
        )
        self.assertEqual(amharic.status_code, 200)
        for row in amharic.data["results"]:
            self.assertEqual(row["language"], "am")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        leaked = self.client.post(
            "/api/v1/knowledge/search/",
            {"query": "virtual assistant remote work", "institution_id": str(self.a.institution_id)},
            format="json",
        )
        self.assertEqual(leaked.status_code, 403)

        service_results = search_course_content(
            institution_id=self.a.institution_id,
            query="virtual assistant",
            course_id=course_a["id"],
            language="en",
            limit=3,
        )
        self.assertTrue(service_results)
        self.assertTrue(service_results[0]["source"]["document_id"])

        b_results = search_course_content(
            institution_id=self.b.institution_id,
            query="virtual assistant remote work",
        )
        self.assertEqual(b_results, [])
