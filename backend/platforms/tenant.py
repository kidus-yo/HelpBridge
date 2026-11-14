from uuid import UUID

from rest_framework.exceptions import PermissionDenied, ValidationError

from platforms.models import Institution
from platforms.services.context import get_platform_context


def is_staff(request) -> bool:
    return bool(request.user and request.user.is_authenticated and request.user.is_staff)


def resolve_institution_id(request, claimed_id=None) -> UUID:
    """Server-validated tenant. Client-supplied IDs are ignored unless staff."""
    context = get_platform_context(request)
    if context is not None:
        if claimed_id and str(claimed_id) != str(context.institution_id):
            raise PermissionDenied("Institution ID does not match authenticated tenant context.")
        return context.institution_id
    if is_staff(request):
        if not claimed_id:
            raise ValidationError({"institution": "This field is required."})
        return UUID(str(claimed_id))
    raise PermissionDenied("Authenticated tenant context is required.")


def get_institution(request, claimed_id=None) -> Institution:
    institution_id = resolve_institution_id(request, claimed_id)
    try:
        return Institution.objects.get(id=institution_id, is_active=True)
    except Institution.DoesNotExist as exc:
        raise PermissionDenied("Institution is not available.") from exc
