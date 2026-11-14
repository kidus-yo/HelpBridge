import uuid
from rest_framework import serializers
from .models import ChatSession, Message

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'session', 'sender_type', 'content', 'language', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']

class ChatSessionSerializer(serializers.ModelSerializer):
    messages_count = serializers.IntegerField(source='messages.count', read_only=True)

    class Meta:
        model = ChatSession
        fields = [
            'id', 'user', 'institution_id', 'course_id', 'channel',
            'preferred_language', 'status', 'messages_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'messages_count']

class CreateChatSessionSerializer(serializers.Serializer):
    institution_id = serializers.CharField(required=False, allow_null=True, default='inst-default')
    course_id = serializers.CharField(required=False, allow_null=True, default='course-va-101')
    channel = serializers.ChoiceField(choices=['web', 'telegram', 'sms'], default='web')
    preferred_language = serializers.ChoiceField(choices=['en', 'am'], default='en')

class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=4000, required=True, allow_blank=False)
    language = serializers.ChoiceField(choices=['en', 'am'], required=False, allow_null=True)

    def validate_content(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Message content cannot be blank or whitespace only.")
        return stripped
