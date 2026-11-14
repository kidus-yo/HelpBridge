from rest_framework.permissions import BasePermission, SAFE_METHODS

from platforms.services.context import get_platform_context


class IsStaffUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class HasPlatformContext(BasePermission):
    def has_permission(self, request, view):
        return get_platform_context(request) is not None


class IsStaffOrPlatformContext(BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True
        return get_platform_context(request) is not None


class HasRequiredScope(BasePermission):
    read_scope = ""
    write_scope = ""

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True
        context = get_platform_context(request)
        if context is None:
            return False
        required = self.read_scope if request.method in SAFE_METHODS else self.write_scope
        if not required:
            return True
        return context.has_scope(required)


class CourseAccessPermission(HasRequiredScope):
    read_scope = "courses:read"
    write_scope = "courses:write"


class KnowledgeAccessPermission(HasRequiredScope):
    read_scope = "knowledge:read"
    write_scope = "knowledge:write"


class KnowledgeSearchPermission(HasRequiredScope):
    read_scope = "knowledge:read"
    write_scope = "knowledge:read"
