from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from platforms.models import PlatformIntegration
from platforms.services.context import PlatformContextError, parse_and_validate_token
from platforms.services.credentials import key_prefix, verify_api_key


class PlatformContextAuthentication(BaseAuthentication):
    """Authenticate short-lived signed platform context tokens.

    Header: Authorization: Bearer <token>
    """

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith(f"{self.keyword} "):
            token = request.headers.get("X-HelpBridge-Context")
            if not token:
                return None
        else:
            token = header.split(" ", 1)[1].strip()
        try:
            context = parse_and_validate_token(token)
        except PlatformContextError as exc:
            raise AuthenticationFailed(str(exc)) from exc
        request.platform_context = context
        return (AnonymousUser(), context)


class IntegrationApiKeyAuthentication(BaseAuthentication):
    """Authenticate server-to-server integration API keys.

    Header: Authorization: Api-Key <key>
    Never send this header from browser embed scripts.
    """

    keyword = "Api-Key"

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith(f"{self.keyword} "):
            return None
        raw_key = header.split(" ", 1)[1].strip()
        if not raw_key:
            raise AuthenticationFailed("Missing API key.")
        prefix = key_prefix(raw_key)
        candidates = PlatformIntegration.objects.select_related(
            "platform", "institution"
        ).filter(api_key_prefix=prefix, status=PlatformIntegration.Status.ACTIVE)
        for integration in candidates:
            if verify_api_key(raw_key, integration.api_key_hash):
                request.platform_integration = integration
                return (AnonymousUser(), integration)
        raise AuthenticationFailed("Invalid API key.")
