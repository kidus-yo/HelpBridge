"""
Views for Support Requests, Messaging, and Screen Sharing.
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse

from support.models import SupportRequest, SupportMessage
from support.permissions import IsTicketParticipantOrAgent, IsSupportAgentOrStaff, is_support_agent
from support.services import EscalationService
from support.serializers import (
    SupportRequestListSerializer,
    SupportRequestDetailSerializer,
    SupportRequestCreateSerializer,
    SupportRequestStatusUpdateSerializer,
    SupportMessageSerializer,
    ScreenShareControlSerializer,
    ScreenSnapshotSerializer
)


class SupportRequestListCreateView(generics.ListCreateAPIView):
    """
    List support tickets (filtered to requester or all for agents),
    or create a new ticket with one-click escalation and optional chat consent.
    """
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SupportRequestCreateSerializer
        return SupportRequestListSerializer

    def get_queryset(self):
        user = self.request.user
        if is_support_agent(user):
            return SupportRequest.objects.all().select_related('assigned_agent')

        if user.is_authenticated:
            return SupportRequest.objects.filter(learner=user).select_related('assigned_agent')

        # Guest tokens from headers or query param
        guest_token = self.request.headers.get('X-Guest-Token') or self.request.query_params.get('guest_token')
        if guest_token:
            return SupportRequest.objects.filter(guest_token=guest_token).select_related('assigned_agent')

        return SupportRequest.objects.none()

    @extend_schema(
        summary="Create a new support request",
        description="Initiates human escalation with category, subject, description, and explicit chat consent.",
        request=SupportRequestCreateSerializer,
        responses={201: SupportRequestDetailSerializer}
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = request.headers.get('X-Guest-Token') or request.data.get('guest_token')
        ticket = EscalationService.create_support_request(
            subject=serializer.validated_data['subject'],
            description=serializer.validated_data['description'],
            category=serializer.validated_data.get('category', 'course'),
            priority=serializer.validated_data.get('priority', 'normal'),
            preferred_assistance_mode=serializer.validated_data.get('preferred_assistance_mode', 'chat'),
            learner=request.user if request.user.is_authenticated else None,
            guest_token=token,
            institution_id=serializer.validated_data.get('institution_id'),
            chat_session_id=serializer.validated_data.get('chat_session_id'),
            learner_consent_chat_history=serializer.validated_data.get('learner_consent_chat_history', False),
            language=serializer.validated_data.get('language', 'en')
        )

        response_serializer = SupportRequestDetailSerializer(ticket)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class SupportRequestDetailView(generics.RetrieveAPIView):
    """
    Retrieve ticket details, message history, and accessibility status announcements.
    """
    queryset = SupportRequest.objects.all().select_related('assigned_agent').prefetch_related('messages')
    serializer_class = SupportRequestDetailSerializer
    permission_classes = [IsTicketParticipantOrAgent]
    lookup_field = 'id'


class SupportRequestStatusView(APIView):
    """
    Update support ticket status or assign agent (support agent or staff only).
    """
    permission_classes = [IsSupportAgentOrStaff]

    @extend_schema(
        summary="Update support ticket status or assign agent",
        request=SupportRequestStatusUpdateSerializer,
        responses={200: SupportRequestDetailSerializer}
    )
    def patch(self, request, id):
        try:
            ticket = SupportRequest.objects.get(id=id)
        except SupportRequest.DoesNotExist:
            return Response({'error': {'code': 'not_found', 'message': 'Ticket not found.'}}, status=status.HTTP_404_NOT_FOUND)

        serializer = SupportRequestStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']
        agent = request.user if serializer.validated_data.get('assign_to_me') else None

        updated_ticket = EscalationService.update_status(ticket, new_status=new_status, agent=agent)
        return Response(SupportRequestDetailSerializer(updated_ticket).data, status=status.HTTP_200_OK)


class SupportMessageListCreateView(generics.ListCreateAPIView):
    """
    List messages or post a message in a support ticket thread.
    """
    serializer_class = SupportMessageSerializer
    permission_classes = [IsTicketParticipantOrAgent]

    def get_queryset(self):
        ticket_id = self.kwargs['id']
        return SupportMessage.objects.filter(support_request_id=ticket_id)

    @extend_schema(
        summary="Post a message in support ticket thread",
        request=SupportMessageSerializer,
        responses={201: SupportMessageSerializer}
    )
    def create(self, request, id):
        try:
            ticket = SupportRequest.objects.get(id=id)
        except SupportRequest.DoesNotExist:
            return Response({'error': {'code': 'not_found', 'message': 'Ticket not found.'}}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, ticket)

        content = request.data.get('content')
        if not content or not str(content).strip():
            return Response({'error': {'code': 'validation_error', 'fields': {'content': ['Message content cannot be empty.']}}}, status=status.HTTP_400_BAD_REQUEST)

        # Determine sender type
        if is_support_agent(request.user):
            sender_type = 'agent'
        else:
            sender_type = 'learner'

        msg = EscalationService.post_message(
            ticket=ticket,
            sender_type=sender_type,
            content=content,
            sender=request.user if request.user.is_authenticated else None
        )
        return Response(SupportMessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class ScreenShareControlView(APIView):
    """
    Learner-controlled screen sharing initiation and termination.
    Strictly learner-initiated.
    """
    permission_classes = [IsTicketParticipantOrAgent]

    @extend_schema(
        summary="Control screen sharing session (start/stop)",
        request=ScreenShareControlSerializer,
        responses={200: OpenApiResponse(description="Screen share status details")}
    )
    def post(self, request, id):
        try:
            ticket = SupportRequest.objects.get(id=id)
        except SupportRequest.DoesNotExist:
            return Response({'error': {'code': 'not_found', 'message': 'Ticket not found.'}}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, ticket)

        serializer = ScreenShareControlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']

        if action == 'start':
            result = EscalationService.start_screen_share(ticket)
        else:
            result = EscalationService.stop_screen_share(ticket)

        return Response(result, status=status.HTTP_200_OK)


class ScreenSnapshotView(APIView):
    """
    Low-bandwidth fallback: Sends a static DOM / screenshot snapshot to the support agent.
    """
    permission_classes = [IsTicketParticipantOrAgent]

    @extend_schema(
        summary="Send screen snapshot (low-bandwidth mode)",
        request=ScreenSnapshotSerializer,
        responses={201: SupportMessageSerializer}
    )
    def post(self, request, id):
        try:
            ticket = SupportRequest.objects.get(id=id)
        except SupportRequest.DoesNotExist:
            return Response({'error': {'code': 'not_found', 'message': 'Ticket not found.'}}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, ticket)

        serializer = ScreenSnapshotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        msg = EscalationService.send_screen_snapshot(
            ticket=ticket,
            snapshot_data=serializer.validated_data['snapshot_data'],
            description=serializer.validated_data.get('description', '')
        )
        return Response(SupportMessageSerializer(msg).data, status=status.HTTP_201_CREATED)
