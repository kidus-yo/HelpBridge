from django.db import models

from common.languages import LANGUAGE_CHOICES
from common.models import TimeStampedUUIDModel
from platforms.models import Institution


class Course(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="courses"
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)
    language = models.CharField(max_length=8, choices=LANGUAGE_CHOICES, default="en")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "slug"],
                name="uniq_course_slug_per_institution",
            )
        ]
        indexes = [
            models.Index(fields=["institution", "status"]),
            models.Index(fields=["institution", "language"]),
        ]

    def __str__(self) -> str:
        return self.title


class CourseSection(TimeStampedUUIDModel):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="sections"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=8, choices=LANGUAGE_CHOICES, blank=True)

    class Meta:
        ordering = ["position", "created_at"]
        indexes = [models.Index(fields=["course", "position"])]

    def __str__(self) -> str:
        return self.title


class Lesson(TimeStampedUUIDModel):
    class LessonType(models.TextChoices):
        TEXT = "text", "Text"
        VIDEO = "video", "Video"
        DOCUMENT = "document", "Document"
        EXTERNAL = "external", "External resource"

    section = models.ForeignKey(
        CourseSection, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    lesson_type = models.CharField(
        max_length=20, choices=LessonType.choices, default=LessonType.TEXT
    )
    content = models.TextField(blank=True)
    external_url = models.URLField(blank=True)
    position = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=8, choices=LANGUAGE_CHOICES, default="en")

    class Meta:
        ordering = ["position", "created_at"]
        indexes = [models.Index(fields=["section", "position"])]

    def __str__(self) -> str:
        return self.title


class LessonResource(TimeStampedUUIDModel):
    class ResourceType(models.TextChoices):
        FILE = "file", "File"
        URL = "url", "External URL"
        DOCUMENT = "document", "Knowledge document"

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="resources"
    )
    resource_type = models.CharField(max_length=20, choices=ResourceType.choices)
    title = models.CharField(max_length=255)
    external_url = models.URLField(blank=True)
    file_ref = models.CharField(max_length=512, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
