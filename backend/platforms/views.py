from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from platforms.authentication import IntegrationApiKeyAuthentication, PlatformContextAuthentication
from platforms.models import Institution, Platform, PlatformIntegration
from platforms.permissions import IsStaffOrPlatformContext, IsStaffUser
from platforms.serializers import (
    InstitutionSerializer,
    IssueContextTokenSerializer,
    PlatformIntegrationSerializer,
    PlatformSerializer,
)
from platforms.services.context import (
    PlatformContextError,
    get_platform_context,
    issue_platform_context_token,
)
from platforms.tenant import is_staff


class PlatformListCreateView(generics.ListCreateAPIView):
    queryset = Platform.objects.all()
    serializer_class = PlatformSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsStaffUser]


class PlatformDetailView(generics.RetrieveAPIView):
    queryset = Platform.objects.all()
    serializer_class = PlatformSerializer
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [IsStaffOrPlatformContext]


class InstitutionListCreateView(generics.ListCreateAPIView):
    serializer_class = InstitutionSerializer
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [IsStaffOrPlatformContext]

    def get_queryset(self):
        qs = Institution.objects.filter(is_active=True)
        context = get_platform_context(self.request)
        if context is not None:
            return qs.filter(id=context.institution_id)
        return qs

    def perform_create(self, serializer):
        if not is_staff(self.request):
            raise AuthenticationFailed("Only staff can create institutions.")
        serializer.save()


class InstitutionDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = InstitutionSerializer
    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [IsStaffOrPlatformContext]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        qs = Institution.objects.all()
        context = get_platform_context(self.request)
        if context is not None:
            return qs.filter(id=context.institution_id)
        if is_staff(self.request):
            return qs
        return qs.none()


class PlatformIntegrationCreateView(generics.CreateAPIView):
    queryset = PlatformIntegration.objects.all()
    serializer_class = PlatformIntegrationSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsStaffUser]


class IssuePlatformContextTokenView(APIView):
    authentication_classes = [IntegrationApiKeyAuthentication]
    permission_classes = []

    def post(self, request):
        integration = getattr(request, "platform_integration", None)
        if integration is None:
            raise AuthenticationFailed("Valid integration API key is required.")
        serializer = IssueContextTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            token = issue_platform_context_token(
                integration=integration,
                user_ref=data["user_ref"],
                context_type=data.get("context_type") or "general",
                context_id=data.get("context_id") or None,
                scopes=data.get("scopes"),
                preferred_language=data.get("preferred_language") or "en",
            )
        except PlatformContextError as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "token": token,
                "token_type": "Bearer",
                "expires_in": request.GET.get("ttl") or None,
                "audience": "helpbridge",
            },
            status=status.HTTP_201_CREATED,
        )


class CurrentPlatformContextView(APIView):
    authentication_classes = [PlatformContextAuthentication]
    permission_classes = [IsStaffOrPlatformContext]

    def get(self, request):
        context = get_platform_context(request)
        if context is None:
            raise AuthenticationFailed("Platform context token is required.")
        return Response(
            {
                "platform_id": str(context.platform_id),
                "platform_type": context.platform_type,
                "institution_id": str(context.institution_id),
                "user_ref": context.user_ref,
                "context_type": context.context_type,
                "context_id": context.context_id,
                "scopes": list(context.scopes),
                "preferred_language": context.preferred_language,
                "token_issuer": context.token_issuer,
                "token_audience": context.token_audience,
                "token_expiry": context.token_expiry.isoformat(),
            }
        )
