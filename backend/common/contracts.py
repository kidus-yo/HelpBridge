"""
Shared Service Contracts and Decoupled Stubs.
Follows the contract definitions agreed in Milestone 0 of the Team Technical Guide.
Allows Samuel (Developer 3) to test AI grounding and channels independently before
Kidus (Lead/Knowledge Base) and Koket (Chat/Widget) merge their apps.
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from uuid import UUID

DATA_DIR = Path(__file__).resolve().parent.parent / 'ai_engine' / 'data'
SECTIONS_FILE = DATA_DIR / 'default_course_sections.json'

STOP_WORDS = {
    # English stop words
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
    'can', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from',
    'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself',
    'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'just', 'me', 'more', 'most',
    'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our',
    'ours', 'ourselves', 'out', 'over', 'own', 'same', 'she', 'should', 'so', 'some', 'such', 'than',
    'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this',
    'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'we', 'were', 'what', 'when',
    'where', 'which', 'while', 'who', 'whom', 'why', 'with', 'would', 'you', 'your', 'yours', 'yourself',
    'tell', 'explain', 'give',
    # Amharic stop words
    'ነው', 'ናት', 'ናቸው', 'ነበር', 'ነበሩ', 'ሆኖ', 'ሆና', 'እንደ', 'ስለ', 'ጋር', 'ውስጥ', 'ላይ', 'ወደ', 'ከ',
    'የ', 'እና', 'ወይም', 'ግን', 'ነገር', 'ይህ', 'ይህች', 'እነዚህ', 'ያ', 'ያች', 'እነዚያ', 'እኔ', 'አንተ', 'አንቺ',
    'እሱ', 'እሷ', 'እኛ', 'እናንተ', 'እነሱ', 'ማን', 'ምን', 'መቼ', 'የት', 'እንዴት', 'ለምን', 'ያህል', 'በጣም',
    'ሁሉ', 'አንድ', 'ሁለት', 'አለ', 'አሉ', 'የለም', 'የሉም', 'ና', 'እስኪ', 'እባክዎ'
}


class MockKnowledgeRetrievalService:
    """
    Contract implementation representing Kidus's Knowledge Retrieval Service
    Endpoint: POST /api/v1/knowledge/search/
    """
    def __init__(self, sections_file: Optional[Path] = None):
        self.sections_file = sections_file or SECTIONS_FILE
        self._sections = self._load_sections()

    def _load_sections(self) -> List[Dict[str, Any]]:
        if self.sections_file.exists():
            with open(self.sections_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def search(
        self,
        question: str,
        course_id: Optional[str] = None,
        language: str = 'en',
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieves relevant course evidence chunks.
        Strict requirement: Returns an empty list when no relevant material is found.
        Never fabricates passages or citations.
        """
        if not question or not question.strip():
            return []

        all_tokens = re.findall(r'\w+', question.lower())
        content_tokens = set([t for t in all_tokens if t not in STOP_WORDS and len(t) > 1])
        if not content_tokens:
            return []

        scored_results = []
        for s in self._sections:
            content_en = s.get('content_en', '')
            content_am = s.get('content_am', '')
            keywords = [k.lower() for k in s.get('keywords', [])]

            search_blob = f"{s.get('title', '')} {content_en} {s.get('title_am', '')} {content_am}".lower()
            section_tokens = set([t for t in re.findall(r'\w+', search_blob) if t not in STOP_WORDS])

            overlap = content_tokens.intersection(section_tokens)
            if not overlap:
                continue

            # Exact keyword match check
            keyword_overlap = [k for k in keywords if k in content_tokens or k == question.lower().strip()]

            # If only 1 token overlaps out of 2+ question tokens and no explicit keyword, skip
            if len(overlap) < 2 and len(content_tokens) >= 2 and not keyword_overlap:
                continue

            # Title matching boost
            title_text = f"{s.get('title', '')} {s.get('title_am', '')}".lower()
            title_tokens = set([t for t in re.findall(r'\w+', title_text) if t not in STOP_WORDS])
            title_overlap = content_tokens.intersection(title_tokens)

            overlap_ratio = len(overlap) / len(content_tokens)
            relevance = overlap_ratio * 0.5 + (0.2 if keyword_overlap else 0.0)
            if title_overlap:
                relevance += 0.25 * len(title_overlap)

            relevance = min(round(relevance, 2), 0.99)

            if relevance >= 0.25:
                text = content_am if language == 'am' and content_am else content_en
                scored_results.append({
                    'chunk_id': s.get('id', 'chunk-uuid'),
                    'text': text,
                    'document_id': 'doc-va-101',
                    'document_title': s.get('document_title_am', s.get('document_title', 'The Future of VA Work')) if language == 'am' else s.get('document_title', 'The Future of VA Work'),
                    'page': s.get('page', 1),
                    'section': s.get('title_am', s.get('title')) if language == 'am' else s.get('title'),
                    'anchor': s.get('anchor', ''),
                    'url': s.get('url', ''),
                    'relevance': relevance,
                })

        scored_results.sort(key=lambda x: x['relevance'], reverse=True)
        return scored_results[:limit]


class MockChatService:
    """
    Contract implementation representing Koket's Chat and Session Service
    """
    _sessions: Dict[str, Dict[str, Any]] = {}
    _messages: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def create_session(
        cls,
        institution_id: str = 'inst-default',
        course_id: Optional[str] = 'course-va-101',
        channel: str = 'telegram',
        preferred_language: str = 'am',
        external_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        import uuid
        from datetime import datetime, timezone

        session_id = f"sess-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        session = {
            'id': session_id,
            'institution_id': institution_id,
            'course_id': course_id,
            'channel': channel,
            'preferred_language': preferred_language,
            'external_user_id': external_user_id,
            'status': 'active',
            'created_at': now,
            'updated_at': now
        }
        cls._sessions[session_id] = session
        cls._messages[session_id] = []
        return session

    @classmethod
    def get_or_create_session_for_channel(
        cls,
        channel: str,
        external_id: str,
        preferred_language: str = 'am'
    ) -> Dict[str, Any]:
        for s in cls._sessions.values():
            if s.get('channel') == channel and s.get('external_user_id') == str(external_id) and s.get('status') == 'active':
                return s
        return cls.create_session(
            channel=channel,
            preferred_language=preferred_language,
            external_user_id=str(external_id)
        )

    @classmethod
    def append_message(
        cls,
        session_id: str,
        sender_type: str,
        content: str,
        language: str = 'en',
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        import uuid
        from datetime import datetime, timezone

        msg = {
            'id': f"msg-{uuid.uuid4().hex[:10]}",
            'session_id': session_id,
            'sender_type': sender_type,
            'content': content,
            'language': language,
            'metadata': metadata or {},
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        if session_id in cls._messages:
            cls._messages[session_id].append(msg)
        else:
            cls._messages[session_id] = [msg]
        return msg


def search_course_content(
    institution_id: Union[str, UUID],
    query: str,
    course_id: Union[str, UUID, None] = None,
    language: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Kidus's knowledge retrieval contract for the AI / chat teams.

    Implementation lives in knowledge.services.retrieval. This wrapper is the
    stable import path other developers can use without depending on parsers
    or embedding internals.

    Returns an empty list when nothing relevant is found. Never fabricates
    citations. Tenant isolation is enforced by institution_id at query time.
    """
    from knowledge.services.retrieval import search_course_content as _search

    return _search(
        institution_id=institution_id,
        query=query,
        course_id=course_id,
        language=language,
        limit=limit,
    )
