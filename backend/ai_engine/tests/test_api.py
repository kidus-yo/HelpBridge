from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase
from rest_framework.test import APIClient

from courses.models import Course
from knowledge.models import ContentChunk, KnowledgeDocument
from platforms.tests.factories import context_token, make_integration, make_institution


class AIAnswerAPITests(TestCase):
    def setUp(self):
        self.integration = make_integration()
        self.course = Course.objects.create(
            institution_id=self.integration.institution_id,
            title="Published course",
            slug="published-course",
            status=Course.Status.PUBLISHED,
        )
        self.document = KnowledgeDocument.objects.create(
            institution_id=self.integration.institution_id,
            course=self.course,
            original_filename="course-material.txt",
            document_type="txt",
            language="en",
            processing_status=KnowledgeDocument.ProcessingStatus.COMPLETED,
            storage_ref="test-only",
            checksum="answer-api-test",
            byte_size=60,
        )
        ContentChunk.objects.create(
            document=self.document,
            institution_id=self.integration.institution_id,
            course=self.course,
            chunk_text=(
                "Virtual assistants use digital tools to work remotely with clients. "
                "Remote work is a major future trend for virtual assistants."
            ),
            chunk_index=0,
            page_number=2,
            section_heading="Remote work",
            language="en",
        )
        self.token = context_token(
            self.integration,
            context_type="course",
            context_id=str(self.course.id),
            preferred_language="en",
        )
        self.client = APIClient()

    def _authorize(self, token=None):
        if token:
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        else:
            self.client.credentials()

    def test_answer_endpoint_requires_authenticated_context(self):
        response = self.client.post(
            "/api/v1/ai/answer/",
            {"question": "How do virtual assistants work remotely?"},
            format="json",
        )
        self.assertIn(response.status_code, {401, 403})

    def test_answer_uses_signed_course_context_and_real_citation(self):
        self._authorize(self.token)
        response = self.client.post(
            "/api/v1/ai/answer/",
            {"question": "How do virtual assistants work remotely?"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["grounded"])
        self.assertEqual(response.data["citations"][0]["document_title"], "course-material.txt")
        self.assertEqual(response.data["citations"][0]["page"], 2)

    def test_request_cannot_override_signed_course_or_institution(self):
        other_institution = make_institution(slug="answer-other", name="Other")
        other_course = Course.objects.create(
            institution=other_institution,
            title="Other",
            slug="other",
            status=Course.Status.PUBLISHED,
        )
        self._authorize(self.token)
        response = self.client.post(
            "/api/v1/ai/answer/",
            {
                "question": "How do virtual assistants work remotely?",
                "course_id": str(other_course.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_context_without_knowledge_scope_is_rejected(self):
        token = context_token(
            self.integration,
            context_type="course",
            context_id=str(self.course.id),
            scopes=["courses:read"],
        )
        self._authorize(token)
        response = self.client.post(
            "/api/v1/ai/answer/",
            {"question": "How do virtual assistants work remotely?"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_tenant_knowledge_database_failure_is_not_returned_as_an_answer(self):
        self._authorize(self.token)
        with patch(
            "ai_engine.services.answer_service.search_course_content",
            side_effect=OperationalError("private database detail"),
        ):
            response = self.client.post(
                "/api/v1/ai/answer/",
                {"question": "How do virtual assistants work remotely?"},
                format="json",
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["error"]["code"], "knowledge_unavailable")
        self.assertNotIn("private database detail", str(response.data))
