"""
Tests for Pluggable AI Providers (Offline, Cloud, Local, Mock).
"""

from django.test import TestCase
from ai_engine.providers.offline import OfflineKeywordProvider
from ai_engine.providers.cloud import CloudAIProvider
from ai_engine.providers.mock import MockAIProvider


class ProviderTests(TestCase):
    def setUp(self):
        self.evidence = [
            {
                "chunk_id": "c-1",
                "text": "Virtual assistants work remotely across time zones with digital tools.",
                "document_title": "VA Fundamentals",
                "section": "Remote Work Trends",
                "page": 1,
                "anchor": "#sec-1",
                "url": "/lesson.html#sec-1",
                "relevance": 0.88
            }
        ]

    def test_offline_keyword_provider_with_evidence(self):
        provider = OfflineKeywordProvider()
        res = provider.generate(
            question="Tell me about remote work for VAs",
            evidence=self.evidence,
            language="en"
        )
        self.assertTrue(res['grounded'])
        self.assertEqual(res['provider'], 'offline-keyword')
        self.assertEqual(len(res['citations']), 1)
        self.assertEqual(res['citations'][0]['section'], "Remote Work Trends")

    def test_mock_provider(self):
        provider = MockAIProvider()
        res = provider.generate(
            question="What is a VA?",
            evidence=self.evidence,
            language="en"
        )
        self.assertTrue(res['grounded'])
        self.assertEqual(res['provider'], 'mock')

    def test_cloud_provider_fallback_when_unconfigured(self):
        """When AI_CLOUD_API_KEY is unset, CloudAIProvider must fall back to offline keyword provider."""
        provider = CloudAIProvider(api_key="")
        res = provider.generate(
            question="Tell me about remote work for VAs",
            evidence=self.evidence,
            language="en"
        )
        self.assertTrue(res['grounded'])
        self.assertIn("fallback:offline", res['provider'])
