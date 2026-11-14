"""
Mock AI Provider for Unit Tests and Deterministic CI Testing.
"""

from typing import List, Dict, Any, Optional
from .base import BaseAIProvider


class MockAIProvider(BaseAIProvider):
    name: str = "mock"

    def __init__(self, should_fail: bool = False, custom_answer: Optional[str] = None):
        self.should_fail = should_fail
        self.custom_answer = custom_answer

    def generate(
        self,
        question: str,
        evidence: List[Dict[str, Any]],
        language: str = "en",
        conversation_context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        lang = 'am' if language == 'am' else 'en'

        if self.should_fail:
            raise RuntimeError("Simulated provider failure for testing resilience")

        if not evidence:
            answer = (
                "ይህንን መረጃ በኮርሱ ይዘት ውስጥ ማግኘት አልቻልኩም። ከሰው አስተማሪ ጋር መነጋገር ይፈልጋሉ?"
                if lang == 'am'
                else "I could not find this information in the course material. Would you like to speak to a human tutor?"
            )
            return {
                "answer": answer,
                "language": lang,
                "grounded": False,
                "fallback_used": False,
                "citations": [],
                "provider": self.name
            }

        answer = self.custom_answer or (
            f"[ሞክ መልስ] ለጥያቄዎ መልስ በክፍል «{evidence[0].get('section')}» ተገኝቷል።"
            if lang == 'am'
            else f"[Mock Answer] Answer for '{question}' derived from '{evidence[0].get('section')}'."
        )

        citations = [
            {
                "chunk_id": evidence[0].get('chunk_id', 'chunk-1'),
                "document_title": evidence[0].get('document_title', 'Course PDF'),
                "section": evidence[0].get('section', 'Section 1'),
                "page": evidence[0].get('page', 1),
                "anchor": evidence[0].get('anchor', '#sec-1'),
                "url": evidence[0].get('url', '/course.html#sec-1'),
                "relevance": evidence[0].get('relevance', 0.95)
            }
        ]

        return {
            "answer": answer,
            "language": lang,
            "grounded": True,
            "fallback_used": False,
            "citations": citations,
            "provider": self.name
        }
