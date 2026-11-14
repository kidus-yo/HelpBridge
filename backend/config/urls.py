
"""
URL Configuration for HelpBridge.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from channels.views import sms_inbound_view
from common.views import HealthView

from careers.urls import (
    accommodation_urlpatterns,
    job_alert_urlpatterns,
)


urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),

    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Health check
    path("api/v1/health/", HealthView.as_view(), name="health"),

    # Your platform foundation
    path("api/v1/", include("platforms.urls")),
    path("api/v1/", include("courses.urls")),
    path("api/v1/", include("knowledge.urls")),

    # AI and communication
    path("api/v1/ai/", include("ai_engine.urls")),
    path("api/v1/channels/", include("channels.urls")),
    path("sms/inbound", sms_inbound_view, name="direct-sms-inbound"),

    # Koket's chat and accessibility
    path("api/v1/chat/", include("chat.urls")),
    path("api/v1/accessibility/", include("accessibility.urls")),

    # Yensew's support and career features
    path("api/v1/support/", include("support.urls")),
    path("api/v1/jobs/", include("careers.urls")),
    path(
        "api/v1/accommodations/",
        include((accommodation_urlpatterns, "accommodations")),
    ),
    path(
        "api/v1/job-alerts/",
        include((job_alert_urlpatterns, "job-alerts")),
    ),
]
