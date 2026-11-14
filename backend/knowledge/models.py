from django.db import models

from common.languages import LANGUAGE_CHOICES
from common.models import TimeStampedUUIDModel
from courses.models import Course, Lesson
from platforms.models import Institution


class KnowledgeDocument(TimeStampedUUIDModel):
    class DocumentType(models.TextChoices):
        PDF = "pdf", "PDF"
        TXT = "txt", "Plain text"

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="knowledge_documents"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_documents",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_documents",
    )
    original_filename = models.CharField(max_length=255)
    document_type = models.CharField(max_length=16, choices=DocumentType.choices)
    language = models.CharField(max_length=8, choices=LANGUAGE_CHOICES, default="en")
    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )
    storage_ref = models.CharField(max_length=512)
    checksum = models.CharField(max_length=64)
    byte_size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    consent_to_external_ai = models.BooleanField(default=False)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["institution", "processing_status"]),
            models.Index(fields=["institution", "course"]),
            models.Index(fields=["checksum"]),
        ]

    def __str__(self) -> str:
        return self.original_filename


class ContentChunk(TimeStampedUUIDModel):
    document = models.ForeignKey(
        KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks"
    )
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="content_chunks"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="content_chunks",
    )
    chunk_text = models.TextField()
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    section_heading = models.CharField(max_length=255, blank=True)
    language = models.CharField(max_length=8, choices=LANGUAGE_CHOICES, default="en")
    metadata = models.JSONField(default=dict, blank=True)
    embedding = models.JSONField(null=True, blank=True)
    embedding_provider = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="uniq_chunk_index_per_document",
            )
        ]
        indexes = [
            models.Index(fields=["institution", "language"]),
            models.Index(fields=["institution", "course"]),
        ]

    def __str__(self) -> str:
        return f"{self.document_id}:{self.chunk_index}"


class DocumentProcessingJob(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    document = models.ForeignKey(
        KnowledgeDocument, on_delete=models.CASCADE, related_name="jobs"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.QUEUED
    )
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    stats = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
