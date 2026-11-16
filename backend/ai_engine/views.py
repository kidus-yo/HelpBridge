"""
Views and API Endpoints for the AI Engine.
Provides Level 2 OpenAPI-documented endpoints for AI status and direct Q&A.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.conf import settings
from uuid import UUID

from ai_engine.services.answer_service import (
    KnowledgeRetrievalUnavailable,
    generate_answer,
)
from common.languages import LANGUAGE_CHOICES, SUPPORTED_TUTOR_LANGUAGE_CODES
from courses.models import Course
from platforms.authentication import PlatformContextAuthentication
from platforms.permissions import IsStaffOrPlatformContext, KnowledgeSearchPermission
from platforms.services.context import get_platform_context
from platforms.tenant import get_institution


class AIStatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="ready")
    active_provider = serializers.CharField()
    supported_providers = serializers.ListField(child=serializers.CharField())
    configured_providers = serializers.ListField(child=serializers.CharField())
    active_provider_configured = serializers.BooleanField()
    grounding_threshold = serializers.FloatField()
    supported_languages = serializers.ListField(child=serializers.CharField())
    offline_fallback_enabled = serializers.BooleanField(default=True)


class AnswerRequestSerializer(serializers.Serializer):
    question = serializers.CharField(required=True, max_length=1000, help_text="Learner's course or platform question")
    institution_id = serializers.UUIDField(required=False, help_text="Required for staff requests; inferred from platform context otherwise")
    course_id = serializers.UUIDField(required=False, help_text="Must match the signed platform course context")
    language = serializers.ChoiceField(choices=LANGUAGE_CHOICES, required=False, help_text="Requested response language")
    provider = serializers.ChoiceField(
        choices=['offline', 'cloud', 'local'],
        required=False,
        help_text="Optional configured AI provider override"
    )


class CitationSerializer(serializers.Serializer):
    chunk_id = serializers.CharField(required=False)
    document_title = serializers.CharField()
    section = serializers.CharField()
    page = serializers.IntegerField(default=1)
    anchor = serializers.CharField(required=False)
    url = serializers.CharField(required=False)
    relevance = serializers.FloatField(required=False)


class AnswerResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    language = serializers.CharField()
    grounded = serializers.BooleanField()
    fallback_used = serializers.BooleanField()
    citations = serializers.ListField(child=CitationSerializer())
    provider = serializers.CharField()
    answer_status = serializers.CharField(required=False)
    requested_language = serializers.CharField(required=False)


class AIStatusView(APIView):
    """Diagnostic endpoint reporting AI engine health and active provider."""

    @extend_schema(
        summary="AI Engine Status",
        description="Check status, active provider, and language capabilities of the AI Engine.",
        responses={200: AIStatusResponseSerializer}
    )
    def get(self, request):
        configured = ["offline"]
        if getattr(settings, "AI_CLOUD_API_KEY", ""):
            configured.append("cloud")
        if getattr(settings, "AI_LOCAL_ENDPOINT", ""):
            configured.append("local")
        active_provider = getattr(settings, "AI_PROVIDER", "offline")
        return Response({
            "status": "ready",
            "active_provider": active_provider,
            "supported_providers": ["offline", "cloud", "local"],
            "configured_providers": configured,
            "active_provider_configured": active_provider in configured,
            "grounding_threshold": getattr(settings, 'AI_GROUNDING_THRESHOLD', 0.20),
            "supported_languages": sorted(SUPPORTED_TUTOR_LANGUAGE_CODES),
            "offline_fallback_enabled": True
        })


class AnswerQuestionView(APIView):
    """Direct Level 2 Question Answering endpoint with citations and refusal."""
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [IsStaffOrPlatformContext, KnowledgeSearchPermission]

    @extend_schema(
        summary="Generate Grounded Course Answer",
        description=(
            "Answer a question grounded in course materials. Cites document title, section, "
            "and page. Refuses honestly if no evidence is found."
        ),
        request=AnswerRequestSerializer,
        responses={
            200: OpenApiResponse(response=AnswerResponseSerializer, description="Successful answer"),
            400: OpenApiResponse(description="Invalid request data")
        }
    )
    def post(self, request):
        serializer = AnswerRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": {"code": "validation_error", "fields": serializer.errors}},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        context = get_platform_context(request)
        if context is not None:
            if not context.has_scope("courses:read"):
                raise PermissionDenied("Missing courses:read scope.")
            if context.context_type != "course" or not context.context_id:
                raise ValidationError({"context": "A signed course context is required."})
            if data.get("institution_id") and data["institution_id"] != context.institution_id:
                raise PermissionDenied("Institution ID does not match authenticated tenant context.")
            if data.get("course_id") and str(data["course_id"]) != context.context_id:
                raise PermissionDenied("Course ID does not match authenticated context.")
            institution = get_institution(request)
            course_id = context.context_id
            language = data.get("language") or context.preferred_language
        else:
            institution = get_institution(request, data.get("institution_id"))
            course_id = data.get("course_id")
            language = data.get("language", "en")

        if not course_id:
            raise ValidationError({"course_id": "A course is required."})
        try:
            course_uuid = UUID(str(course_id))
        except (TypeError, ValueError) as exc:
            raise ValidationError({"course_id": "A valid course ID is required."}) from exc
        if not Course.objects.filter(
            id=course_uuid,
            institution=institution,
            status=Course.Status.PUBLISHED,
        ).exists():
            raise NotFound("Published course not found for this institution.")

        try:
            result = generate_answer(
                question=data['question'],
                course_id=str(course_uuid),
                institution_id=str(institution.id),
                language=language,
                provider_name=data.get('provider')
            )
        except KnowledgeRetrievalUnavailable:
            return Response(
                {
                    "error": {
                        "code": "knowledge_unavailable",
                        "message": "Course knowledge is temporarily unavailable. Please try again.",
                    }
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(result, status=status.HTTP_200_OK)
