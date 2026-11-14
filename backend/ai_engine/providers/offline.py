"""
Offline Keyword-based AI Provider.
Fulfills the hackathon requirement:
'Search with no AI at all: split the lesson into sections, score them against
 the question by keywords, and show the best section with its link.
 This is your offline mode, and it is the fallback when no AI is configured. Build it first.'
"""

import re
from typing import List, Dict, Any, Optional
from .base import BaseAIProvider


class OfflineKeywordProvider(BaseAIProvider):
    name: str = "offline-keyword"

    REFUSAL_MESSAGES = {
        'en': (
            "I could not find this information in the course material. "
            "You can click 'Talk to a human' to ask an instructor or support agent."
        ),
        'am': (
            "ይህንን መረጃ በኮርሱ ይዘት ውስጥ ማግኘት አልቻልኩም። "
            "ከሰው አስተማሪ ወይም የድጋፍ ባለሙያ ጋር ለመነጋገር 'ከሰው ጋር ተነጋገር' የሚለውን ይጫኑ።"
        )
    }

    def generate(
        self,
        question: str,
        evidence: List[Dict[str, Any]],
        language: str = "en",
        conversation_context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        lang = 'am' if language == 'am' else 'en'

        if not evidence:
            return {
                "answer": self.REFUSAL_MESSAGES[lang],
                "language": lang,
                "grounded": False,
                "fallback_used": False,
                "citations": [],
                "provider": self.name
            }

        # Select the best matching evidence chunk
        best_chunk = evidence[0]
        chunk_text = best_chunk.get('text', '')
        section_title = best_chunk.get('section', 'Course Content')
        anchor = best_chunk.get('anchor', '')
        url = best_chunk.get('url', '')

        # Sentence-level ranking within the chunk
        sentences = re.split(r'(?<=[.!?።\n])\s+', chunk_text)
        question_tokens = set(re.findall(r'\w+', question.lower()))

        scored_sentences = []
        for s in sentences:
            s_clean = s.strip()
            if not s_clean or len(s_clean) < 15:
                continue
            s_tokens = set(re.findall(r'\w+', s_clean.lower()))
            overlap = len(question_tokens.intersection(s_tokens))
            scored_sentences.append((overlap, s_clean))

        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        # Pick the top 2-3 matching sentences, or the beginning of the section if no single sentence dominated
        if scored_sentences and scored_sentences[0][0] > 0:
            extracted_text = " ".join([s[1] for s in scored_sentences[:3]])
        else:
            extracted_text = " ".join([s.strip() for s in sentences[:3] if s.strip()])

        # Compose grounded answer
        if lang == 'am':
            answer_text = (
                f"በኮርሱ ክፍል «{section_title}» መሠረት፦\n\n"
                f"{extracted_text}"
            )
        else:
            answer_text = (
                f"According to course section «{section_title}»:\n\n"
                f"{extracted_text}"
            )

        citations = [
            {
                "chunk_id": best_chunk.get('chunk_id'),
                "document_title": best_chunk.get('document_title', 'Course Material'),
                "section": section_title,
                "page": best_chunk.get('page', 1),
                "anchor": anchor,
                "url": url,
                "relevance": best_chunk.get('relevance', 1.0)
            }
        ]

        # Add secondary citation if available and relevant
        if len(evidence) > 1 and evidence[1].get('relevance', 0) >= 0.3:
            sec = evidence[1]
            citations.append({
                "chunk_id": sec.get('chunk_id'),
                "document_title": sec.get('document_title', 'Course Material'),
                "section": sec.get('section', 'Course Content'),
                "page": sec.get('page', 1),
                "anchor": sec.get('anchor', ''),
                "url": sec.get('url', ''),
                "relevance": sec.get('relevance', 0)
            })

        return {
            "answer": answer_text,
            "language": lang,
            "grounded": True,
            "fallback_used": False,
            "citations": citations,
            "provider": self.name
        }
