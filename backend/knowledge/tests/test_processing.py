from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from knowledge.models import ContentChunk, KnowledgeDocument
from knowledge.tests.test_pdf_helpers import minimal_text_pdf
from platforms.tests.factories import context_token, make_institution, make_integration


class DocumentProcessingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.a = make_integration()
        self.b = make_integration(
            platform=self.a.platform,
            institution=make_institution(slug="kb-b", name="KB B"),
        )
        self.token_a = context_token(self.a)
        self.token_b = context_token(self.b)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

    def _create_course(self, token=None, slug="va-101"):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token or self.token_a}")
        return client.post(
            "/api/v1/courses/",
            {"title": "VA", "slug": slug, "language": "en"},
            format="json",
        ).data

    def test_txt_upload_validation_processing_and_chunks(self):
        course = self._create_course()
        payload = SimpleUploadedFile(
            "module.txt",
            b"Introduction\n\nHelpBridge answers questions from course content with citations.",
            content_type="text/plain",
        )
        uploaded = self.client.post(
            "/api/v1/documents/",
            {"file": payload, "course_id": course["id"], "language": "en"},
            format="multipart",
        )
        self.assertEqual(uploaded.status_code, 201)
        self.assertEqual(uploaded.data["processing_status"], "pending")
        self.assertNotIn("storage_ref", uploaded.data)
        doc_id = uploaded.data["id"]

        processed = self.client.post(f"/api/v1/documents/{doc_id}/process/")
        self.assertEqual(processed.status_code, 200)
        self.assertEqual(processed.data["processing_status"], "completed")
        self.assertGreaterEqual(processed.data["chunk_count"], 1)

        document = KnowledgeDocument.objects.get(id=doc_id)
        chunk = ContentChunk.objects.get(document=document)
        self.assertEqual(chunk.institution_id, self.a.institution_id)
        self.assertEqual(chunk.course_id, document.course_id)
        self.assertIn("HelpBridge", chunk.chunk_text)
        self.assertEqual(chunk.page_number, 1)

    def test_pdf_upload_extracts_text_and_page_number(self):
        pdf = minimal_text_pdf("Introduction to HelpBridge citations")
        payload = SimpleUploadedFile("course.pdf", pdf, content_type="application/pdf")
        uploaded = self.client.post("/api/v1/documents/", {"file": payload, "language": "en"}, format="multipart")
        self.assertEqual(uploaded.status_code, 201)
        processed = self.client.post(f"/api/v1/documents/{uploaded.data['id']}/process/")
        self.assertEqual(processed.status_code, 200, processed.data)
        chunk = ContentChunk.objects.get(document_id=uploaded.data["id"])
        self.assertEqual(chunk.page_number, 1)
        self.assertIn("HelpBridge", chunk.chunk_text)

    def test_rejects_unsupported_type_and_oversize(self):
        exe = SimpleUploadedFile("payload.exe", b"MZ", content_type="application/octet-stream")
        bad = self.client.post("/api/v1/documents/", {"file": exe}, format="multipart")
        self.assertEqual(bad.status_code, 400)

        with override_settings(DOCUMENT_MAX_UPLOAD_MB=0):
            txt = SimpleUploadedFile("a.txt", b"hello world", content_type="text/plain")
            oversized = self.client.post("/api/v1/documents/", {"file": txt}, format="multipart")
            self.assertEqual(oversized.status_code, 400)

    def test_empty_pdf_is_marked_failed(self):
        from io import BytesIO
        from pypdf import PdfWriter

        buffer = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(buffer)
        payload = SimpleUploadedFile("blank.pdf", buffer.getvalue(), content_type="application/pdf")
        uploaded = self.client.post("/api/v1/documents/", {"file": payload}, format="multipart")
        processed = self.client.post(f"/api/v1/documents/{uploaded.data['id']}/process/")
        self.assertEqual(processed.status_code, 400)
        document = KnowledgeDocument.objects.get(id=uploaded.data["id"])
        self.assertEqual(document.processing_status, KnowledgeDocument.ProcessingStatus.FAILED)

    def test_cross_tenant_document_access_is_rejected(self):
        payload = SimpleUploadedFile("a.txt", b"private notes for institution A", content_type="text/plain")
        uploaded = self.client.post("/api/v1/documents/", {"file": payload}, format="multipart")
        self.client.post(f"/api/v1/documents/{uploaded.data['id']}/process/")
        other = APIClient()
        other.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        response = other.get(f"/api/v1/documents/{uploaded.data['id']}/")
        self.assertIn(response.status_code, {403, 404})
        process = other.post(f"/api/v1/documents/{uploaded.data['id']}/process/")
        self.assertIn(process.status_code, {403, 404})
