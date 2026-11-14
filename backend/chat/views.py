from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import get_object_or_404
from drf_spectacular.utils import extend_schema
from .models import ChatSession, Message
from .serializers import (
    ChatSessionSerializer,
    CreateChatSessionSerializer,
    MessageSerializer,
    SendMessageSerializer
)
from .services import create_chat_session, process_learner_message

class ChatSessionListCreateView(APIView):
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

        user = request.user if request.user.is_authenticated else None

        session = create_chat_session(
            institution_id=data.get('institution_id', 'inst-default'),
            course_id=data.get('course_id', 'course-va-101'),
            channel=data.get('channel', 'web'),
            preferred_language=data.get('preferred_language', 'en'),
            user=user
        )

        return Response(ChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: ChatSessionSerializer(many=True)}, summary="List chat sessions")
    def get(self, request):
        sessions = ChatSession.objects.all()
        if request.user.is_authenticated:
            sessions = sessions.filter(user=request.user)
        serializer = ChatSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ChatSessionDetailView(APIView):
    """
    GET /api/v1/chat/sessions/{session_id}/ - Retrieve a single chat session.
    """

    @extend_schema(responses={200: ChatSessionSerializer}, summary="Retrieve chat session details")
    def get(self, request, session_id):
        session = get_object_or_404(ChatSession, id=session_id)
        return Response(ChatSessionSerializer(session).data, status=status.HTTP_200_OK)

class MessageListCreateView(APIView):
    """
    GET  /api/v1/chat/sessions/{session_id}/messages/ - Retrieve conversation history.
    POST /api/v1/chat/sessions/{session_id}/messages/ - Post learner message & get grounded answer with citations.
    """

    @extend_schema(responses={200: MessageSerializer(many=True)}, summary="Retrieve messages for a session")
    def get(self, request, session_id):
        session = get_object_or_404(ChatSession, id=session_id)
        messages = session.messages.all().order_by('created_at')
        return Response(MessageSerializer(messages, many=True).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=SendMessageSerializer,
        summary="Send learner message and receive evidence-grounded response"
    )
    def post(self, request, session_id):
        session = get_object_or_404(ChatSession, id=session_id)
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = process_learner_message(
            session_id=session.id,
            content=serializer.validated_data['content'],
            language=serializer.validated_data.get('language')
        )

        return Response(result, status=status.HTTP_200_OK)
