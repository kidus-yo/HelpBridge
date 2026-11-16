from rest_framework.permissions import BasePermission

from platforms.services.context import get_platform_context


class IsStaffOrScopedPlatformContext(BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True

        context = get_platform_context(request)
        return bool(
            context
            and context.has_scope("courses:read")
            and context.has_scope("knowledge:read")
        )
