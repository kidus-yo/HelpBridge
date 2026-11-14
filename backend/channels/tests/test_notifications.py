"""
Tests for Outbound Notification Dispatcher (Contract with Yensew for Job Alerts).
"""

from django.test import TestCase, Client
from channels.models import MessageDelivery
from channels.notifications.delivery import send_notification


class NotificationDeliveryTests(TestCase):
    def test_send_notification_via_sms(self):
        result = send_notification(
            recipient="0911223344",
            message="New interview accommodation approved.",
            channel="sms",
            title="Interview Update"
        )
        self.assertEqual(result['channel'], 'sms')
        self.assertEqual(result['status'], 'delivered')
        self.assertTrue(MessageDelivery.objects.filter(id=result['delivery_id']).exists())

    def test_send_notification_via_telegram(self):
        result = send_notification(
            recipient="12345678",
            message="New matching job posted: Virtual Assistant in Addis Ababa.",
            channel="telegram",
            title="Job Alert"
        )
        self.assertEqual(result['channel'], 'telegram')
        self.assertEqual(result['status'], 'delivered')
        self.assertTrue(MessageDelivery.objects.filter(id=result['delivery_id']).exists())

    def test_notification_api_endpoint(self):
        client = Client()
        payload = {
            "recipient": "0911223344",
            "message": "Reminder: Accessibility workshop at 10:00 AM.",
            "channel": "sms",
            "title": "Workshop Reminder"
        }
        response = client.post(
            "/api/v1/channels/notifications/send/",
            data=payload,
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        delivery_id = data['delivery_id']

        # Verify status endpoint
        status_resp = client.get(f"/api/v1/channels/deliveries/{delivery_id}/")
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.json()['status'], 'delivered')
