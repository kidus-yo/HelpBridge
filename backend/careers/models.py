"""
Models for Career Gateway, Job Opportunities, Accommodations, and Subscriptions.
"""

import uuid
from django.db import models
from django.conf import settings


class JobListing(models.Model):
    EMPLOYMENT_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('internship', 'Internship'),
        ('contract', 'Contract / Freelance'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft (Staff Only)'),
        ('published', 'Published (Learner Accessible)'),
        ('closed', 'Closed'),
    ]

    REMOTE_CHOICES = [
        ('remote', 'Fully Remote'),
        ('hybrid', 'Hybrid'),
        ('on_site', 'On-Site'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, db_index=True)
    organization = models.CharField(max_length=255, db_index=True)
    description = models.TextField()
    location = models.CharField(max_length=255)
    employment_type = models.CharField(max_length=32, choices=EMPLOYMENT_CHOICES, default='full_time')
    remote_policy = models.CharField(max_length=32, choices=REMOTE_CHOICES, default='on_site')
    application_url = models.URLField(max_length=500, blank=True)
    contact_instructions = models.TextField(blank=True)
    required_skills = models.JSONField(default=list, blank=True)
    salary_info = models.CharField(max_length=255, blank=True, help_text="Published salary if provided.")
    deadline = models.DateField(null=True, blank=True)
    source_url = models.URLField(max_length=500, blank=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='draft', db_index=True)
    is_demo = models.BooleanField(default=True, help_text="Flags demo/sample hackathon postings transparently.")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='posted_jobs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} at {self.organization} ({self.status})"


class AccommodationRequest(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('reviewing', 'Reviewing'),
        ('responded', 'Responded / Accommodations Arranged'),
        ('closed', 'Closed'),
    ]

    CONTACT_CHOICES = [
        ('telegram', 'Telegram'),
        ('sms', 'SMS'),
        ('email', 'Email'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='accommodation_requests'
    )
    guest_token = models.CharField(max_length=64, blank=True, db_index=True)
    job_listing = models.ForeignKey(
        JobListing,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='accommodations'
    )

    # Privacy-First: Functional adjustment requests ONLY (NO medical diagnosis)
    functional_needs = models.JSONField(
        default=list,
        help_text="Functional adjustments required (e.g. screen reader compatible environment, extra time, captions)"
    )
    description = models.TextField(
        help_text="Specific functional requests or setup requirements."
    )
    preferred_contact_method = models.CharField(
        max_length=16,
        choices=CONTACT_CHOICES,
        default='email'
    )
    contact_details = models.CharField(max_length=255)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='submitted', db_index=True)
    coordinator_response = models.TextField(blank=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='handled_accommodations'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AccommodationRequest {self.id} [{self.status}]"


class JobAlertSubscription(models.Model):
    CHANNEL_CHOICES = [
        ('telegram', 'Telegram'),
        ('sms', 'SMS'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='job_alert_subscriptions'
    )
    guest_token = models.CharField(max_length=64, blank=True, db_index=True)
    contact_identity = models.CharField(
        max_length=255,
        help_text="Verified destination: Telegram Chat ID or Phone number for SMS."
    )
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES, default='telegram')
    keywords = models.JSONField(
        default=list,
        blank=True,
        help_text="Search keywords / skill tags for job matching."
    )
    location_preference = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Subscription {self.id} ({self.channel}: {self.contact_identity})"
