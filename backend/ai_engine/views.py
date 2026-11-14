"""
Views and API Endpoints for the AI Engine.
Provides Level 2 OpenAPI-documented endpoints for AI status and direct Q&A.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.conf import settings
from ai_engine.services.answer_service import generate_answer


class AIStatusResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="healthy")
    active_provider = serializers.CharField()
    supported_providers = serializers.ListField(child=serializers.CharField())
    grounding_threshold = serializers.FloatField()
    supported_languages = serializers.ListField(child=serializers.CharField())
    offline_fallback_enabled = serializers.BooleanField(default=True)


class AnswerRequestSerializer(serializers.Serializer):
    question = serializers.CharField(required=True, max_length=1000, help_text="Learner's course or platform question")
    course_id = serializers.CharField(required=False, default="course-va-101", help_text="Target course identifier")
    language = serializers.ChoiceField(choices=['en', 'am'], default='am', help_text="Language code ('en' or 'am')")
    provider = serializers.ChoiceField(
        choices=['offline', 'cloud', 'local', 'mock'],
        required=False,
        help_text="Optional AI provider override for testing"
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


class AIStatusView(APIView):
    """Diagnostic endpoint reporting AI engine health and active provider."""

    @extend_schema(
        summary="AI Engine Status",
        description="Check status, active provider, and language capabilities of the AI Engine.",
        responses={200: AIStatusResponseSerializer}
    )
    def get(self, request):
        return Response({
            "status": "healthy",
            "active_provider": getattr(settings, 'AI_PROVIDER', 'offline'),
            "supported_providers": ["offline", "cloud", "local", "mock"],
            "grounding_threshold": getattr(settings, 'AI_GROUNDING_THRESHOLD', 0.20),
            "supported_languages": ["am", "en"],
            "offline_fallback_enabled": True
        })


class AnswerQuestionView(APIView):
    """Direct Level 2 Question Answering endpoint with citations and refusal."""

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
        result = generate_answer(
            question=data['question'],
            course_id=data.get('course_id'),
            language=data.get('language', 'am'),
            provider_name=data.get('provider')
        )
        return Response(result, status=status.HTTP_200_OK)
