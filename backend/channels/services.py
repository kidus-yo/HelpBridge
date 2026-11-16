import hashlib
import hmac
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError

from chat.models import ChatSession
from chat.services import create_chat_session
from courses.models import Course
from platforms.models import PlatformIntegration


def get_or_create_central_chat_session(identity, channel: str) -> ChatSession:
    integration_id = getattr(settings, "CHANNEL_PLATFORM_INTEGRATION_ID", "")
    course_id = getattr(settings, "CHANNEL_DEFAULT_COURSE_ID", "")
    try:
        integration_uuid = UUID(str(integration_id))
        course_uuid = UUID(str(course_id))
        integration = PlatformIntegration.objects.select_related(
            "platform", "institution"
        ).get(
            id=integration_uuid,
            status=PlatformIntegration.Status.ACTIVE,
            platform__is_active=True,
            institution__is_active=True,
        )
        course = Course.objects.get(
            id=course_uuid,
            institution_id=integration.institution_id,
            status=Course.Status.PUBLISHED,
        )
    except (ValueError, PlatformIntegration.DoesNotExist, Course.DoesNotExist) as exc:
        raise ImproperlyConfigured(
            "The messaging channel has no active platform integration and published course."
        ) from exc

    if identity.session_id:
        try:
            session = ChatSession.objects.filter(
                id=identity.session_id,
                platform_integration_id=integration.id,
                platform_user_ref__gt="",
                institution_id=str(integration.institution_id),
                course_id=str(course.id),
                status="active",
            ).first()
        except (ValueError, ValidationError):
            session = None
        if session is not None:
            return session

    identity_digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"{channel}:{integration.id}:{identity.external_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    session = create_chat_session(
        institution_id=str(integration.institution_id),
        course_id=str(course.id),
        channel=channel,
        preferred_language=identity.preferred_language,
        platform_integration_id=integration.id,
        platform_user_ref=f"channel-{identity_digest}",
    )
    identity.session_id = str(session.id)
    identity.save(update_fields=["session_id", "updated_at"])
    return session
