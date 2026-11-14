import uuid
from django.db import models
from django.conf import settings

class ChatSession(models.Model):
    CHANNEL_CHOICES = [
        ('web', 'Web Widget'),
        ('telegram', 'Telegram'),
        ('sms', 'SMS / Text'),
    ]

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('am', 'Amharic'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_sessions'
    )
    institution_id = models.CharField(max_length=255, blank=True, null=True, default='inst-default')
    course_id = models.CharField(max_length=255, blank=True, null=True, default='course-va-101')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='web')
    preferred_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.id} ({self.channel} - {self.preferred_language})"

class Message(models.Model):
    SENDER_CHOICES = [
        ('learner', 'Learner'),
        ('assistant', 'Assistant'),
        ('agent', 'Human Agent'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender_type = models.CharField(max_length=20, choices=SENDER_CHOICES)
    content = models.TextField()
    language = models.CharField(max_length=10, default='en')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender_type}] {self.content[:30]}..."
