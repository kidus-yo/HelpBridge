"""
Central AI Answer Generation Service.
Implements the contract specified in Section 6 (Developer 3 — Samuel)
and Section 7.5 (Suggested normalized AI answer) of the handbook.
"""

from typing import List, Dict, Any, Optional
from django.conf import settings
from common.contracts import MockKnowledgeRetrievalService
from ai_engine.providers.base import BaseAIProvider
from ai_engine.providers.offline import OfflineKeywordProvider
from ai_engine.providers.cloud import CloudAIProvider
from ai_engine.providers.local import LocalAIProvider
from ai_engine.providers.mock import MockAIProvider
from ai_engine.services.faq_fallback import FAQFallbackService
from ai_engine.services.prompt_templates import REFUSALS, HUMAN_HELP_PROMPT
from knowledge.services.retrieval import search_course_content


class DatabaseKnowledgeRetrievalService:
    def __init__(self, fallback_service: Optional[MockKnowledgeRetrievalService] = None):
        self.fallback_service = fallback_service or MockKnowledgeRetrievalService()

    def search(
        self,
        question: str,
        course_id: Optional[str] = None,
        language: str = 'en',
        limit: int = 3,
        institution_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not question or not question.strip():
            return []

        if institution_id is not None:
            try:
                return search_course_content(
                    institution_id=institution_id,
                    query=question,
                    course_id=course_id,
                    language=language,
                    limit=limit,
                )
            except Exception:  # pragma: no cover - defensive guard at the boundary
                return self.fallback_service.search(
                    question=question,
                    course_id=course_id,
                    language=language,
                    limit=limit,
                )

        return self.fallback_service.search(
            question=question,
            course_id=course_id,
            language=language,
            limit=limit,
        )


class AnswerGenerationService:
    def __init__(
        self,
        retrieval_service: Optional[object] = None,
        faq_service: Optional[FAQFallbackService] = None,
        default_provider_name: Optional[str] = None
    ):
        self.retrieval_service = retrieval_service or DatabaseKnowledgeRetrievalService()
        self.faq_service = faq_service or FAQFallbackService()
        self.default_provider_name = default_provider_name or getattr(settings, 'AI_PROVIDER', 'offline')
        self.threshold = getattr(settings, 'AI_GROUNDING_THRESHOLD', 0.25)

    def _get_provider(self, name: Optional[str] = None) -> BaseAIProvider:
        p_name = (name or self.default_provider_name).lower()
        if p_name == 'cloud':
            return CloudAIProvider()
        elif p_name == 'local':
            return LocalAIProvider()
        elif p_name == 'mock':
            return MockAIProvider()
        else:
            return OfflineKeywordProvider()

    def answer_question(
        self,
        question: str,
        course_id: Optional[str] = 'course-va-101',
        language: str = 'am',
        conversation_context: Optional[List[Dict[str, Any]]] = None,
        provider_name: Optional[str] = None,
        institution_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for question answering.
        Flow:
        1. Check FAQ match for general platform/accessibility/support queries.
        2. Retrieve relevant course evidence.
        3. If evidence found above threshold -> Generate grounded answer.
        4. If evidence not found -> Return FAQ or honest refusal.
        """
        lang = 'am' if language == 'am' else 'en'
        clean_q = (question or '').strip()

        if not clean_q:
            return {
                "answer": "እባክዎ ጥያቄዎን ያስገቡ።" if lang == 'am' else "Please enter your question.",
                "language": lang,
                "grounded": False,
                "fallback_used": False,
                "citations": [],
                "provider": "validator"
            }

        # Check FAQ fallback first
        faq_match = self.faq_service.match(clean_q, language=lang)

        # Retrieval for course content
        evidence = self.retrieval_service.search(
            question=clean_q,
            course_id=course_id,
            language=lang,
            limit=3,
            institution_id=institution_id,
        )

        is_sufficient_evidence = bool(
            evidence and evidence[0].get('relevance', 0) >= self.threshold
        )

        # Priority resolution: If query explicitly asks about human help or language change, FAQ wins
        support_keywords = ['human', 'talk', 'language', 'switch', 'change', 'interview', 'accommodation', 'ሰው', 'አስተማሪ', 'ቋንቋ', 'መቀየር', 'ድጋፍ']
        is_support_intent = any(k in clean_q.lower() for k in support_keywords)

        if faq_match and is_support_intent:
            return faq_match

        # Generate grounded answer from evidence
        if is_sufficient_evidence:
            provider = self._get_provider(provider_name)
            result = provider.generate(
                question=clean_q,
                evidence=evidence,
                language=lang,
                conversation_context=conversation_context
            )
            return result

        if faq_match:
            return faq_match

        # Honest refusal (No fabricated citations, no hallucinations)
        refusal_msg = REFUSALS[lang] + HUMAN_HELP_PROMPT[lang]
        return {
            "answer": refusal_msg,
            "language": lang,
            "grounded": False,
            "fallback_used": False,
            "citations": [],
            "provider": "honest-refusal"
        }


# Convenience singleton
_answer_service = AnswerGenerationService()

def generate_answer(
    question: str,
    course_id: Optional[str] = 'course-va-101',
    language: str = 'am',
    conversation_context: Optional[List[Dict[str, Any]]] = None,
    provider_name: Optional[str] = None,
    institution_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Public functional interface for other modules (Koket's chat, Telegram bot, SMS)."""
    return _answer_service.answer_question(
        question=question,
        course_id=course_id,
        language=language,
        conversation_context=conversation_context,
        provider_name=provider_name,
        institution_id=institution_id,
    )
