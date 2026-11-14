from django.contrib.auth import get_user_model

from platforms.models import Institution, Platform, PlatformIntegration
from platforms.services.context import DEFAULT_SCOPES, issue_platform_context_token
from platforms.services.credentials import generate_api_key, hash_api_key, key_prefix

User = get_user_model()

WRITE_SCOPES = list(DEFAULT_SCOPES) + ["courses:write", "knowledge:write"]


def staff_user(username="kidus"):
    return User.objects.create_user(username=username, password="pass", is_staff=True)


def make_platform(slug="savanna", name="ALX Savanna"):
    return Platform.objects.create(
        name=name,
        slug=slug,
        platform_type=Platform.PlatformType.LMS,
        description="Learning platform",
    )


def make_institution(slug="alx", name="ALX Ethiopia"):
    return Institution.objects.create(
        name=name,
        slug=slug,
        institution_type=Institution.InstitutionType.TRAINING,
    )


def make_integration(platform=None, institution=None, scopes=None):
    platform = platform or make_platform()
    institution = institution or make_institution()
    raw = generate_api_key()
    integration = PlatformIntegration.objects.create(
        platform=platform,
        institution=institution,
        name=f"{institution.slug}-integration",
        permitted_scopes=scopes or WRITE_SCOPES,
        api_key_hash=hash_api_key(raw),
        api_key_prefix=key_prefix(raw),
    )
    integration.raw_api_key = raw
    return integration


def context_token(integration, user_ref="learner-anon-1", **kwargs):
    return issue_platform_context_token(
        integration=integration,
        user_ref=user_ref,
        **kwargs,
    )
