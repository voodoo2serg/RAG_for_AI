from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.archive_ingest.views import ArchiveImportJobViewSet

router = DefaultRouter()
router.register(r'import-jobs', ArchiveImportJobViewSet, basename='import-jobs')

urlpatterns = [
    path('', include(router.urls)),
]
