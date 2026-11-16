"""Institution-scoped knowledge retrieval.

`search_course_content` is the integration contract for the AI team. It never
returns another institution's chunks. Relevance scores are uncalibrated lexical
overlap in [0, 1], not probabilities.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from django.db.models import QuerySet
from rest_framework.exceptions import PermissionDenied, ValidationError

from knowledge.embeddings import cosine_similarity
from knowledge.models import ContentChunk, KnowledgeDocument
from platforms.models import Institution
from platforms.services.context import get_platform_context
from platforms.tenant import is_staff

STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "what", "how", "why", "with", "from", "this", "that",
}


def search_course_content(
    institution_id: UUID | str,
    query: str,
    course_id: UUID | str | None = None,
    language: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if not query or not str(query).strip() or not course_id:
        return []
    try:
        Institution.objects.get(id=institution_id, is_active=True)
    except Institution.DoesNotExist as exc:
        raise ValidationError({"institution_id": "Unknown institution."}) from exc

    qs = ContentChunk.objects.select_related("document", "course").filter(
        institution_id=institution_id,
        course_id=course_id,
        course__status="published",
        document__processing_status=KnowledgeDocument.ProcessingStatus.COMPLETED,
    )
    if language:
        qs = qs.filter(language=language)
    return _score_chunks(qs, query, limit)


def search_for_request(request, *, query: str, course_id=None, language=None, limit=5, institution_id=None) -> list[dict[str, Any]]:
    context = get_platform_context(request)
    if context is not None:
        if institution_id and str(institution_id) != str(context.institution_id):
            raise PermissionDenied("Cannot search another institution.")
        tenant_id = context.institution_id
        if not context.has_scope("knowledge:read"):
            raise PermissionDenied("Missing knowledge:read scope.")
    elif is_staff(request):
        if not institution_id:
            raise ValidationError({"institution_id": "This field is required."})
        tenant_id = institution_id
    else:
        raise PermissionDenied("Authenticated tenant context is required.")
    return search_course_content(
        institution_id=tenant_id,
        query=query,
        course_id=course_id,
        language=language,
        limit=limit,
    )


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"\w+", text.lower())
        if token not in STOP_WORDS and len(token) > 1
    }


def _score_chunks(qs: QuerySet, query: str, limit: int) -> list[dict[str, Any]]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    query_embedding = None
    scored: list[tuple[float, ContentChunk]] = []
    for chunk in qs.iterator():
        chunk_tokens = _tokenize(chunk.chunk_text + " " + (chunk.section_heading or ""))
        overlap = query_tokens.intersection(chunk_tokens)
        if not overlap:
            continue
        lexical = len(overlap) / max(len(query_tokens), 1)
        vector_score = 0.0
        if chunk.embedding:
            if query_embedding is None:
                from knowledge.embeddings import get_embedding_provider

                embedded = get_embedding_provider().embed_texts([query])[0]
                query_embedding = embedded
            vector_score = cosine_similarity(query_embedding, chunk.embedding)
        # Lexical is the documented score; vector is a weak optional boost only.
        score = min(1.0, lexical + (0.1 * vector_score))
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, chunk in scored[: max(1, min(limit, 20))]:
        results.append(
            {
                "chunk_id": str(chunk.id),
                "content": chunk.chunk_text,
                "text": chunk.chunk_text,
                "source": {
                    "document_id": str(chunk.document_id),
                    "document_name": chunk.document.original_filename,
                    "page": chunk.page_number,
                    "section": chunk.section_heading or "",
                },
                "document_id": str(chunk.document_id),
                "document_title": chunk.document.original_filename,
                "page": chunk.page_number,
                "section": chunk.section_heading or "",
                "course_id": str(chunk.course_id) if chunk.course_id else None,
                "language": chunk.language,
                "relevance_score": round(score, 4),
                "relevance": round(score, 4),
                "score_type": "uncalibrated_lexical_overlap",
            }
        )
    return results
