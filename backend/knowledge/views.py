from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from knowledge.serializers import (
    DocumentUploadSerializer,
    KnowledgeDocumentSerializer,
    KnowledgeSearchSerializer,
)
from knowledge.services.processing import get_owned_document, process_document, store_upload
from knowledge.services.retrieval import search_for_request
from platforms.authentication import PlatformContextAuthentication
from platforms.permissions import KnowledgeAccessPermission, KnowledgeSearchPermission


class DocumentUploadView(APIView):
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [KnowledgeAccessPermission]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        document = store_upload(
            request,
            uploaded_file=data["file"],
            institution_id=data.get("institution"),
            course_id=data.get("course_id"),
            lesson_id=data.get("lesson_id"),
            language=data.get("language") or "en",
            consent_to_external_ai=data.get("consent_to_external_ai", False),
        )
        return Response(KnowledgeDocumentSerializer(document).data, status=status.HTTP_201_CREATED)


class DocumentDetailView(APIView):
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [KnowledgeAccessPermission]

    def get(self, request, pk):
        document = get_owned_document(request, pk)
        payload = KnowledgeDocumentSerializer(document).data
        payload["chunk_count"] = document.chunks.count()
        return Response(payload)


class DocumentProcessView(APIView):
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [KnowledgeAccessPermission]

    def post(self, request, pk):
        document = get_owned_document(request, pk)
        document = process_document(request, document)
        payload = KnowledgeDocumentSerializer(document).data
        payload["chunk_count"] = document.chunks.count()
        return Response(payload)


class KnowledgeSearchView(APIView):
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [KnowledgeSearchPermission]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = KnowledgeSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        results = search_for_request(
            request,
            query=data["query"],
            course_id=data.get("course_id"),
            language=data.get("language") or None,
            limit=data.get("limit") or 5,
            institution_id=data.get("institution_id"),
        )
        return Response({"results": results, "count": len(results)})
