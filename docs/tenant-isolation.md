# Tenant isolation

Every course, document, chunk, and processing job belongs to an `Institution`. UUIDs are identifiers, not authorization.

- Platform context tokens bind `institution_id` after server-side signature checks.
- Querysets filter by that institution.
- Supplying another institution's ID in the JSON body is rejected.
- Tests in `courses.tests` and `knowledge.tests` assert institution A cannot read B's courses or knowledge.

Do not implement tenant checks only in the widget. Deletion: removing a `KnowledgeDocument` cascades to chunks and jobs. Institution delete is protected while integrations exist (`PROTECT` on platform/institution FKs). Document files live under `MEDIA_ROOT/private/knowledge/` and must not be published as static media.
