"""
Cloud AI Provider (OpenAI / Gemini / Claude compatible).
Calls a remote LLM API via proxy with strict retrieval evidence prompts.
Falls back safely to the offline keyword provider on missing credentials or network errors.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import requests
from django.conf import settings
from .base import BaseAIProvider
from .offline import OfflineKeywordProvider

logger = logging.getLogger(__name__)


class CloudAIProvider(BaseAIProvider):
    name: str = "cloud"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        endpoint: Optional[str] = None
    ):
        self.api_key = api_key or getattr(settings, 'AI_CLOUD_API_KEY', '')
        self.model = model or getattr(settings, 'AI_CLOUD_MODEL', 'gpt-4o-mini')
        self.endpoint = endpoint or os.getenv('AI_CLOUD_ENDPOINT', 'https://api.openai.com/v1/chat/completions')
        self._offline_fallback = OfflineKeywordProvider()

    def generate(
        self,
        question: str,
        evidence: List[Dict[str, Any]],
        language: str = "en",
        conversation_context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        lang = 'am' if language == 'am' else 'en'

        # If no evidence was found, refuse immediately without calling expensive cloud LLM
        if not evidence:
            return self._offline_fallback.generate(question, evidence, language=lang)

        # If no API key configured, use offline provider directly
        if not self.api_key:
            logger.info("No AI_CLOUD_API_KEY provided; utilizing offline keyword provider.")
            res = self._offline_fallback.generate(question, evidence, language=lang)
            res['provider'] = f"{self.name} (fallback:offline)"
            return res

        # Build evidence context block
        evidence_text = "\n\n".join([
            f"[Source {i+1}: {chunk.get('document_title')} - {chunk.get('section')}]\n{chunk.get('text')}"
            for i, chunk in enumerate(evidence)
        ])

        system_prompt = (
            "You are the Digital Bridge Assistant for ALX Savanna learners.\n"
            "STRICT RULES:\n"
            "1. Answer the question using ONLY the provided course evidence below.\n"
            "2. Do NOT invent information or draw from unsupported memory.\n"
            f"3. Answer in the requested language: {'Amharic (አማርኛ)' if lang == 'am' else 'English'}.\n"
            "4. Keep technical terms and proper names intact where appropriate.\n"
            "5. If the evidence does not answer the question, state honestly that the answer is not in the course and suggest human help."
        )

        user_prompt = f"Course Evidence:\n{evidence_text}\n\nLearner Question: {question}"

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_context:
            for ctx in conversation_context[-3:]:
                messages.append({
                    "role": "user" if ctx.get('sender_type') == 'learner' else "assistant",
                    "content": ctx.get('content', '')
                })
        messages.append({"role": "user", "content": user_prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 500
        }

        try:
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                answer_content = data['choices'][0]['message']['content'].strip()

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
                    "answer": answer_content,
                    "language": lang,
                    "grounded": True,
                    "fallback_used": False,
                    "citations": citations,
                    "provider": f"{self.name}:{self.model}"
                }
            else:
                logger.warning("Cloud provider returned HTTP %s. Falling back to offline.", resp.status_code)
                res = self._offline_fallback.generate(question, evidence, language=lang)
                res['provider'] = f"{self.name} (fallback:offline)"
                return res

        except Exception as err:
            logger.error("Cloud provider error: %s. Falling back to offline provider.", str(err))
            res = self._offline_fallback.generate(question, evidence, language=lang)
            res['provider'] = f"{self.name} (fallback:offline)"
            return res
