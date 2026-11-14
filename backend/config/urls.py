"""
URL configuration for Digital Bridge project.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from channels.views import sms_inbound_view

urlpatterns = [
    path('admin/', admin.site.urls),

    # OpenAPI 3 Documentation (Level 2 Integration)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Modular API routes
    path('api/v1/ai/', include('ai_engine.urls')),
    path('api/v1/channels/', include('channels.urls')),
    path('api/v1/chat/', include('chat.urls')),
    path('api/v1/accessibility/', include('accessibility.urls')),

    # Track 3 requirement: Direct /sms/inbound route
    path('sms/inbound', sms_inbound_view, name='direct-sms-inbound'),
]
