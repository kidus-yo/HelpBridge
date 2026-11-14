from django.db import models

from common.models import TimeStampedUUIDModel


class Platform(TimeStampedUUIDModel):
    class PlatformType(models.TextChoices):
        LMS = "lms", "LMS"
        JOB_PORTAL = "job_portal", "Job portal"
        CAREER_PORTAL = "career_portal", "Career portal"
        INCLUSIVE_RECRUITMENT = "inclusive_recruitment", "Inclusive recruitment platform"
        OTHER = "other", "Other"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=80, unique=True)
    platform_type = models.CharField(max_length=40, choices=PlatformType.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["platform_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class Institution(TimeStampedUUIDModel):
    class InstitutionType(models.TextChoices):
        TRAINING = "training", "Training institution"
        EMPLOYER = "employer", "Employer"
        UNIVERSITY = "university", "University"
        NGO = "ngo", "NGO / partner"
        OTHER = "other", "Other"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=80, unique=True)
    institution_type = models.CharField(max_length=40, choices=InstitutionType.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["institution_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class PlatformIntegration(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        REVOKED = "revoked", "Revoked"

    platform = models.ForeignKey(
        Platform, on_delete=models.PROTECT, related_name="integrations"
    )
    institution = models.ForeignKey(
        Institution, on_delete=models.PROTECT, related_name="integrations"
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    permitted_scopes = models.JSONField(default=list)
    api_key_hash = models.CharField(max_length=128)
    api_key_prefix = models.CharField(max_length=16)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["platform", "institution", "name"],
                name="uniq_platform_institution_integration_name",
            )
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["api_key_prefix"]),
        ]

    def __str__(self) -> str:
        return f"{self.institution.slug}:{self.platform.slug}:{self.name}"
