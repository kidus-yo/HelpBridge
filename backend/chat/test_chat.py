from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from chat.models import ChatSession, Message
from courses.models import Course
from ai_engine.services.answer_service import KnowledgeRetrievalUnavailable
from knowledge.models import ContentChunk, KnowledgeDocument
from platforms.tests.factories import context_token, make_integration, make_institution


class ChatAPITests(APITestCase):
    def setUp(self):
        self.integration = make_integration()
        self.course = Course.objects.create(
            institution_id=self.integration.institution_id,
            title="Virtual Assistant Foundations",
            slug="va-foundations",
            language="en",
            status=Course.Status.PUBLISHED,
        )
        self._create_document(
            "The Future of the VA Industry - VA-1",
            "en",
            (
                "Artificial intelligence shapes future virtual assistant work by "
                "automating routine tasks and helping workers serve clients remotely. "
                "Remote work is a major future trend in the virtual assistant industry."
            ),
        )
        self._create_document(
            "የረዳት ሥራ የወደፊት ዕድል",
            "am",
            (
                "ሰው ሰራሽ አስተውሎት የቨርቹዋል ረዳቶችን ሥራ ይቀርጸዋል። "
                "የቨርቹዋል ረዳት ሥራ የወደፊት ዕድል በዲጂታል መሣሪያዎች ይደገፋል።"
            ),
        )
        self.token = context_token(
            self.integration,
            context_type="course",
            context_id=str(self.course.id),
            preferred_language="en",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        self.session = self._create_session()

    def _create_document(self, filename, language, text):
        document = KnowledgeDocument.objects.create(
            institution_id=self.integration.institution_id,
            course=self.course,
            original_filename=filename,
            document_type="txt",
            language=language,
            processing_status=KnowledgeDocument.ProcessingStatus.COMPLETED,
            storage_ref="test-only",
            checksum=f"{language}-{filename}",
            byte_size=len(text.encode("utf-8")),
        )
        ContentChunk.objects.create(
            document=document,
            institution_id=self.integration.institution_id,
            course=self.course,
            chunk_text=text,
            chunk_index=0,
            page_number=1,
            section_heading="Future of virtual assistant work",
            language=language,
        )

    def _create_session(self, language=None, token=None, client=None):
        request_client = client or self.client
        if token:
            request_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = request_client.post(
            reverse("chat-session-list-create"),
            {
                "channel": "web",
                **({"preferred_language": language} if language else {}),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return ChatSession.objects.get(id=response.data["id"])

    def test_create_session_uses_authenticated_tenant_and_identity(self):
        response = self.client.post(
            reverse("chat-session-list-create"),
            {"channel": "web", "preferred_language": "en"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session = ChatSession.objects.get(id=response.data["id"])
        self.assertEqual(session.institution_id, str(self.integration.institution_id))
        self.assertEqual(session.course_id, str(self.course.id))
        self.assertEqual(session.platform_integration_id, self.integration.id)
        self.assertEqual(session.platform_user_ref, "learner-anon-1")
        self.assertIsNotNone(session.accessibility_preference)

    def test_client_cannot_override_signed_institution_or_course(self):
        other_institution = make_institution(slug="other-chat", name="Other Chat")
        other_course = Course.objects.create(
            institution=other_institution,
            title="Other Course",
            slug="other-course",
            status=Course.Status.PUBLISHED,
        )
        response = self.client.post(
            reverse("chat-session-list-create"),
            {
                "institution_id": str(other_institution.id),
                "course_id": str(other_course.id),
            },
            format="json",
        )
        self.assertIn(response.status_code, {400, 403})

    def test_session_course_must_be_published_and_in_authenticated_tenant(self):
        draft = Course.objects.create(
            institution_id=self.integration.institution_id,
            title="Draft Course",
            slug="draft-course",
            status=Course.Status.DRAFT,
        )
        draft_token = context_token(
            self.integration,
            context_type="course",
            context_id=str(draft.id),
        )
        client = self.client_class()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {draft_token}")
        response = client.post(
            reverse("chat-session-list-create"),
            {"channel": "web"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_message_returns_database_evidence_and_citations(self):
        url = reverse("chat-message-list-create", kwargs={"session_id": self.session.id})
        response = self.client.post(
            url,
            {"content": "How is AI shaping future virtual assistant work?"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["grounded"])
        self.assertEqual(response.data["answer_status"], "available")
        self.assertGreater(len(response.data["citations"]), 0)
        self.assertEqual(
            response.data["citations"][0]["document_title"],
            "The Future of the VA Industry - VA-1",
        )
        self.assertEqual(self.session.messages.count(), 2)

    def test_amharic_question_uses_amharic_course_chunk(self):
        session = self._create_session(language="am")
        url = reverse("chat-message-list-create", kwargs={"session_id": session.id})
        response = self.client.post(
            url,
            {"content": "ሰው ሰራሽ አስተውሎት የቨርቹዋል ረዳቶችን ሥራ እንዴት ይቀርጸዋል?"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["grounded"])
        self.assertEqual(response.data["assistant_message"]["language"], "am")
        self.assertIn("የረዳት ሥራ", response.data["citations"][0]["document_title"])

    def test_no_evidence_returns_honest_refusal_without_citation(self):
        url = reverse("chat-message-list-create", kwargs={"session_id": self.session.id})
        response = self.client.post(
            url,
            {"content": "Quantum physics astrophysics thermodynamics"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["grounded"])
        self.assertEqual(response.data["citations"], [])

    def test_retrieval_failure_is_explicit_and_learner_message_is_persisted(self):
        url = reverse("chat-message-list-create", kwargs={"session_id": self.session.id})
        with patch(
            "chat.services._answer_service.answer_question",
            side_effect=KnowledgeRetrievalUnavailable("database detail must not be returned"),
        ):
            response = self.client.post(
                url,
                {"content": "How is AI shaping the future?"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["answer_status"], "unavailable")
        self.assertFalse(response.data["fallback_used"])
        self.assertEqual(self.session.messages.count(), 2)
        self.assertNotIn("database detail", response.data["assistant_message"]["content"])

    def test_anonymous_cannot_list_or_retrieve_chat_sessions(self):
        client = self.client_class()
        listing = client.get(reverse("chat-session-list-create"))
        detail = client.get(
            reverse("chat-session-detail", kwargs={"session_id": self.session.id})
        )
        history = client.get(
            reverse("chat-message-list-create", kwargs={"session_id": self.session.id})
        )
        self.assertIn(listing.status_code, {401, 403})
        self.assertIn(detail.status_code, {401, 403})
        self.assertIn(history.status_code, {401, 403})

    def test_platform_user_cannot_access_another_users_session(self):
        other_token = context_token(
            self.integration,
            user_ref="different-learner",
            context_type="course",
            context_id=str(self.course.id),
        )
        other_client = self.client_class()
        other_client.credentials(HTTP_AUTHORIZATION=f"Bearer {other_token}")
        other_session = self._create_session(token=other_token, client=other_client)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        detail = self.client.get(
            reverse("chat-session-detail", kwargs={"session_id": other_session.id})
        )
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_knowledge_scope_is_rejected(self):
        read_courses_only = context_token(
            self.integration,
            context_type="course",
            context_id=str(self.course.id),
            scopes=["courses:read"],
        )
        client = self.client_class()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {read_courses_only}")
        response = client.get(reverse("chat-session-list-create"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
