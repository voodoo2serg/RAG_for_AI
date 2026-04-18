from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    MessageViewSet, ProjectViewSet, DomainViewSet, TelegramSourceViewSet,
    KnowledgeItemViewSet, WikiPageViewSet, RetrievalSessionViewSet,
    OutboundDeliveryLogViewSet, SearchView,
)

router = DefaultRouter()
router.register("messages", MessageViewSet)
router.register("projects", ProjectViewSet)
router.register("domains", DomainViewSet)
router.register("sources", TelegramSourceViewSet)
router.register("knowledge", KnowledgeItemViewSet)
router.register("wiki", WikiPageViewSet)
router.register("retrieval-sessions", RetrievalSessionViewSet)
router.register("outbound-deliveries", OutboundDeliveryLogViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("search/", SearchView.as_view(), name="api_search"),
]
