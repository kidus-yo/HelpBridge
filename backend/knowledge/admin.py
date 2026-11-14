from django.contrib import admin

from knowledge.models import ContentChunk, DocumentProcessingJob, KnowledgeDocument


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "institution", "document_type", "processing_status", "language")
    list_filter = ("processing_status", "document_type", "language")
    readonly_fields = ("storage_ref", "checksum")
    search_fields = ("original_filename", "checksum")


@admin.register(ContentChunk)
class ContentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "page_number", "language")


@admin.register(DocumentProcessingJob)
class DocumentProcessingJobAdmin(admin.ModelAdmin):
    list_display = ("document", "status", "error_code", "created_at")
