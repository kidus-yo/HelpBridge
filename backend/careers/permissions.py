"""
Permissions for Careers, Accommodations, and Subscriptions.
"""

from rest_framework import permissions


class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Allows read-only access for anyone, but write access only to staff/admin.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsAccommodationOwnerOrStaff(permissions.BasePermission):
    """
    Ensures accommodation requests remain strictly private between the requester and staff.
    """

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True

        if request.user and request.user.is_authenticated and obj.learner == request.user:
            return True

        token = request.headers.get('X-Guest-Token') or request.query_params.get('guest_token')
        if token and obj.guest_token and token == obj.guest_token:
            return True

        return False


class IsSubscriptionOwner(permissions.BasePermission):
    """
    Ensures only the subscription owner can view or edit their job alert preferences.
    """

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or obj.learner == request.user:
                return True

        token = request.headers.get('X-Guest-Token') or request.query_params.get('guest_token')
        if token and obj.guest_token and token == obj.guest_token:
            return True

        return False
