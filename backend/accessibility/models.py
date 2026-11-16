import uuid
from django.db import models
from django.conf import settings
from common.languages import LANGUAGE_CHOICES
from chat.models import ChatSession

class AccessibilityPreference(models.Model):
    TEXT_SIZE_CHOICES = [
        ('normal', 'Normal'),
        ('large', 'Large'),
        ('xlarge', 'Extra Large'),
    ]

    TEXT_DIRECTION_CHOICES = [
        ('ltr', 'Left-to-Right (LTR)'),
        ('rtl', 'Right-to-Left (RTL)'),
        ('auto', 'Automatic'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='accessibility_preference'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessibility_preferences'
    )
    preferred_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    simple_mode = models.BooleanField(
        default=False,
        help_text="Reduces visual clutter and uses simplified explanations"
    )
    text_size = models.CharField(max_length=10, choices=TEXT_SIZE_CHOICES, default='normal')
    voice_input_enabled = models.BooleanField(default=False)
    voice_output_enabled = models.BooleanField(default=False)
    text_direction = models.CharField(max_length=10, choices=TEXT_DIRECTION_CHOICES, default='ltr')
    high_contrast = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Prefs for session {self.session_id} (Lang: {self.preferred_language}, Simple: {self.simple_mode})"

