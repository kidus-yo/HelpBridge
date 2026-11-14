import uuid
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from chat.models import ChatSession
from accessibility.models import AccessibilityPreference

class AccessibilityAPITests(APITestCase):
    def setUp(self):
        self.session = ChatSession.objects.create(
            channel="web",
            preferred_language="en"
        )

    def test_get_preferences_returns_defaults(self):
        url = reverse('accessibility-preference-detail', kwargs={'session_id': self.session.id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['preferred_language'], 'en')
        self.assertEqual(res.data['language'], 'en')
        self.assertFalse(res.data['simple_mode'])
        self.assertEqual(res.data['text_size'], 'normal')
        self.assertEqual(res.data['text_direction'], 'ltr')
        self.assertFalse(res.data['right_to_left'])

    def test_update_preferences_user_specified_payload(self):
        """
        Tests the exact handbook payload:
        {
            "language": "am",
            "simple_mode": True,
            "text_size": "large",
            "voice_enabled": False
        }
        """
        url = reverse('accessibility-preference-detail', kwargs={'session_id': self.session.id})
        data = {
            "language": "am",
            "simple_mode": True,
            "text_size": "large",
            "voice_enabled": False
        }
        res = self.client.patch(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['simple_mode'])
        self.assertEqual(res.data['text_size'], 'large')
        self.assertEqual(res.data['language'], 'am')
        self.assertEqual(res.data['preferred_language'], 'am')
        self.assertFalse(res.data['voice_enabled'])

        # Check that session language is synced
        self.session.refresh_from_db()
        self.assertEqual(self.session.preferred_language, 'am')

    def test_update_right_to_left_preference(self):
        url = reverse('accessibility-preference-detail', kwargs={'session_id': self.session.id})
        data = {"right_to_left": True}
        res = self.client.patch(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['text_direction'], 'rtl')
        self.assertTrue(res.data['right_to_left'])

    def test_invalid_text_size_rejected(self):
        url = reverse('accessibility-preference-detail', kwargs={'session_id': self.session.id})
        data = {"text_size": "huge_giant_invalid"}
        res = self.client.patch(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_language_rejected(self):
        url = reverse('accessibility-preference-detail', kwargs={'session_id': self.session.id})
        data = {"language": "klingon"}
        res = self.client.patch(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_session_returns_404(self):
        fake_id = uuid.uuid4()
        url = reverse('accessibility-preference-detail', kwargs={'session_id': fake_id})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
