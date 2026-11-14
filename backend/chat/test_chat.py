import uuid
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from chat.models import ChatSession, Message

class ChatAPITests(APITestCase):
    def setUp(self):
        self.session = ChatSession.objects.create(
            channel="web",
            preferred_language="en",
            course_id="course-va-101"
        )

    def test_create_session_success(self):
        url = reverse('chat-session-list-create')
        data = {
            "channel": "web",
            "preferred_language": "en",
            "course_id": "course-va-101"
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", res.data)
        self.assertEqual(res.data["channel"], "web")
        self.assertEqual(res.data["preferred_language"], "en")

        # Verify accessibility preferences were initialized automatically
        session_id = res.data["id"]
        session = ChatSession.objects.get(id=session_id)
        self.assertIsNotNone(session.accessibility_preference)

    def test_send_message_grounded_response_with_citations(self):
        url = reverse('chat-message-list-create', kwargs={'session_id': self.session.id})
        data = {"content": "How is AI shaping the future of virtual assistant work?"}
        res = self.client.post(url, data, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["grounded"])
        self.assertGreater(len(res.data["citations"]), 0)
        self.assertIn("The Future of the VA Industry", res.data["citations"][0]["document_title"])

        # Check that messages are persisted
        self.assertEqual(self.session.messages.count(), 2)
        learner_msg = self.session.messages.filter(sender_type='learner').first()
        assistant_msg = self.session.messages.filter(sender_type='assistant').first()
        self.assertIsNotNone(learner_msg)
        self.assertIsNotNone(assistant_msg)

    def test_send_message_ungrounded_honest_refusal(self):
        url = reverse('chat-message-list-create', kwargs={'session_id': self.session.id})
        data = {"content": "Quantum physics astrophysics thermodynamics"}
        res = self.client.post(url, data, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data["grounded"])
        self.assertEqual(len(res.data["citations"]), 0)

    def test_amharic_grounded_response(self):
        session_am = ChatSession.objects.create(
            channel="web",
            preferred_language="am",
            course_id="course-va-101"
        )
        url = reverse('chat-message-list-create', kwargs={'session_id': session_am.id})
        data = {"content": "ሰው ሰራሽ አስተውሎት AI ረዳቶችን እንዴት ይረዳል?"}
        res = self.client.post(url, data, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["grounded"])
        self.assertGreater(len(res.data["citations"]), 0)

    def test_empty_message_rejected(self):
        url = reverse('chat-message-list-create', kwargs={'session_id': self.session.id})
        res = self.client.post(url, {"content": "   "}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_oversized_message_rejected(self):
        url = reverse('chat-message-list-create', kwargs={'session_id': self.session.id})
        res = self.client.post(url, {"content": "a" * 4001}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_message_ordering_and_history(self):
        Message.objects.create(session=self.session, sender_type='learner', content='Msg 1')
        Message.objects.create(session=self.session, sender_type='assistant', content='Reply 1')
        Message.objects.create(session=self.session, sender_type='learner', content='Msg 2')

        url = reverse('chat-message-list-create', kwargs={'session_id': self.session.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)
        self.assertEqual(res.data[0]['content'], 'Msg 1')
        self.assertEqual(res.data[1]['content'], 'Reply 1')
        self.assertEqual(res.data[2]['content'], 'Msg 2')
