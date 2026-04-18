from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("telegram/", include("apps.chat_events.urls")),
    path("api/", include("apps.api.urls")),
    path("health/", include("apps.health.urls")),
    path("", include("apps.webui.urls")),
]
