from django.conf import settings
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        db_ok = True
        db_vendor = connection.vendor
        try:
            connection.ensure_connection()
        except Exception:
            db_ok = False
        return Response(
            {
                "status": "ok" if db_ok else "degraded",
                "service": "helpbridge",
                "database": {"ok": db_ok, "vendor": db_vendor},
                "environment": getattr(settings, "DJANGO_ENV", "development"),
            }
        )
