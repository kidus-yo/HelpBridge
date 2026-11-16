from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from drf_spectacular.utils import extend_schema
from courses.models import Course
from platforms.authentication import PlatformContextAuthentication
from platforms.services.context import get_platform_context
from platforms.tenant import get_institution
from .models import ChatSession, Message
from .permissions import IsStaffOrScopedPlatformContext
from .serializers import (
    ChatSessionSerializer,
    CreateChatSessionSerializer,
    MessageSerializer,
    SendMessageSerializer
)
from .services import (
    accessible_sessions,
    create_chat_session,
    get_accessible_session,
    process_learner_message,
)


class ScopedChatAPIView(APIView):
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [IsStaffOrScopedPlatformContext]

class ChatSessionListCreateView(ScopedChatAPIView):
    """
    POST /api/v1/chat/sessions/ - Create a new chat session.
    GET  /api/v1/chat/sessions/ - List chat sessions.
    """

    @extend_schema(
        request=CreateChatSessionSerializer,
        responses={201: ChatSessionSerializer},
        summary="Create a new chat session"
    )
    def post(self, request):
        serializer = CreateChatSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        context = get_platform_context(request)
        if context is not None:
            institution = get_institution(request, data.get("institution_id"))
            if context.context_type != "course" or not context.context_id:
                raise DRFValidationError(
                    {"context": "A course context is required to start a tutoring session."}
                )
            if data.get("course_id") and str(data["course_id"]) != context.context_id:
                raise PermissionDenied("Course ID does not match authenticated context.")
            course_id = context.context_id
            integration_id = context.integration_id
            user_ref = context.user_ref
            preferred_language = (
                data.get("preferred_language") or context.preferred_language
            )
        else:
            institution = get_institution(request, data.get("institution_id"))
            course_id = data.get("course_id")
            integration_id = None
            user_ref = ""
            preferred_language = data.get("preferred_language", "en")

        if not course_id:
            raise DRFValidationError({"course_id": "A course is required."})
        try:
            course = Course.objects.get(
                id=course_id,
                institution=institution,
                status=Course.Status.PUBLISHED,
            )
        except (Course.DoesNotExist, ValueError):
            raise DRFValidationError(
                {"course_id": "Published course not found for this institution."}
            )

        session = create_chat_session(
            institution_id=str(institution.id),
            course_id=str(course.id),
            channel=data.get('channel', 'web'),
            preferred_language=preferred_language,
            user=request.user if request.user.is_authenticated else None,
            platform_integration_id=integration_id,
            platform_user_ref=user_ref,
        )

        return Response(ChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: ChatSessionSerializer(many=True)}, summary="List chat sessions")
    def get(self, request):
        serializer = ChatSessionSerializer(accessible_sessions(request), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChatSessionDetailView(ScopedChatAPIView):
    """
    GET /api/v1/chat/sessions/{session_id}/ - Retrieve a single chat session.
    """

    @extend_schema(responses={200: ChatSessionSerializer}, summary="Retrieve chat session details")
    def get(self, request, session_id):
        session = get_accessible_session(request, session_id)
        return Response(ChatSessionSerializer(session).data, status=status.HTTP_200_OK)


class MessageListCreateView(ScopedChatAPIView):
    """
    GET  /api/v1/chat/sessions/{session_id}/messages/ - Retrieve conversation history.
    POST /api/v1/chat/sessions/{session_id}/messages/ - Post learner message & get grounded answer with citations.
    """

    @extend_schema(responses={200: MessageSerializer(many=True)}, summary="Retrieve messages for a session")
    def get(self, request, session_id):
        session = get_accessible_session(request, session_id)
        messages = session.messages.all().order_by('created_at')
        return Response(MessageSerializer(messages, many=True).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=SendMessageSerializer,
        summary="Send learner message and receive evidence-grounded response"
    )
    def post(self, request, session_id):
        session = get_accessible_session(request, session_id)
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = process_learner_message(
            session_id=session.id,
            content=serializer.validated_data['content'],
            language=serializer.validated_data.get('language')
        )

        return Response(result, status=status.HTTP_200_OK)
