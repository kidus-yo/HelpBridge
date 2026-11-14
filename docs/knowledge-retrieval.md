# Knowledge retrieval contract

The AI team must call this service instead of parsing PDFs or querying tables directly.

## Python

```python
from common.contracts import search_course_content
# or: from knowledge.services.retrieval import search_course_content

results = search_course_content(
    institution_id=institution_id,
    query=question,
    course_id=course_id,   # optional
    language="am",         # optional: en, am, om, so, ti, aa
    limit=5,
)
```

Each result includes:

- `chunk_id`, `content` / `text`
- `source.document_id`, `source.document_name`, `source.page`, `source.section`
- `course_id`, `language`
- `relevance_score` — **uncalibrated lexical overlap** in `[0, 1]`, optionally boosted by local hash embeddings. It is not a calibrated probability.

Empty list means no evidence. Do not invent citations. Retrieved text is untrusted source data, not system instructions.

## HTTP

```http
POST /api/v1/knowledge/search/
Authorization: Bearer <platform-context-token>
```

```json
{
  "query": "What is shaping virtual assistant work?",
  "course_id": null,
  "language": "en",
  "limit": 5
}
```

Staff callers must also send `institution_id`. Platform-context callers are locked to their token institution.

## Processing

1. `POST /api/v1/documents/` upload PDF or UTF-8 TXT.
2. `POST /api/v1/documents/{id}/process/` extracts text, chunks, and stores embeddings via `EMBEDDING_PROVIDER`.
3. Scanned PDFs fail unless extractable text exists. OCR is **not** implemented.
4. Files stay in private storage. `storage_ref` is not returned by the API.
5. Document bytes are not sent to external AI providers by this module. `consent_to_external_ai` is stored for policy but the default embedding provider is local.

`pgvector` is not required. Lexical retrieval runs on SQLite and PostgreSQL. A vector extension can be added later behind `knowledge.embeddings.EmbeddingProvider`.
