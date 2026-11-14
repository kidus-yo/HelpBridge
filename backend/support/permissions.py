"""
Permissions for Support Requests and Live Help Messaging.
"""

from rest_framework import permissions


def is_support_agent(user):
    return user and user.is_authenticated and (
        user.is_staff or user.groups.filter(name='SupportAgent').exists()
    )


class IsTicketParticipantOrAgent(permissions.BasePermission):
    """
    Ensures only the requesting learner (authenticated or via verified guest token)
    or an authorized support agent / staff member can view or participate in a ticket.
    """

    def has_object_permission(self, request, view, obj):
        # Staff and support agents have access
        if is_support_agent(request.user):
            return True

        # Authenticated learner match
        if request.user and request.user.is_authenticated and obj.learner == request.user:
            return True

        # Unauthenticated guest token match
        token = request.headers.get('X-Guest-Token') or request.query_params.get('guest_token')
        if token and obj.guest_token and token == obj.guest_token:
            return True

        return False


class IsSupportAgentOrStaff(permissions.BasePermission):
    """
    Restricts access to support agents or administrators.
    """

    def has_permission(self, request, view):
        return is_support_agent(request.user)

    def has_object_permission(self, request, view, obj):
        return is_support_agent(request.user)
