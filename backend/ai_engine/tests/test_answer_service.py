"""
Tests for AI Grounding, Citation Attribution, and Honest Refusal.
Ensures compliance with Section 6.B, 6.C, and 6.D of the Team Handbook.
"""

from django.test import TestCase
from ai_engine.services.answer_service import AnswerGenerationService, generate_answer
from ai_engine.providers.mock import MockAIProvider
from common.contracts import MockKnowledgeRetrievalService


class AnswerGenerationServiceTests(TestCase):
    def setUp(self):
        self.service = AnswerGenerationService()

    def test_grounded_answer_from_course_evidence(self):
        """Questions matching course material must return grounded answers with valid citations."""
        res = self.service.answer_question(
            question="What is shaping the future of remote virtual assistant work?",
            language="en"
        )
        self.assertTrue(res['grounded'])
        self.assertFalse(res['fallback_used'])
        self.assertGreater(len(res['citations']), 0)

        # Citations must reference actual section and document
        top_citation = res['citations'][0]
        self.assertIn("What is Shaping the Future", top_citation['section'])
        self.assertEqual(top_citation['document_title'], "The Future of the VA Industry - VA-1")
        self.assertIn("#what-is-shaping-the-future-of-va-work", top_citation['anchor'])

    def test_grounded_answer_amharic_language(self):
        """Amharic queries must return Ethiopic grounded responses."""
        res = self.service.answer_question(
            question="ሰው ሰራሽ አስተውሎት AI የቨርቹዋል ረዳቶችን ሥራ እንዴት ይቀርጸዋል?",
            language="am"
        )
        self.assertTrue(res['grounded'])
        self.assertEqual(res['language'], 'am')
        self.assertGreater(len(res['citations']), 0)
        self.assertIn("ሰው ሰራሽ አስተውሎት", res['citations'][0]['section'])

    def test_honest_refusal_when_no_evidence_found(self):
        """Questions completely outside course content must refuse honestly without fabricating citations."""
        unrelated_questions = [
            "How do I bake chocolate chip cookies?",
            "What is the theory of quantum loop gravity?",
            "ማርስ ላይ ሰዎች መቼ ይሄዳሉ?"
        ]
        for q in unrelated_questions:
            res = self.service.answer_question(question=q, language="en")
            self.assertFalse(res['grounded'], f"Expected ungrounded refusal for '{q}'")
            self.assertEqual(len(res['citations']), 0, "No citations should be fabricated for unknown topics")
            self.assertIn("I could not find this information in the course material", res['answer'])

    def test_honest_refusal_in_amharic(self):
        """Amharic refusal must provide clear message and offer human escalation."""
        res = self.service.answer_question(
            question="የፓይዘን ፕሮግራሚንግ ቋንቋ እንዴት ነው የሚሠራው?",
            language="am"
        )
        self.assertFalse(res['grounded'])
        self.assertEqual(len(res['citations']), 0)
        self.assertIn("ይህንን መረጃ በኮርሱ ይዘት ውስጥ ማግኘት አልቻልኩም", res['answer'])
        self.assertIn("ከሰው ጋር ተነጋገር", res['answer'])

    def test_offline_faq_fallback(self):
        """Common platform and accessibility questions must match offline FAQ with fallback_used=True."""
        faq_queries = [
            ("How do I change language to Amharic?", "en"),
            ("ስክሪን ሪደር እና ኪቦርድ እንዴት ይደገፋል?", "am"),
            ("How can I talk to a human tutor?", "en"),
            ("ለሥራ ቃለ መጠይቅ ድጋፍ እንዴት እጠይቃለሁ?", "am"),
        ]
        for query, lang in faq_queries:
            res = self.service.answer_question(question=query, language=lang)
            self.assertTrue(res['fallback_used'], f"Expected FAQ fallback for '{query}'")
            self.assertFalse(res['grounded'])
            self.assertEqual(res['provider'], "offline-faq")
            self.assertIn("FAQ", res['citations'][0]['document_title'])

    def test_empty_or_whitespace_question_handling(self):
        """Empty inputs must return graceful guidance, not crash."""
        res = self.service.answer_question(question="   ", language="en")
        self.assertFalse(res['grounded'])
        self.assertIn("Please enter your question", res['answer'])
