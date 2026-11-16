"""
Tests for Outbound Notification Dispatcher (Contract with Yensew for Job Alerts).
"""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from channels.models import MessageDelivery
from channels.notifications.delivery import send_notification
from platforms.tests.factories import make_integration, make_institution, staff_user


class NotificationDeliveryTests(TestCase):
    def test_send_notification_via_sms(self):
        result = send_notification(
            recipient="0911223344",
            message="New interview accommodation approved.",
            channel="sms",
            title="Interview Update"
        )
        self.assertEqual(result['channel'], 'sms')
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(MessageDelivery.objects.filter(id=result['delivery_id']).exists())

    @override_settings(TELEGRAM_BOT_TOKEN="")
    def test_send_notification_via_telegram(self):
        result = send_notification(
            recipient="12345678",
            message="New matching job posted: Virtual Assistant in Addis Ababa.",
            channel="telegram",
            title="Job Alert"
        )
        self.assertEqual(result['channel'], 'telegram')
        self.assertEqual(result['status'], 'failed')
        delivery = MessageDelivery.objects.get(id=result['delivery_id'])
        self.assertEqual(delivery.status, "failed")

    def test_notification_api_endpoint(self):
        client = APIClient()
        payload = {
            "recipient": "0911223344",
            "message": "Reminder: Accessibility workshop at 10:00 AM.",
            "channel": "sms",
            "title": "Workshop Reminder"
        }
        unauthorized = client.post(
            "/api/v1/channels/notifications/send/",
            payload,
            format="json",
        )
        self.assertIn(unauthorized.status_code, {401, 403})

        unscoped_integration = make_integration(scopes=["courses:read"])
        client.credentials(
            HTTP_AUTHORIZATION=f"Api-Key {unscoped_integration.raw_api_key}"
        )
        forbidden = client.post(
            "/api/v1/channels/notifications/send/",
            payload,
            format="json",
        )
        self.assertEqual(forbidden.status_code, 403)

        integration = make_integration(
            platform=unscoped_integration.platform,
            institution=make_institution(
                slug="notification-scoped",
                name="Notification Scoped",
            ),
            scopes=["notifications:send"],
        )
        client.credentials(HTTP_AUTHORIZATION=f"Api-Key {integration.raw_api_key}")
        response = client.post(
            "/api/v1/channels/notifications/send/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, 503)
        data = response.json()
        delivery_id = data['delivery_id']
        self.assertEqual(data["status"], "failed")

        # Delivery records are visible only to staff, not the integration key.
        status_resp = client.get(f"/api/v1/channels/deliveries/{delivery_id}/")
        self.assertIn(status_resp.status_code, {401, 403})

        staff_client = APIClient()
        staff_client.force_authenticate(user=staff_user())
        status_resp = staff_client.get(f"/api/v1/channels/deliveries/{delivery_id}/")
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.json()['status'], 'failed')
