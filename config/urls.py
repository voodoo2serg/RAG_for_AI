from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("telegram/", include("apps.chat_events.urls")),
    path("api/", include("apps.api.urls")),
    path("api/", include("apps.archive_ingest.urls")),  # Import API
    path("health/", include("apps.health.urls")),
    path("import-dashboard/", TemplateView.as_view(template_name="dashboard.html")),  # Import Dashboard
    path("", include("apps.webui.urls")),
]