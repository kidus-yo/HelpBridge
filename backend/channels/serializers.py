"""
Serializers for Channel Inbound & Outbound Endpoints.
"""

from rest_framework import serializers
from channels.models import ChannelIdentity, MessageDelivery


class SMSInboundSerializer(serializers.Serializer):
    """
    Accepts inbound SMS data from gateways or curl tests.
    Supports either 'from' or 'sender', and 'text', 'message', or 'body'.
    """
    from_number = serializers.CharField(
        required=False,
        help_text="Sender Ethiopian phone number (e.g. 0911223344 or +251911223344)"
    )
    text = serializers.CharField(
        required=False,
        help_text="Message text content"
    )

    def validate(self, data):
        # Support various gateway field names
        initial = self.initial_data
        sender = initial.get('from') or initial.get('sender') or data.get('from_number')
        body = initial.get('text') or initial.get('message') or initial.get('body') or data.get('text')

        if not sender:
            raise serializers.ValidationError({"from": "Sender phone number is required (field 'from' or 'sender')."})
        if not body:
            raise serializers.ValidationError({"text": "Message content is required (field 'text' or 'body')."})

        return {
            "from_number": str(sender).strip(),
            "text": str(body).strip()
        }


class NotificationSendSerializer(serializers.Serializer):
    recipient = serializers.CharField(help_text="Destination Telegram chat ID or Ethiopian phone number")
    message = serializers.CharField(help_text="Notification message text")
    channel = serializers.ChoiceField(choices=['telegram', 'sms'], default='telegram')
    title = serializers.CharField(required=False, allow_blank=True, help_text="Optional alert headline")


class MessageDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageDelivery
        fields = ['id', 'channel', 'recipient', 'content', 'status', 'error_message', 'created_at', 'delivered_at']


class ChannelIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelIdentity
        fields = ['id', 'channel', 'external_id', 'phone_number', 'username', 'preferred_language', 'session_id', 'is_active', 'created_at']
