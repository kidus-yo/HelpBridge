from __future__ import annotations

import hashlib
import logging
from typing import BinaryIO

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from courses.models import Course, Lesson
from knowledge.chunking import split_pages
from knowledge.embeddings import get_embedding_provider
from knowledge.extraction import ExtractionError, extract_pages
from knowledge.models import ContentChunk, DocumentProcessingJob, KnowledgeDocument
from knowledge.storage import get_document_storage
from platforms.services.context import get_platform_context
from platforms.tenant import get_institution, is_staff

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/x-pdf": "pdf",
    "text/plain": "txt",
}
ALLOWED_EXTENSIONS = {".pdf": "pdf", ".txt": "txt"}


def _can_write(request) -> bool:
    if is_staff(request):
        return True
    context = get_platform_context(request)
    return bool(context and context.has_scope("knowledge:write"))


def _can_process(request) -> bool:
    if is_staff(request):
        return True
    context = get_platform_context(request)
    return bool(
        context
        and (context.has_scope("knowledge:write") or context.has_scope("knowledge:process"))
    )


def _detect_type(filename: str, content_type: str | None) -> str:
    name = (filename or "").lower()
    for ext, dtype in ALLOWED_EXTENSIONS.items():
        if name.endswith(ext):
            return dtype
    if content_type in ALLOWED_TYPES:
        return ALLOWED_TYPES[content_type]
    raise ValidationError(
        {"file": "Unsupported file type. Upload a PDF or UTF-8 TXT file. Scanned PDFs require OCR, which is not implemented."}
    )


def store_upload(request, *, uploaded_file: BinaryIO, institution_id=None, course_id=None, lesson_id=None, language="en", consent_to_external_ai=False) -> KnowledgeDocument:
    if not _can_write(request):
        raise PermissionDenied("Missing knowledge:write scope.")

    filename = getattr(uploaded_file, "name", "upload.bin")
    content_type = getattr(uploaded_file, "content_type", "")
    document_type = _detect_type(filename, content_type)
    content = uploaded_file.read()
    max_bytes = int(getattr(settings, "DOCUMENT_MAX_UPLOAD_MB", 10)) * 1024 * 1024
    if len(content) == 0:
        raise ValidationError({"file": "The uploaded file is empty."})
    if len(content) > max_bytes:
        raise ValidationError({"file": f"File exceeds the {settings.DOCUMENT_MAX_UPLOAD_MB} MB limit."})

    institution = get_institution(request, institution_id)
    course = None
    lesson = None
    if course_id:
        try:
            course = Course.objects.get(id=course_id, institution=institution)
        except Course.DoesNotExist as exc:
            raise ValidationError({"course_id": "Course not found for this institution."}) from exc
    if lesson_id:
        try:
            lesson = Lesson.objects.select_related("section__course").get(id=lesson_id)
        except Lesson.DoesNotExist as exc:
            raise ValidationError({"lesson_id": "Lesson not found."}) from exc
        if lesson.section.course.institution_id != institution.id:
            raise PermissionDenied("Lesson does not belong to this institution.")
        if course and lesson.section.course_id != course.id:
            raise ValidationError({"lesson_id": "Lesson does not belong to the given course."})
        course = course or lesson.section.course

    checksum = hashlib.sha256(content).hexdigest()
    document = KnowledgeDocument(
        institution=institution,
        course=course,
        lesson=lesson,
        original_filename=filename,
        document_type=document_type,
        language=language or "en",
        processing_status=KnowledgeDocument.ProcessingStatus.PENDING,
        storage_ref="",
        checksum=checksum,
        byte_size=len(content),
        metadata={"content_type": content_type},
        consent_to_external_ai=bool(consent_to_external_ai),
    )
    document.save()
    storage = get_document_storage()
    storage_ref = storage.save(str(institution.id), str(document.id), filename, content)
    document.storage_ref = storage_ref
    document.save(update_fields=["storage_ref", "updated_at"])
    DocumentProcessingJob.objects.create(document=document)
    logger.info("Stored knowledge document %s (%s bytes)", document.id, len(content))
    return document


def get_owned_document(request, document_id) -> KnowledgeDocument:
    qs = KnowledgeDocument.objects.select_related("institution", "course", "lesson")
    context = get_platform_context(request)
    if context is not None:
        qs = qs.filter(institution_id=context.institution_id)
    elif not is_staff(request):
        qs = qs.none()
    try:
        return qs.get(id=document_id)
    except KnowledgeDocument.DoesNotExist as exc:
        raise PermissionDenied("Document not found for this tenant.") from exc


def process_document(request, document: KnowledgeDocument) -> KnowledgeDocument:
    if not _can_process(request):
        raise PermissionDenied("Missing knowledge processing permission.")

    job = (
        DocumentProcessingJob.objects.filter(document=document)
        .order_by("-created_at")
        .first()
    )
    if job is None:
        job = DocumentProcessingJob.objects.create(document=document)

    job.status = DocumentProcessingJob.Status.RUNNING
    job.started_at = timezone.now()
    job.error_code = ""
    job.error_message = ""
    job.save(update_fields=["status", "started_at", "error_code", "error_message", "updated_at"])

    document.processing_status = KnowledgeDocument.ProcessingStatus.PROCESSING
    document.save(update_fields=["processing_status", "updated_at"])

    try:
        storage = get_document_storage()
        content = storage.read(document.storage_ref)
        pages = extract_pages(content, document.document_type)
        chunks = split_pages(pages)
        if not chunks:
            raise ExtractionError("No chunks could be created from the document.", "empty_chunks")

        provider = get_embedding_provider()
        embeddings = provider.embed_texts([chunk.text for chunk in chunks])

        ContentChunk.objects.filter(document=document).delete()
        ContentChunk.objects.bulk_create(
            [
                ContentChunk(
                    document=document,
                    institution=document.institution,
                    course=document.course,
                    chunk_text=chunk.text,
                    chunk_index=chunk.index,
                    page_number=chunk.page_number,
                    section_heading=chunk.section_heading,
                    language=document.language,
                    metadata=chunk.metadata,
                    embedding=embeddings[index] or None,
                    embedding_provider=provider.name if embeddings[index] else "",
                )
                for index, chunk in enumerate(chunks)
            ]
        )
        document.processing_status = KnowledgeDocument.ProcessingStatus.COMPLETED
        document.processed_at = timezone.now()
        document.save(update_fields=["processing_status", "processed_at", "updated_at"])
        job.status = DocumentProcessingJob.Status.SUCCEEDED
        job.finished_at = timezone.now()
        job.stats = {"chunk_count": len(chunks), "page_count": len(pages)}
        job.save(update_fields=["status", "finished_at", "stats", "updated_at"])
        logger.info("Processed document %s into %s chunks", document.id, len(chunks))
        return document
    except ExtractionError as exc:
        _mark_failed(document, job, exc.code, str(exc))
        raise ValidationError({"detail": str(exc)}) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Document processing failed for %s", document.id)
        _mark_failed(document, job, "processing_failed", "Document processing failed.")
        raise ValidationError({"detail": "Document processing failed."}) from exc


def _mark_failed(document: KnowledgeDocument, job: DocumentProcessingJob, code: str, message: str) -> None:
    document.processing_status = KnowledgeDocument.ProcessingStatus.FAILED
    document.processed_at = timezone.now()
    document.save(update_fields=["processing_status", "processed_at", "updated_at"])
    job.status = DocumentProcessingJob.Status.FAILED
    job.finished_at = timezone.now()
    job.error_code = code
    job.error_message = message
    job.save(update_fields=["status", "finished_at", "error_code", "error_message", "updated_at"])
