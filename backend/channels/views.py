"""
Views and Webhook Handlers for Telegram, SMS, and Job Notification Delivery.
"""

from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse
from channels.models import MessageDelivery
from channels.serializers import (
    SMSInboundSerializer,
    NotificationSendSerializer,
    MessageDeliverySerializer,
)
from channels.sms.adapter import SMSAdapter
from channels.telegram.bot import TelegramBotHandler
from channels.notifications.delivery import send_notification


class TelegramWebhookSerializer(serializers.Serializer):
    update_id = serializers.IntegerField(required=False, help_text="Unique Telegram update identifier")
    message = serializers.DictField(required=False, help_text="Telegram message object")
    callback_query = serializers.DictField(required=False, help_text="Telegram callback query object")


@extend_schema(
    summary="Inbound SMS Gateway Endpoint",
    description=(
        "Inbound SMS endpoint for low-bandwidth access. Accepts 'from' and 'text'. "
        "Returns plain text course answer of at most 160 characters."
    ),
    request=SMSInboundSerializer,
    responses={
        200: OpenApiResponse(description="Plain text response <= 160 characters"),
        400: OpenApiResponse(description="Invalid request")
    }
)
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def sms_inbound_view(request):
    """
    Direct endpoint for Track 3 requirement:
    POST /sms/inbound { from, text } -> plain text reply <= 160 characters.
    Also accepts form-encoded data as sent by standard SMS gateways.
    """
    if request.method == 'GET':
        return HttpResponse("SMS Inbound Gateway Endpoint Ready. Use POST.", content_type="text/plain")

    serializer = SMSInboundSerializer(data=request.data)
    if not serializer.is_valid():
        err_msg = "Invalid SMS request. Required: 'from' and 'text'."
        return HttpResponse(err_msg[:160], content_type="text/plain; charset=utf-8", status=400)

    data = serializer.validated_data
    reply_text = SMSAdapter.process_inbound(
        from_phone=data['from_number'],
        text=data['text']
    )

    # Hackathon specification: returns plain text <= 160 characters
    return HttpResponse(reply_text, content_type="text/plain; charset=utf-8", status=200)


class TelegramWebhookView(APIView):
    """
    Telegram Bot Webhook endpoint.
    Receives updates from Telegram Bot API and routes them to TelegramBotHandler.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Telegram Bot Webhook",
        description="Receives Telegram webhook updates from Telegram Bot servers.",
        request=TelegramWebhookSerializer,
        responses={200: OpenApiResponse(description="Update received and processed successfully")}
    )
    def post(self, request):
        # Validate secret header if configured
        secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
        if secret:
            header_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
            if header_secret != secret:
                return Response({"error": "Unauthorized webhook token"}, status=status.HTTP_403_FORBIDDEN)

        handler = TelegramBotHandler()
        res = handler.handle_update(request.data)
        return Response(res, status=status.HTTP_200_OK)


class NotificationSendView(APIView):
    """
    Shared Outbound Notification Dispatcher API.
    Used by Yensew (Developer 4) for sending Job Alerts and Career notifications.
    """

    @extend_schema(
        summary="Send Outbound Notification (Telegram/SMS)",
        description="Dispatches a job alert or system notification to a learner via Telegram or SMS.",
        request=NotificationSendSerializer,
        responses={
            201: OpenApiResponse(response=MessageDeliverySerializer, description="Notification queued/delivered"),
            400: OpenApiResponse(description="Validation error")
        }
    )
    def post(self, request):
        serializer = NotificationSendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": {"code": "validation_error", "fields": serializer.errors}},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        try:
            result = send_notification(
                recipient=data['recipient'],
                message=data['message'],
                channel=data.get('channel', 'telegram'),
                title=data.get('title')
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class DeliveryStatusView(APIView):
    """Check the delivery status of an outbound notification."""

    @extend_schema(
        summary="Get Delivery Status",
        description="Retrieve delivery tracking details for an outbound SMS or Telegram notification.",
        responses={
            200: MessageDeliverySerializer,
            404: OpenApiResponse(description="Delivery record not found")
        }
    )
    def get(self, request, delivery_id):
        try:
            delivery = MessageDelivery.objects.get(id=delivery_id)
            return Response(MessageDeliverySerializer(delivery).data)
        except MessageDelivery.DoesNotExist:
            return Response({"error": "Delivery record not found"}, status=status.HTTP_404_NOT_FOUND)
