"""
URL configuration for HelpBridge / Digital Bridge.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from channels.views import sms_inbound_view
from common.views import HealthView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/", include("platforms.urls")),
    path("api/v1/", include("courses.urls")),
    path("api/v1/", include("knowledge.urls")),
    path("api/v1/ai/", include("ai_engine.urls")),
    path("api/v1/channels/", include("channels.urls")),
    path("sms/inbound", sms_inbound_view, name="direct-sms-inbound"),
]
