from django.urls import path

from platforms.views import (
    CurrentPlatformContextView,
    InstitutionDetailView,
    InstitutionListCreateView,
    IssuePlatformContextTokenView,
    PlatformDetailView,
    PlatformIntegrationCreateView,
    PlatformListCreateView,
)

urlpatterns = [
    path("platforms/", PlatformListCreateView.as_view(), name="platform-list"),
    path("platforms/<uuid:pk>/", PlatformDetailView.as_view(), name="platform-detail"),
    path("institutions/", InstitutionListCreateView.as_view(), name="institution-list"),
    path("institutions/<uuid:pk>/", InstitutionDetailView.as_view(), name="institution-detail"),
    path("platform-integrations/", PlatformIntegrationCreateView.as_view(), name="platform-integration-create"),
    path("platform-context/tokens/", IssuePlatformContextTokenView.as_view(), name="platform-context-token"),
    path("platform-context/", CurrentPlatformContextView.as_view(), name="platform-context-current"),
]
