from django.urls import path
from .views import AccessibilityPreferenceDetailView

urlpatterns = [
    path('preferences/<uuid:session_id>/', AccessibilityPreferenceDetailView.as_view(), name='accessibility-preference-detail'),
]

