from django.test import TestCase
from rest_framework.test import APIClient

from courses.models import Course
from platforms.tests.factories import context_token, make_integration, staff_user


class CourseApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = staff_user("course-admin")
        self.a = make_integration()
        self.b = make_integration(
            platform=self.a.platform,
            institution=__import__("platforms.tests.factories", fromlist=["make_institution"]).make_institution(
                slug="inst-b", name="Institution B"
            ),
        )
        self.token_a = context_token(self.a)
        self.token_b = context_token(self.b)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_create_update_list_and_publish_rules(self):
        self._auth(self.token_a)
        created = self.client.post(
            "/api/v1/courses/",
            {
                "title": "VA 101",
                "slug": "va-101",
                "description": "Virtual assistant basics",
                "language": "en",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        course_id = created.data["id"]
        self.assertEqual(created.data["status"], "draft")
        self.assertEqual(created.data["institution"], str(self.a.institution_id))

        listed_as_reader = APIClient()
        reader_token = context_token(self.a, user_ref="reader", scopes=["courses:read", "knowledge:read"])
        listed_as_reader.credentials(HTTP_AUTHORIZATION=f"Bearer {reader_token}")
        hidden = listed_as_reader.get("/api/v1/courses/")
        self.assertEqual(hidden.status_code, 200)
        self.assertEqual(hidden.data, [])

        published = self.client.post(f"/api/v1/courses/{course_id}/publish/")
        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.data["status"], "published")
        visible = listed_as_reader.get("/api/v1/courses/")
        self.assertEqual(len(visible.data), 1)

        patched = self.client.patch(
            f"/api/v1/courses/{course_id}/",
            {"title": "VA 101 Updated"},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.data["title"], "VA 101 Updated")

        unpublished = self.client.post(f"/api/v1/courses/{course_id}/unpublish/")
        self.assertEqual(unpublished.data["status"], Course.Status.DRAFT)

    def test_section_and_lesson_ownership(self):
        self._auth(self.token_a)
        course = self.client.post(
            "/api/v1/courses/",
            {"title": "Owned", "slug": "owned", "language": "am"},
            format="json",
        ).data
        section = self.client.post(
            f"/api/v1/courses/{course['id']}/sections/",
            {"title": "Week 1", "position": 1},
            format="json",
        )
        self.assertEqual(section.status_code, 201)
        lesson = self.client.post(
            f"/api/v1/sections/{section.data['id']}/lessons/",
            {"title": "Intro", "lesson_type": "text", "content": "Hello", "language": "am"},
            format="json",
        )
        self.assertEqual(lesson.status_code, 201)
        self._auth(self.token_b)
        stolen_section = self.client.get(f"/api/v1/courses/{course['id']}/sections/")
        self.assertIn(stolen_section.status_code, {403, 404})
        stolen_lesson = self.client.post(
            f"/api/v1/sections/{section.data['id']}/lessons/",
            {"title": "Hijack", "language": "en"},
            format="json",
        )
        self.assertIn(stolen_lesson.status_code, {403, 404})

    def test_cross_tenant_course_access_is_rejected(self):
        self._auth(self.token_a)
        course = self.client.post(
            "/api/v1/courses/",
            {"title": "Secret", "slug": "secret", "language": "en"},
            format="json",
        ).data
        self.client.post(f"/api/v1/courses/{course['id']}/publish/")
        self._auth(self.token_b)
        response = self.client.get(f"/api/v1/courses/{course['id']}/")
        self.assertIn(response.status_code, {403, 404})
        listed = self.client.get("/api/v1/courses/")
        ids = [row["id"] for row in listed.data]
        self.assertNotIn(course["id"], ids)

    def test_invalid_language_rejected(self):
        self._auth(self.token_a)
        response = self.client.post(
            "/api/v1/courses/",
            {"title": "Bad", "slug": "bad", "language": "xx"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
