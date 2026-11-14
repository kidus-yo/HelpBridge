"""
Channel Identity and Message Delivery Models.
Stores mappings from Telegram and SMS external IDs to central chat sessions,
and tracks outbound notifications (e.g. for Yensew's job alerts).
"""

import uuid
from django.db import models


class ChannelIdentity(models.Model):
    """
    Associates external messaging identities (Telegram chat ID, SMS phone number)
    with a central chat session and language preference.
    """
    CHANNEL_CHOICES = [
        ('telegram', 'Telegram'),
        ('sms', 'SMS / Text'),
        ('web', 'Web Widget'),
    ]

    LANGUAGE_CHOICES = [
        ('am', 'Amharic (አማርኛ)'),
        ('en', 'English'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, db_index=True)
    external_id = models.CharField(max_length=128, db_index=True, help_text="External user/chat ID or phone number")
    phone_number = models.CharField(max_length=32, blank=True, null=True, help_text="Normalized E.164 phone number")
    username = models.CharField(max_length=128, blank=True, null=True, help_text="Telegram username if available")
    preferred_language = models.CharField(max_length=8, choices=LANGUAGE_CHOICES, default='am')
    session_id = models.CharField(max_length=128, blank=True, null=True, db_index=True, help_text="Linked central chat session ID")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Channel Identity"
        verbose_name_plural = "Channel Identities"
        unique_together = ('channel', 'external_id')

    def __str__(self):
        return f"{self.get_channel_display()}: {self.external_id} ({self.preferred_language})"


class MessageDelivery(models.Model):
    """
    Tracks outbound message deliveries (such as job alerts from Yensew or channel responses).
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.CharField(max_length=20, choices=ChannelIdentity.CHANNEL_CHOICES)
    recipient = models.CharField(max_length=128, help_text="Destination chat ID or phone number")
    content = models.TextField(help_text="Message text delivered")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Message Delivery"
        verbose_name_plural = "Message Deliveries"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.status.upper()}] {self.channel} -> {self.recipient} ({self.created_at:%Y-%m-%d %H:%M})"
