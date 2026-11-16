"""
Serializers for Support Requests, Messages, and Screen-Share Operations.
"""

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, OpenApiTypes
from support.models import SupportRequest, SupportMessage
from support.permissions import is_support_agent
from chat.models import ChatSession


class SupportMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = SupportMessage
        fields = [
            'id',
            'support_request',
            'sender_type',
            'sender',
            'sender_username',
            'content',
            'is_read',
            'is_snapshot',
            'snapshot_data',
            'created_at',
        ]
        read_only_fields = ['id', 'support_request', 'sender_type', 'sender', 'sender_username', 'is_read', 'created_at']


class SupportRequestListSerializer(serializers.ModelSerializer):
    assigned_agent_name = serializers.CharField(source='assigned_agent.username', read_only=True)
    messages_count = serializers.IntegerField(source='messages.count', read_only=True)

    class Meta:
        model = SupportRequest
        fields = [
            'id',
            'category',
            'subject',
            'description',
            'priority',
            'status',
            'preferred_assistance_mode',
            'language',
            'assigned_agent',
            'assigned_agent_name',
            'learner_consent_chat_history',
            'screen_share_active',
            'messages_count',
            'created_at',
            'updated_at',
        ]


class SupportRequestDetailSerializer(serializers.ModelSerializer):
    assigned_agent_name = serializers.CharField(source='assigned_agent.username', read_only=True)
    messages = SupportMessageSerializer(many=True, read_only=True)
    accessibility_meta = serializers.SerializerMethodField()
    guest_token = serializers.SerializerMethodField()
    shared_chat_history = serializers.SerializerMethodField()

    class Meta:
        model = SupportRequest
        fields = [
            'id',
            'institution_id',
            'chat_session_id',
            'category',
            'subject',
            'description',
            'priority',
            'status',
            'preferred_assistance_mode',
            'language',
            'assigned_agent',
            'assigned_agent_name',
            'learner_consent_chat_history',
            'screen_share_active',
            'guest_token',
            'shared_chat_history',
            'messages',
            'created_at',
            'updated_at',
            'accessibility_meta',
        ]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_accessibility_meta(self, obj):
        status_announcements = {
            'open': 'Your support request is open. Waiting for an agent to be assigned.',
            'assigned': f'Support agent {obj.assigned_agent.username if obj.assigned_agent else "assigned"} has taken your ticket.',
            'in_progress': 'You are currently in conversation with your support agent.',
            'resolved': 'Your support ticket has been marked as resolved.',
            'closed': 'This support ticket is closed.',
        }
        return {
            'status_announcement': status_announcements.get(obj.status, f"Ticket status is {obj.status}."),
            'screen_sharing_status': "Active" if obj.screen_share_active else "Inactive",
            'language': obj.language,
        }

    def get_guest_token(self, obj):
        request = self.context.get("request")
        if request and request.method == "POST":
            return obj.guest_token
        return ""

    def get_shared_chat_history(self, obj):
        request = self.context.get("request")
        if (
            not obj.learner_consent_chat_history
            or not obj.chat_session_id
            or not request
            or not is_support_agent(request.user)
        ):
            return []

        session = ChatSession.objects.filter(
            id=obj.chat_session_id,
            institution_id=str(obj.institution_id),
        ).first()
        if session is None:
            return []
        messages = list(session.messages.order_by("-created_at")[:20])
        messages.reverse()
        return [
            {
                "sender_type": message.sender_type,
                "content": message.content,
                "language": message.language,
                "created_at": message.created_at,
            }
            for message in messages
        ]


class SupportRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportRequest
        fields = [
            'id',
            'institution_id',
            'chat_session_id',
            'category',
            'subject',
            'description',
            'priority',
            'preferred_assistance_mode',
            'language',
            'learner_consent_chat_history',
            'guest_token',
        ]
        read_only_fields = ['id', 'guest_token']


class SupportRequestStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[c[0] for c in SupportRequest.STATUS_CHOICES])
    assign_to_me = serializers.BooleanField(required=False, default=False)


class ScreenShareControlSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['start', 'stop'])


class ScreenSnapshotSerializer(serializers.Serializer):
    snapshot_data = serializers.CharField(required=True)
    description = serializers.CharField(required=False, allow_blank=True, default='')
