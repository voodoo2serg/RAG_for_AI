from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("telegram/", include("apps.chat_events.urls")),
    path("api/", include("apps.api.urls")),
    path("api/", include("apps.archive_ingest.urls")),  # Import API
    path("health/", include("apps.health.urls")),
    path("import-dashboard/", TemplateView.as_view(template_name="dashboard.html")),
    path("import-widget/", TemplateView.as_view(template_name="import-widget-demo.html")),  # Universal widget demo
    path("", include("apps.webui.urls")),
]