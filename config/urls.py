from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("telegram/", include("apps.chat_events.urls")),
    path("api/", include("apps.api.urls")),
    path("api/", include("apps.archive_ingest.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("health/", include("apps.health.urls")),
    path("metrics/", include("django_prometheus.urls")),
    path("import-dashboard/", TemplateView.as_view(template_name="dashboard.html")),
    path("import-widget/", TemplateView.as_view(template_name="import-widget-demo.html")),
    path("", include("apps.webui.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)