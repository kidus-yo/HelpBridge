"""
Models for Human Escalation, Live Help, Agent Triaging, and Learner-Controlled Screen Sharing.
"""

import uuid
from django.db import models
from django.conf import settings


class SupportRequest(models.Model):
    CATEGORY_CHOICES = [
        ('course', 'Course Content Help'),
        ('technical', 'Platform & Tech Issue'),
        ('accessibility', 'Accessibility & Assistive Tech Issue'),
        ('career', 'Career & Job Support'),
        ('other', 'General Inquiry'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open - Waiting for Agent'),
        ('assigned', 'Agent Assigned'),
        ('in_progress', 'In Conversation'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    PREFERRED_ASSISTANCE_CHOICES = [
        ('chat', 'Text Chat Only (Default)'),
        ('screen_share', 'Screen Sharing Requested'),
        ('low_bandwidth', 'Low-Bandwidth / Async SMS/Telegram'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='support_requests'
    )
    guest_token = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="Token for unauthenticated LMS guest sessions to access their own ticket."
    )
    institution_id = models.UUIDField(null=True, blank=True, db_index=True)
    chat_session_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Reference to Koket's chat session if escalated from automated tutor."
    )

    # Consent & Privacy
    learner_consent_chat_history = models.BooleanField(
        default=False,
        help_text="Explicit learner permission to let the agent review prior chat messages."
    )

    preferred_assistance_mode = models.CharField(
        max_length=20,
        choices=PREFERRED_ASSISTANCE_CHOICES,
        default='chat'
    )
    language = models.CharField(max_length=10, default='en')

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='course')
    subject = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)

    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_support_tickets'
    )

    # Learner-controlled screen sharing tracking
    screen_share_active = models.BooleanField(default=False)
    screen_share_token = models.CharField(max_length=64, blank=True)
    screen_share_started_at = models.DateTimeField(null=True, blank=True)
    screen_share_stopped_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"SupportRequest {self.id} [{self.status}]: {self.subject}"


class SupportMessage(models.Model):
    SENDER_TYPE_CHOICES = [
        ('learner', 'Learner'),
        ('agent', 'Agent'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    support_request = models.ForeignKey(
        SupportRequest,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender_type = models.CharField(max_length=16, choices=SENDER_TYPE_CHOICES)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)

    # Low-bandwidth visual snapshot fallback
    is_snapshot = models.BooleanField(default=False)
    snapshot_data = models.TextField(blank=True, help_text="Plain text DOM snapshot or data URI image.")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"SupportMessage {self.id} by {self.sender_type} on {self.support_request_id}"
