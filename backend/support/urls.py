"""
URL Configuration for Support App.
"""

from django.urls import path
from support.views import (
    SupportRequestListCreateView,
    SupportRequestDetailView,
    SupportRequestStatusView,
    SupportMessageListCreateView,
    ScreenShareControlView,
    ScreenSnapshotView
)

urlpatterns = [
    path('requests/', SupportRequestListCreateView.as_view(), name='support-request-list-create'),
    path('requests/<uuid:id>/', SupportRequestDetailView.as_view(), name='support-request-detail'),
    path('requests/<uuid:id>/status/', SupportRequestStatusView.as_view(), name='support-request-status'),
    path('requests/<uuid:id>/messages/', SupportMessageListCreateView.as_view(), name='support-message-list-create'),
    path('requests/<uuid:id>/screenshare/', ScreenShareControlView.as_view(), name='support-screen-share'),
    path('requests/<uuid:id>/snapshot/', ScreenSnapshotView.as_view(), name='support-screen-snapshot'),
]
