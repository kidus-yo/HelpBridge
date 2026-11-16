"""
Tests for Telegram Bot Handler and Webhook API.
"""

from django.test import TestCase, Client
from chat.models import ChatSession, Message
from channels.models import ChannelIdentity
from channels.telegram.client import TelegramClient
from channels.telegram.bot import TelegramBotHandler
from courses.models import Course
from knowledge.models import ContentChunk, KnowledgeDocument
from platforms.tests.factories import make_integration


class MockTelegramClient(TelegramClient):
    """Captures sent messages in memory for test assertions."""
    def __init__(self):
        super().__init__(token="")
        self.sent_messages = []

    def send_message(self, chat_id, text, parse_mode="Markdown", reply_markup=None):
        self.sent_messages.append({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": reply_markup
        })
        return {"ok": True, "result": {"message_id": len(self.sent_messages), "text": text}}

    def answer_callback_query(self, callback_query_id, text=None):
        return {"ok": True}


class TelegramBotTests(TestCase):
    def setUp(self):
        integration = make_integration()
        course = Course.objects.create(
            institution_id=integration.institution_id,
            title="Virtual Assistant Foundations",
            slug="virtual-assistant-foundations",
            language="en",
            status=Course.Status.PUBLISHED,
        )
        document = KnowledgeDocument.objects.create(
            institution_id=integration.institution_id,
            course=course,
            original_filename="What is Shaping the Future of Virtual Assistant Work",
            document_type="txt",
            language="en",
            processing_status=KnowledgeDocument.ProcessingStatus.COMPLETED,
            storage_ref="test-only",
            checksum="telegram-channel-test",
            byte_size=120,
        )
        ContentChunk.objects.create(
            document=document,
            institution_id=integration.institution_id,
            course=course,
            chunk_text=(
                "The future of virtual assistant work is shaped by remote work, "
                "digital tools, and artificial intelligence."
            ),
            chunk_index=0,
            page_number=2,
            section_heading="What is Shaping the Future of Virtual Assistant Work",
            language="en",
        )
        self.enterContext(self.settings(
            CHANNEL_PLATFORM_INTEGRATION_ID=str(integration.id),
            CHANNEL_DEFAULT_COURSE_ID=str(course.id),
            TELEGRAM_WEBHOOK_SECRET="",
        ))
        self.mock_client = MockTelegramClient()
        self.bot = TelegramBotHandler(client=self.mock_client)

    def test_start_command_returns_language_picker(self):
        update = {
            "update_id": 1001,
            "message": {
                "message_id": 1,
                "chat": {"id": 12345678},
                "from": {"id": 12345678, "username": "amara_test"},
                "text": "/start"
            }
        }
        res = self.bot.handle_update(update)
        self.assertTrue(res['ok'])
        self.assertEqual(res['action'], 'start')

        # Check sent message contains buttons
        self.assertEqual(len(self.mock_client.sent_messages), 1)
        last_msg = self.mock_client.sent_messages[-1]
        self.assertIn("እንኳን ወደ ዲጂታል ብሪጅ ረዳት በደህና መጡ", last_msg['text'])
        self.assertIsNotNone(last_msg['reply_markup'])
        keyboard = last_msg['reply_markup']['inline_keyboard'][0]
        self.assertEqual(keyboard[0]['callback_data'], 'set_lang_am')
        self.assertEqual(keyboard[1]['callback_data'], 'set_lang_en')

    def test_callback_query_updates_preferred_language(self):
        cb_update = {
            "update_id": 1002,
            "callback_query": {
                "id": "cb-999",
                "chat_instance": "ci-1",
                "from": {"id": 12345678, "username": "amara_test"},
                "message": {"message_id": 1, "chat": {"id": 12345678}},
                "data": "set_lang_en"
            }
        }
        res = self.bot.handle_update(cb_update)
        self.assertTrue(res['ok'])

        identity = ChannelIdentity.objects.get(external_id="12345678")
        self.assertEqual(identity.preferred_language, "en")

    def test_course_question_returns_grounded_answer_with_citations(self):
        # First ensure language is set
        ChannelIdentity.objects.create(
            channel='telegram',
            external_id="12345678",
            preferred_language="en",
            is_active=True
        )

        update = {
            "update_id": 1003,
            "message": {
                "message_id": 2,
                "chat": {"id": 12345678},
                "from": {"id": 12345678},
                "text": "What is shaping the future of virtual assistant work?"
            }
        }
        res = self.bot.handle_update(update)
        self.assertTrue(res['ok'])
        self.assertTrue(res['grounded'])
        self.assertGreater(res['citations_count'], 0)

        last_msg = self.mock_client.sent_messages[-1]
        self.assertIn("Course Sources", last_msg['text'])
        self.assertIn("What is Shaping the Future", last_msg['text'])
        identity = ChannelIdentity.objects.get(channel="telegram", external_id="12345678")
        session = ChatSession.objects.get(id=identity.session_id)
        self.assertEqual(session.channel, "telegram")
        self.assertNotEqual(session.platform_user_ref, identity.external_id)
        self.assertEqual(
            list(Message.objects.filter(session=session).values_list("sender_type", flat=True)),
            ["learner", "assistant"],
        )

    def test_unconfigured_channel_returns_explicit_unavailable_response(self):
        with self.settings(
            CHANNEL_PLATFORM_INTEGRATION_ID="",
            CHANNEL_DEFAULT_COURSE_ID="",
        ):
            result = self.bot.handle_update({
                "message": {
                    "chat": {"id": 12345678},
                    "from": {"id": 12345678},
                    "text": "Where can I find course materials?",
                }
            })
        self.assertEqual(result["action"], "unavailable")
        self.assertFalse(result["grounded"])
        self.assertFalse(ChatSession.objects.exists())
        self.assertIn("ገና አልተዋቀረም", self.mock_client.sent_messages[-1]["text"])

    def test_telegram_webhook_http_endpoint(self):
        client = Client()
        payload = {
            "update_id": 1004,
            "message": {
                "message_id": 3,
                "chat": {"id": 88888888},
                "from": {"id": 88888888},
                "text": "/help"
            }
        }
        response = client.post(
            "/api/v1/channels/telegram/webhook/",
            data=payload,
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
