from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import FilterSet, filters
from apps.chat_events.models import Message, TelegramSource, OutboundDeliveryLog
from apps.domains_projects.models import Domain, Project
from apps.knowledge.models import KnowledgeItem
from apps.wiki.models import WikiPage
from apps.retrieval.models import RetrievalSession
from apps.retrieval.search import get_search_engine
from .serializers import (
    MessageSerializer, DomainSerializer, ProjectSerializer,
    KnowledgeItemSerializer, WikiPageSerializer, RetrievalSessionSerializer,
    TelegramSourceSerializer, OutboundDeliveryLogSerializer,
)


class MessageFilter(FilterSet):
    project = filters.NumberFilter()
    domain = filters.NumberFilter()
    sender_type = filters.CharFilter()
    message_role = filters.CharFilter()
    rag_eligibility = filters.CharFilter()
    source = filters.NumberFilter()
    min_date = filters.DateTimeFilter(field_name="timestamp", lookup_expr="gte")
    max_date = filters.DateTimeFilter(field_name="timestamp", lookup_expr="lte")

    class Meta:
        model = Message
        fields = ["project", "domain", "sender_type", "message_role", "rag_eligibility", "source"]


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Message.objects.filter(is_deleted=False).select_related("source", "domain", "project", "thread")
    serializer_class = MessageSerializer
    filterset_class = MessageFilter
    ordering_fields = ["timestamp", "created_at"]
    search_fields = ["raw_text", "normalized_text"]


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Project.objects.filter(is_deleted=False).select_related("domain")
    serializer_class = ProjectSerializer
    filterset_fields = ["domain", "status"]


class DomainViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Domain.objects.filter(is_deleted=False)
    serializer_class = DomainSerializer


class TelegramSourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TelegramSource.objects.filter(is_deleted=False).select_related("default_domain", "default_project", "default_agent_profile")
    serializer_class = TelegramSourceSerializer
    filterset_fields = ["source_kind", "is_active", "is_inbound_enabled", "is_outbound_enabled"]


class KnowledgeItemViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeItem.objects.filter(is_deleted=False).select_related("domain", "project")
    serializer_class = KnowledgeItemSerializer
    filterset_fields = ["domain", "project", "knowledge_type", "status"]
    search_fields = ["title", "body"]


class WikiPageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WikiPage.objects.filter(is_deleted=False, is_active=True).select_related("wiki_space")
    serializer_class = WikiPageSerializer
    filterset_fields = ["wiki_space"]


class RetrievalSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RetrievalSession.objects.select_related("user_message")
    serializer_class = RetrievalSessionSerializer
    filterset_fields = ["user_message"]
    ordering_fields = ["created_at"]


class OutboundDeliveryLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OutboundDeliveryLog.objects.select_related("source", "message")
    serializer_class = OutboundDeliveryLogSerializer
    filterset_fields = ["source", "status"]


class SearchView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "")
        project_id = request.query_params.get("project_id")
        domain_id = request.query_params.get("domain_id")
        try:
            limit = max(1, min(int(request.query_params.get("limit", 20)), 100))
        except (ValueError, TypeError):
            limit = 20

        if not query:
            return Response({"error": "Query parameter 'q' is required"}, status=status.HTTP_400_BAD_REQUEST)

        engine = get_search_engine()
        results = engine.search_corpus(
            query,
            project_id=int(project_id) if project_id else None,
            domain_id=int(domain_id) if domain_id else None,
            limit=limit,
        )

        # Separate results by entry type for backward-compatible response
        messages = [r.obj for r in results if r.obj.entry_type == "message" and hasattr(r.obj, "source")]
        knowledge = [r.obj for r in results if r.obj.entry_type == "knowledge"]

        return Response({
            "query": query,
            "messages": MessageSerializer(messages, many=True).data,
            "knowledge": KnowledgeItemSerializer(knowledge, many=True).data,
            "total": len(results),
        })
