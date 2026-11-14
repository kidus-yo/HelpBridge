"""
Views for Careers, Job Search, Grounded Q&A, Accommodations, and Job Alert Subscriptions.
"""

import secrets
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter

from careers.models import JobListing, AccommodationRequest, JobAlertSubscription
from careers.permissions import IsStaffOrReadOnly, IsAccommodationOwnerOrStaff, IsSubscriptionOwner
from careers.services import JobQAService, JobAlertService
from careers.serializers import (
    JobListingSerializer,
    JobListingAdminSerializer,
    JobQuestionRequestSerializer,
    JobQuestionResponseSerializer,
    AccommodationRequestSerializer,
    JobAlertSubscriptionSerializer
)


class JobListingListCreateView(generics.ListCreateAPIView):
    """
    List published job opportunities for learners (with search/filtering),
    or create a new job listing (staff/admin only).
    """
    permission_classes = [IsStaffOrReadOnly]

    def get_serializer_class(self):
        if self.request.user and self.request.user.is_authenticated and self.request.user.is_staff:
            return JobListingAdminSerializer
        return JobListingSerializer

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated and user.is_staff:
            qs = JobListing.objects.all()
        else:
            qs = JobListing.objects.filter(status='published')

        # Filter by search keyword
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(organization__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search)
            )

        # Filter by location
        location = self.request.query_params.get('location')
        if location:
            qs = qs.filter(location__icontains=location)

        # Filter by employment_type
        emp_type = self.request.query_params.get('employment_type')
        if emp_type:
            qs = qs.filter(employment_type=emp_type)

        # Filter by remote_policy
        remote = self.request.query_params.get('remote_policy')
        if remote:
            qs = qs.filter(remote_policy=remote)

        return qs

    @extend_schema(
        summary="List published jobs",
        parameters=[
            OpenApiParameter('search', str, description="Search keyword in title, organization, description"),
            OpenApiParameter('location', str, description="Filter by location (e.g. Addis Ababa)"),
            OpenApiParameter('employment_type', str, description="Filter by full_time, part_time, internship, contract"),
            OpenApiParameter('remote_policy', str, description="Filter by remote, hybrid, on_site"),
        ],
        responses={200: JobListingSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create a job listing (staff only)",
        request=JobListingAdminSerializer,
        responses={201: JobListingAdminSerializer}
    )
    def perform_create(self, serializer):
        job = serializer.save(created_by=self.request.user)
        if job.status == 'published':
            JobAlertService.dispatch_alerts_for_job(job)


class JobListingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve job details (learners only view published),
    or update/publish/close job listing (staff only).
    """
    permission_classes = [IsStaffOrReadOnly]
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.request.user and self.request.user.is_authenticated and self.request.user.is_staff:
            return JobListingAdminSerializer
        return JobListingSerializer

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated and user.is_staff:
            return JobListing.objects.all()
        return JobListing.objects.filter(status='published')

    def perform_update(self, serializer):
        prev_status = serializer.instance.status
        job = serializer.save()
        # If transitioning to published, dispatch alerts!
        if prev_status != 'published' and job.status == 'published':
            JobAlertService.dispatch_alerts_for_job(job)


class JobQuestionView(APIView):
    """
    Asks a question about a specific published job listing.
    Answers strictly grounded in published fields, refusing unlisted info honestly.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Grounded Job Q&A",
        description="Answers questions about published job details without hallucinating omitted fields.",
        request=JobQuestionRequestSerializer,
        responses={200: JobQuestionResponseSerializer}
    )
    def post(self, request):
        serializer = JobQuestionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job_id = serializer.validated_data['job_id']
        question = serializer.validated_data['question']
        language = serializer.validated_data.get('language', 'en')

        try:
            job = JobListing.objects.get(id=job_id, status='published')
        except JobListing.DoesNotExist:
            return Response(
                {'error': {'code': 'not_found', 'message': 'Published job listing not found.'}},
                status=status.HTTP_404_NOT_FOUND
            )

        answer_data = JobQAService.answer_question(job=job, question=question, language=language)
        return Response(JobQuestionResponseSerializer(answer_data).data, status=status.HTTP_200_OK)


class AccommodationRequestListCreateView(generics.ListCreateAPIView):
    """
    Submit an interview accommodation request (privacy-preserving, functional adjustments only),
    or list submitted requests for the learner/guest or staff.
    """
    serializer_class = AccommodationRequestSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated and user.is_staff:
            return AccommodationRequest.objects.all().select_related('job_listing')

        if user and user.is_authenticated:
            return AccommodationRequest.objects.filter(learner=user).select_related('job_listing')

        token = self.request.headers.get('X-Guest-Token') or self.request.query_params.get('guest_token')
        if token:
            return AccommodationRequest.objects.filter(guest_token=token).select_related('job_listing')

        return AccommodationRequest.objects.none()

    @extend_schema(
        summary="Submit interview accommodation request",
        description="Confidential accommodation request without requiring medical diagnoses.",
        request=AccommodationRequestSerializer,
        responses={201: AccommodationRequestSerializer}
    )
    def perform_create(self, serializer):
        user = self.request.user
        token = self.request.headers.get('X-Guest-Token') or self.request.data.get('guest_token')
        if not user.is_authenticated and not token:
            token = secrets.token_urlsafe(32)

        serializer.save(
            learner=user if user.is_authenticated else None,
            guest_token=token or '',
            status='submitted'
        )


class AccommodationRequestDetailView(generics.RetrieveUpdateAPIView):
    """
    View status of accommodation request (learner/guest or staff),
    or update/respond (staff only).
    """
    queryset = AccommodationRequest.objects.all().select_related('job_listing')
    serializer_class = AccommodationRequestSerializer
    permission_classes = [IsAccommodationOwnerOrStaff]
    lookup_field = 'id'

    def perform_update(self, serializer):
        if self.request.user.is_staff:
            serializer.save(responded_by=self.request.user)
        else:
            serializer.save()


class JobAlertSubscriptionListCreateView(generics.ListCreateAPIView):
    """
    Subscribe to job alert notifications via Telegram or low-bandwidth SMS.
    """
    serializer_class = JobAlertSubscriptionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated and user.is_staff:
            return JobAlertSubscription.objects.all()

        if user and user.is_authenticated:
            return JobAlertSubscription.objects.filter(learner=user)

        token = self.request.headers.get('X-Guest-Token') or self.request.query_params.get('guest_token')
        if token:
            return JobAlertSubscription.objects.filter(guest_token=token)

        return JobAlertSubscription.objects.none()

    @extend_schema(
        summary="Subscribe to job alerts",
        description="Subscribes phone number (SMS) or Telegram ID to new matching job alerts.",
        request=JobAlertSubscriptionSerializer,
        responses={201: JobAlertSubscriptionSerializer}
    )
    def perform_create(self, serializer):
        user = self.request.user
        token = self.request.headers.get('X-Guest-Token') or self.request.data.get('guest_token')
        if not user.is_authenticated and not token:
            token = secrets.token_urlsafe(32)

        serializer.save(
            learner=user if user.is_authenticated else None,
            guest_token=token or '',
            is_active=True
        )


class JobAlertSubscriptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update keywords/status, or unsubscribe from job alerts.
    """
    queryset = JobAlertSubscription.objects.all()
    serializer_class = JobAlertSubscriptionSerializer
    permission_classes = [IsSubscriptionOwner]
    lookup_field = 'id'
