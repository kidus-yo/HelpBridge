"""
Offline FAQ Fallback Service for Digital Bridge Assistant.
Fulfills the requirement:
'Implement an FAQ fallback that can work without the AI provider.
 Search for a suitable FAQ match using a simple, explainable method.
 Clearly mark that the response is an FAQ/fallback answer, not a live AI-generated course explanation.'
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from common.contracts import STOP_WORDS

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
FAQS_FILE = DATA_DIR / 'faqs.json'


class FAQFallbackService:
    def __init__(self, faqs_file: Optional[Path] = None):
        self.faqs_file = faqs_file or FAQS_FILE
        self._faqs = self._load_faqs()

    def _load_faqs(self) -> List[Dict[str, Any]]:
        if self.faqs_file.exists():
            with open(self.faqs_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def match(self, question: str, language: str = 'en') -> Optional[Dict[str, Any]]:
        """
        Check if question matches any curated FAQ entry.
        Returns normalized response dict or None if no match.
        """
        if not question or not question.strip():
            return None

        all_tokens = re.findall(r'\w+', question.lower())
        tokens = set([t for t in all_tokens if t not in STOP_WORDS and len(t) > 1])
        if not tokens:
            return None

        best_faq = None
        best_score = 0.0

        for item in self._faqs:
            keywords = [k.lower() for k in item.get('keywords', [])]
            q_en_tokens = set([t for t in re.findall(r'\w+', item.get('question_en', '').lower()) if t not in STOP_WORDS])
            q_am_tokens = set([t for t in re.findall(r'\w+', item.get('question_am', '').lower()) if t not in STOP_WORDS])

            # Check overlap against question and keywords
            all_target_tokens = q_en_tokens.union(q_am_tokens).union(keywords)
            overlap = tokens.intersection(all_target_tokens)
            if not overlap:
                continue

            # Need at least 2 matching tokens unless the question itself is only 1-2 words
            keyword_matches = [k for k in keywords if k in question.lower() or any(tok in k for tok in tokens)]
            if len(overlap) < 2 and len(tokens) >= 3 and len(keyword_matches) < 2:
                continue

            score = len(overlap) / len(tokens)
            if keyword_matches:
                score += 0.25 * len(keyword_matches)

            if score > best_score:
                best_score = score
                best_faq = item

        # Threshold for acceptable FAQ match
        if best_faq and best_score >= 0.35:
            lang = 'am' if language == 'am' else 'en'
            answer_body = best_faq.get(f'answer_{lang}', best_faq.get('answer_en'))

            prefix = "📌 [ከቀደሙ የተለመዱ ጥያቄዎች (FAQ) የተገኘ መልስ]፦\n\n" if lang == 'am' else "📌 [Offline FAQ Match]:\n\n"

            return {
                "answer": f"{prefix}{answer_body}",
                "language": lang,
                "grounded": False,
                "fallback_used": True,
                "faq_id": best_faq.get('id'),
                "citations": [
                    {
                        "document_title": "Digital Bridge Curated Help & FAQ",
                        "section": best_faq.get('category', 'FAQ').capitalize(),
                        "page": 1
                    }
                ],
                "provider": "offline-faq"
            }

        return None
