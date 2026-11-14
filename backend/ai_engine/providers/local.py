"""
Local Model Provider (Ollama / Local OpenAI-compatible API).
Supports running completely locally on host or demo laptop.
"""

import logging
import requests
from typing import List, Dict, Any, Optional
from django.conf import settings
from .base import BaseAIProvider
from .offline import OfflineKeywordProvider

logger = logging.getLogger(__name__)


class LocalAIProvider(BaseAIProvider):
    name: str = "local"

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.endpoint = endpoint or getattr(settings, 'AI_LOCAL_ENDPOINT', 'http://localhost:11434/v1')
        self.model = model or getattr(settings, 'AI_LOCAL_MODEL', 'llama3')
        self._offline_fallback = OfflineKeywordProvider()

    def generate(
        self,
        question: str,
        evidence: List[Dict[str, Any]],
        language: str = "en",
        conversation_context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        lang = 'am' if language == 'am' else 'en'

        if not evidence:
            return self._offline_fallback.generate(question, evidence, language=lang)

        evidence_text = "\n\n".join([
            f"[{c.get('section')}]: {c.get('text')}"
            for c in evidence
        ])

        system_prompt = (
            "You are an assistant for ALX Savanna learners. "
            "Answer ONLY using the course evidence provided. If not covered, reply that it is not in the course."
        )

        url = f"{self.endpoint.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Evidence:\n{evidence_text}\n\nQuestion: {question}"}
            ],
            "temperature": 0.1
        }

        try:
            resp = requests.post(url, json=payload, timeout=6)
            if resp.status_code == 200:
                answer = resp.json()['choices'][0]['message']['content'].strip()
                citations = [
                    {
                        "chunk_id": c.get('chunk_id'),
                        "document_title": c.get('document_title'),
                        "section": c.get('section'),
                        "page": c.get('page', 1),
                        "anchor": c.get('anchor', ''),
                        "url": c.get('url', ''),
                        "relevance": c.get('relevance', 1.0)
                    }
                    for c in evidence[:2]
                ]
                return {
                    "answer": answer,
                    "language": lang,
                    "grounded": True,
                    "fallback_used": False,
                    "citations": citations,
                    "provider": f"{self.name}:{self.model}"
                }
        except Exception:
            pass

        # Fallback to offline keyword provider
        res = self._offline_fallback.generate(question, evidence, language=lang)
        res['provider'] = f"{self.name} (fallback:offline)"
        return res
