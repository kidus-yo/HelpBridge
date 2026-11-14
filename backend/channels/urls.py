from django.urls import path
from channels.views import (
    sms_inbound_view,
    TelegramWebhookView,
    NotificationSendView,
    DeliveryStatusView
)

urlpatterns = [
    path('sms/inbound/', sms_inbound_view, name='channels-sms-inbound'),
    path('telegram/webhook/', TelegramWebhookView.as_view(), name='channels-telegram-webhook'),
    path('notifications/send/', NotificationSendView.as_view(), name='channels-notifications-send'),
    path('deliveries/<uuid:delivery_id>/', DeliveryStatusView.as_view(), name='channels-delivery-status'),
]
