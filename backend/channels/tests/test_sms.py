"""
Tests for Low-Bandwidth SMS Route and Ethiopian Phone Normalization.
Ensures compliance with Technical Guide Section 9 (Phone Normalization)
and Track 3 SMS requirement (<= 160 characters plain text response).
"""

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from channels.sms.normalizer import normalize_ethiopian_phone
from channels.sms.adapter import SMSAdapter
from channels.models import ChannelIdentity, MessageDelivery
from chat.models import ChatSession, Message
from courses.models import Course
from knowledge.models import ContentChunk, KnowledgeDocument
from platforms.tests.factories import make_integration


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
    def setUp(self):
        integration = make_integration()
        course = Course.objects.create(
            institution_id=integration.institution_id,
            title="Virtual Assistant Foundations",
            slug="virtual-assistant-foundations",
            language="en",
            status=Course.Status.PUBLISHED,
        )
        for language, text, suffix in (
            (
                "en",
                "The future of virtual assistant work is shaped by remote work, "
                "digital tools, and artificial intelligence.",
                "english",
            ),
            (
                "am",
                "የቨርቹዋል ረዳት ሥራ የወደፊት ዕድል በዲጂታል መሣሪያዎች ይደገፋል። "
                "ሰው ሰራሽ አስተውሎት ሥራውን ይቀርጸዋል።",
                "amharic",
            ),
        ):
            document = KnowledgeDocument.objects.create(
                institution_id=integration.institution_id,
                course=course,
                original_filename=f"future-work-{suffix}.txt",
                document_type="txt",
                language=language,
                processing_status=KnowledgeDocument.ProcessingStatus.COMPLETED,
                storage_ref="test-only",
                checksum=f"sms-channel-{suffix}",
                byte_size=len(text.encode("utf-8")),
            )
            ContentChunk.objects.create(
                document=document,
                institution_id=integration.institution_id,
                course=course,
                chunk_text=text,
                chunk_index=0,
                page_number=1,
                section_heading="Future of virtual assistant work",
                language=language,
            )
        self.enterContext(self.settings(
            CHANNEL_PLATFORM_INTEGRATION_ID=str(integration.id),
            CHANNEL_DEFAULT_COURSE_ID=str(course.id),
            SMS_GATEWAY_API_KEY="test-gateway-secret",
        ))

    def test_inbound_sms_reply_length_constraint(self):
        """Inbound SMS reply must be plain text and <= 160 characters."""
        reply = SMSAdapter.process_inbound(
            from_phone="0911223344",
            text="What is shaping the future of virtual assistant work?"
        )
        self.assertIsInstance(reply, str)
        self.assertLessEqual(len(reply), 160, f"SMS reply exceeded 160 characters ({len(reply)} chars): {reply}")
        self.assertGreater(len(reply), 10)
        identity = ChannelIdentity.objects.get(channel="sms", external_id="+251911223344")
        session = ChatSession.objects.get(id=identity.session_id)
        self.assertEqual(session.channel, "sms")
        self.assertEqual(
            list(Message.objects.filter(session=session).values_list("sender_type", flat=True)),
            ["learner", "assistant"],
        )

    def test_inbound_sms_amharic_reply(self):
        """Amharic SMS query must return an Ethiopic response <= 160 characters."""
        reply = SMSAdapter.process_inbound(
            from_phone="0911223344",
            text="የቨርቹዋል ረዳት ሥራ የወደፊት ዕድል ምን ይመስላል?"
        )
        self.assertLessEqual(len(reply), 160)
        self.assertGreater(len(reply), 10)

    def test_unconfigured_sms_channel_returns_explicit_unavailable_response(self):
        with override_settings(
            CHANNEL_PLATFORM_INTEGRATION_ID="",
            CHANNEL_DEFAULT_COURSE_ID="",
        ):
            reply = SMSAdapter.process_inbound(
                from_phone="0911223344",
                text="What is shaping the future of virtual assistant work?",
            )

        self.assertIn("not configured", reply)
        self.assertFalse(ChatSession.objects.exists())

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
            content_type="application/json",
            HTTP_X_SMS_GATEWAY_KEY="test-gateway-secret",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response['Content-Type'])
        self.assertLessEqual(len(response.content.decode('utf-8')), 160)

    def test_sms_inbound_rejects_missing_gateway_authentication(self):
        response = Client().post(
            "/sms/inbound",
            data={"from": "0911223344", "text": "What is AI?"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_outbound_sms_delivery_recording(self):
        """Unconfigured outbound SMS is recorded as failed, never delivered."""
        res = SMSAdapter.send_outbound(
            to_phone="0911223344",
            text="New Job Alert: Junior VA position posted in Addis Ababa."
        )
        self.assertEqual(res['status'], 'failed')
        delivery = MessageDelivery.objects.get(id=res['delivery_id'])
        self.assertEqual(delivery.status, "failed")
        self.assertIn("configured", delivery.error_message)
