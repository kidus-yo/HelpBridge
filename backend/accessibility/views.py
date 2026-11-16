from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from chat.permissions import IsStaffOrScopedPlatformContext
from chat.services import get_accessible_session
from platforms.authentication import PlatformContextAuthentication
from .models import AccessibilityPreference
from .serializers import (
    AccessibilityPreferenceSerializer,
    UpdateAccessibilityPreferenceSerializer
)

class AccessibilityPreferenceDetailView(APIView):
    """
    GET   /api/v1/accessibility/preferences/{session_id}/ - Retrieve preferences for a chat session.
    PATCH /api/v1/accessibility/preferences/{session_id}/ - Update accessibility/language preferences.
    """

    authentication_classes = [SessionAuthentication, PlatformContextAuthentication]
    permission_classes = [IsStaffOrScopedPlatformContext]

    def get_object(self, session_id):
        session = get_accessible_session(self.request, session_id)
        pref, _ = AccessibilityPreference.objects.get_or_create(
            session=session,
            defaults={
                'user': session.user,
                'preferred_language': session.preferred_language
            }
        )
        return pref, session

    @extend_schema(responses={200: AccessibilityPreferenceSerializer}, summary="Retrieve session accessibility preferences")
    def get(self, request, session_id):
        pref, _ = self.get_object(session_id)
        return Response(AccessibilityPreferenceSerializer(pref).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=UpdateAccessibilityPreferenceSerializer,
        responses={200: AccessibilityPreferenceSerializer},
        summary="Update session accessibility preferences"
    )
    def patch(self, request, session_id):
        pref, session = self.get_object(session_id)
        serializer = UpdateAccessibilityPreferenceSerializer(pref, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_pref = serializer.save()

        # Keep session language in sync if updated
        if 'preferred_language' in serializer.validated_data:
            session.preferred_language = serializer.validated_data['preferred_language']
            session.save(update_fields=['preferred_language'])

        return Response(AccessibilityPreferenceSerializer(updated_pref).data, status=status.HTTP_200_OK)
