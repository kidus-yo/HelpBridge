"""
Abstract Base Provider Interface for Digital Bridge Assistant.
Allows switching seamlessly between Cloud models, Local models (Ollama),
and Offline Keyword/FAQ fallback without modifying application or view logic.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseAIProvider(ABC):
    """Abstract interface for AI answer generation providers."""

    name: str = "base"

    @abstractmethod
    def generate(
        self,
        question: str,
        evidence: List[Dict[str, Any]],
        language: str = "en",
        conversation_context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a retrieval-grounded answer.

        :param question: Learner's question
        :param evidence: List of evidence chunks with text, document_title, page, section, anchor
        :param language: 'en' or 'am'
        :param conversation_context: Optional previous chat message history
        :return: Normalized response dict:
            {
                "answer": str,
                "citations": List[Dict[str, Any]],
                "grounded": bool,
                "fallback_used": bool,
                "provider": str
            }
        """
        pass
