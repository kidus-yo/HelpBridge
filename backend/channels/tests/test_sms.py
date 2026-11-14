"""
Tests for Low-Bandwidth SMS Route and Ethiopian Phone Normalization.
Ensures compliance with Technical Guide Section 9 (Phone Normalization)
and Track 3 SMS requirement (<= 160 characters plain text response).
"""

from django.test import TestCase, Client
from django.urls import reverse
from channels.sms.normalizer import normalize_ethiopian_phone
from channels.sms.adapter import SMSAdapter
from channels.models import ChannelIdentity, MessageDelivery


class EthiopianPhoneNormalizerTests(TestCase):
    def test_valid_phone_formats(self):
        cases = [
            ("0911223344", "+251911223344"),
            ("0712345678", "+251712345678"),
            ("+251911223344", "+251911223344"),
            ("251911223344", "+251911223344"),
            ("0911 22 33 44", "+251911223344"),
            ("(0911)-223-344", "+251911223344"),
        ]
        for raw, expected in cases:
            self.assertEqual(normalize_ethiopian_phone(raw), expected)

    def test_invalid_phone_formats(self):
        invalid_numbers = [
            "0811223344",      # Invalid prefix (not 09 or 07)
            "091122",          # Too short
            "09112233445566",  # Too long
            "abcdefghij",      # Non-digits
            "",                # Empty
        ]
        for raw in invalid_numbers:
            with self.assertRaises(ValueError):
                normalize_ethiopian_phone(raw)


class SMSAdapterTests(TestCase):
    def test_inbound_sms_reply_length_constraint(self):
        """Inbound SMS reply must be plain text and <= 160 characters."""
        reply = SMSAdapter.process_inbound(
            from_phone="0911223344",
            text="What is shaping the future of virtual assistant work?"
        )
        self.assertIsInstance(reply, str)
        self.assertLessEqual(len(reply), 160, f"SMS reply exceeded 160 characters ({len(reply)} chars): {reply}")
        self.assertGreater(len(reply), 10)

    def test_inbound_sms_amharic_reply(self):
        """Amharic SMS query must return an Ethiopic response <= 160 characters."""
        reply = SMSAdapter.process_inbound(
            from_phone="0911223344",
            text="የቨርቹዋል ረዳት ሥራ የወደፊት ዕድል ምን ይመስላል?"
        )
        self.assertLessEqual(len(reply), 160)
        self.assertGreater(len(reply), 10)

    def test_language_switch_via_sms(self):
        """Learners can change language by texting 'LANG EN' or 'LANG AM'."""
        phone = "0922334455"
        reply_en = SMSAdapter.process_inbound(from_phone=phone, text="LANG EN")
        self.assertLessEqual(len(reply_en), 160)
        self.assertIn("English", reply_en)

        identity = ChannelIdentity.objects.get(external_id="+251922334455")
        self.assertEqual(identity.preferred_language, "en")

        reply_am = SMSAdapter.process_inbound(from_phone=phone, text="LANG AM")
        self.assertLessEqual(len(reply_am), 160)
        self.assertIn("አማርኛ", reply_am)

        identity.refresh_from_db()
        self.assertEqual(identity.preferred_language, "am")

    def test_sms_inbound_http_endpoint(self):
        """Tests the direct /sms/inbound HTTP route required by the hackathon guide."""
        client = Client()
        response = client.post(
            "/sms/inbound",
            data={"from": "0911223344", "text": "What is AI in virtual assistance?"},
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response['Content-Type'])
        self.assertLessEqual(len(response.content.decode('utf-8')), 160)

    def test_outbound_sms_delivery_recording(self):
        """Outbound notifications must be recorded in MessageDelivery."""
        res = SMSAdapter.send_outbound(
            to_phone="0911223344",
            text="New Job Alert: Junior VA position posted in Addis Ababa."
        )
        self.assertEqual(res['status'], 'delivered')
        self.assertTrue(MessageDelivery.objects.filter(id=res['delivery_id']).exists())
