from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/", include("apps.tenants.urls")),
    path("api/", include("apps.campaigns.urls")),
    path("api/", include("apps.calls.urls")),
    path("webhooks/", include("apps.whatsapp.urls")),
    path("webhooks/", include("apps.calls.webhook_urls")),
    path("internal/", include("apps.campaigns.internal_urls")),
]
