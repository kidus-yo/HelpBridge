"""
Views and Webhook Handlers for Telegram, SMS, and Job Notification Delivery.
"""

import hmac

from django.http import HttpResponse
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.authentication import SessionAuthentication
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
from platforms.authentication import IntegrationApiKeyAuthentication
from platforms.permissions import IsStaffUser


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

    gateway_key = getattr(settings, "SMS_GATEWAY_API_KEY", "")
    supplied_key = request.headers.get("X-SMS-Gateway-Key", "")
    if not gateway_key:
        return HttpResponse(
            "SMS gateway is not configured.",
            content_type="text/plain; charset=utf-8",
            status=503,
        )
    if not hmac.compare_digest(supplied_key, gateway_key):
        return HttpResponse(
            "Unauthorized SMS gateway request.",
            content_type="text/plain; charset=utf-8",
            status=403,
        )

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
            if not hmac.compare_digest(header_secret, secret):
                return Response({"error": "Unauthorized webhook token"}, status=status.HTTP_403_FORBIDDEN)
        elif getattr(settings, "DJANGO_ENV", "development") == "production":
            return Response(
                {"error": {"code": "webhook_not_configured"}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        handler = TelegramBotHandler()
        res = handler.handle_update(request.data)
        return Response(res, status=status.HTTP_200_OK)


class StaffOrNotificationIntegration(BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True
        integration = getattr(request, "platform_integration", None)
        return bool(
            integration
            and "notifications:send" in (integration.permitted_scopes or [])
        )


class NotificationSendView(APIView):
    """
    Shared Outbound Notification Dispatcher API.
    Used by Yensew (Developer 4) for sending Job Alerts and Career notifications.
    """

    authentication_classes = [SessionAuthentication, IntegrationApiKeyAuthentication]
    permission_classes = [StaffOrNotificationIntegration]

    @extend_schema(
        summary="Send Outbound Notification (Telegram/SMS)",
        description="Dispatches a job alert or system notification to a learner via Telegram or SMS.",
        request=NotificationSendSerializer,
        responses={
            201: OpenApiResponse(response=MessageDeliverySerializer, description="Notification sent"),
            400: OpenApiResponse(description="Validation error"),
            503: OpenApiResponse(description="No delivery provider is configured"),
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
            response_status = (
                status.HTTP_201_CREATED
                if result.get("status") in {"pending", "sent", "delivered"}
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )
            return Response(result, status=response_status)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class DeliveryStatusView(APIView):
    """Check the delivery status of an outbound notification."""
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsStaffUser]

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
