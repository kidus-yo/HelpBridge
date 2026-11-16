"""
Shared Outbound Notification Dispatcher.
Implements the contract agreed in Section 7.4 (Samuel <-> Yensew) of the handbook:
'Yensew calls a shared notification/delivery interface for job alerts.
 Samuel owns provider adapters and delivery status.
 Do not duplicate Telegram/SMS credentials or integrations.'
"""

import logging
from typing import Dict, Any, Optional
from channels.models import MessageDelivery
from channels.sms.adapter import SMSAdapter
from channels.telegram.client import TelegramClient

logger = logging.getLogger(__name__)


class NotificationDeliveryService:
    @classmethod
    def dispatch(
        cls,
        recipient: str,
        message: str,
        channel: str = 'telegram',
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches outbound notification via Telegram or SMS.
        """
        ch = (channel or 'telegram').lower()
        full_text = f"📢 **{title}**\n\n{message}" if title else message

        if ch == 'sms':
            # Use SMS adapter
            return SMSAdapter.send_outbound(to_phone=recipient, text=full_text)

        elif ch == 'telegram':
            client = TelegramClient()
            resp = client.send_message(chat_id=recipient, text=full_text)
            status = 'sent' if resp.get('ok') else 'failed'
            err_msg = resp.get('error')

            delivery = MessageDelivery.objects.create(
                channel='telegram',
                recipient=str(recipient),
                content=full_text,
                status=status,
                error_message=err_msg,
            )

            return {
                "delivery_id": str(delivery.id),
                "channel": "telegram",
                "recipient": str(recipient),
                "status": delivery.status,
                "delivered_at": delivery.delivered_at.isoformat() if delivery.delivered_at else None
            }

        else:
            raise ValueError(f"Unsupported delivery channel '{channel}'. Use 'telegram' or 'sms'.")


# Functional interface for Yensew and other apps
def send_notification(
    recipient: str,
    message: str,
    channel: str = 'telegram',
    title: Optional[str] = None
) -> Dict[str, Any]:
    return NotificationDeliveryService.dispatch(
        recipient=recipient,
        message=message,
        channel=channel,
        title=title
    )
