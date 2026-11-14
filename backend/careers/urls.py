"""
URL Configuration for Careers App: Jobs, Accommodations, and Job Alert Subscriptions.
"""

from django.urls import path
from careers.views import (
    JobListingListCreateView,
    JobListingDetailView,
    JobQuestionView,
    AccommodationRequestListCreateView,
    AccommodationRequestDetailView,
    JobAlertSubscriptionListCreateView,
    JobAlertSubscriptionDetailView
)

urlpatterns = [
    # Jobs
    path('', JobListingListCreateView.as_view(), name='job-list-create'),
    path('questions/', JobQuestionView.as_view(), name='job-questions'),
    path('<uuid:id>/', JobListingDetailView.as_view(), name='job-detail'),
]

accommodation_urlpatterns = [
    path('', AccommodationRequestListCreateView.as_view(), name='accommodation-list-create'),
    path('<uuid:id>/', AccommodationRequestDetailView.as_view(), name='accommodation-detail'),
]

job_alert_urlpatterns = [
    path('subscriptions/', JobAlertSubscriptionListCreateView.as_view(), name='job-alert-subscription-list-create'),
    path('subscriptions/<uuid:id>/', JobAlertSubscriptionDetailView.as_view(), name='job-alert-subscription-detail'),
]
