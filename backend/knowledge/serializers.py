from rest_framework import serializers

from knowledge.models import ContentChunk, DocumentProcessingJob, KnowledgeDocument


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    institution = serializers.UUIDField(source="institution_id", read_only=True)
    course = serializers.UUIDField(source="course_id", read_only=True, allow_null=True)
    lesson = serializers.UUIDField(source="lesson_id", read_only=True, allow_null=True)

    class Meta:
        model = KnowledgeDocument
        fields = [
            "id",
            "institution",
            "course",
            "lesson",
            "original_filename",
            "document_type",
            "language",
            "processing_status",
            "checksum",
            "byte_size",
            "uploaded_at",
            "processed_at",
            "metadata",
            "consent_to_external_ai",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    institution = serializers.UUIDField(required=False)
    course_id = serializers.UUIDField(required=False)
    lesson_id = serializers.UUIDField(required=False)
    language = serializers.CharField(max_length=8, default="en")
    consent_to_external_ai = serializers.BooleanField(default=False)


class KnowledgeSearchSerializer(serializers.Serializer):
    query = serializers.CharField()
    institution_id = serializers.UUIDField(required=False)
    course_id = serializers.UUIDField(required=False)
    language = serializers.CharField(max_length=8, required=False, allow_blank=True)
    limit = serializers.IntegerField(min_value=1, max_value=20, default=5)


class DocumentProcessingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentProcessingJob
        fields = [
            "id",
            "status",
            "error_code",
            "error_message",
            "started_at",
            "finished_at",
            "stats",
            "created_at",
        ]


class ContentChunkSerializer(serializers.ModelSerializer):
    document = serializers.UUIDField(source="document_id", read_only=True)
    institution = serializers.UUIDField(source="institution_id", read_only=True)
    course = serializers.UUIDField(source="course_id", read_only=True, allow_null=True)

    class Meta:
        model = ContentChunk
        fields = [
            "id",
            "document",
            "institution",
            "chunk_text",
            "chunk_index",
            "page_number",
            "section_heading",
            "language",
            "course",
        ]
