from django.conf import settings
from django.http import HttpResponse
from django.utils.cache import patch_vary_headers


class WidgetCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin")
        allowed_origins = getattr(settings, "CORS_ALLOWED_ORIGINS", ())
        if origin and request.method == "OPTIONS" and origin in allowed_origins:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if origin:
            patch_vary_headers(response, ("Origin",))
            if origin in allowed_origins:
                response["Access-Control-Allow-Origin"] = origin
                if request.method == "OPTIONS":
                    response["Access-Control-Allow-Methods"] = (
                        "GET, POST, PATCH, OPTIONS"
                    )
                    response["Access-Control-Allow-Headers"] = (
                        "Authorization, Content-Type, X-Guest-Token"
                    )
                    response["Access-Control-Max-Age"] = "600"
        return response
