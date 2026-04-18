from rest_framework import serializers
from apps.chat_events.models import Message, TelegramSource, OutboundDeliveryLog
from apps.domains_projects.models import Domain, Project
from apps.knowledge.models import KnowledgeItem
from apps.wiki.models import WikiPage
from apps.retrieval.models import RetrievalSession


class TelegramSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramSource
        fields = [
            "id", "slug", "display_name", "source_kind", "bot_username", "is_active",
            "is_inbound_enabled", "is_outbound_enabled", "default_retrieval_mode"
        ]


class MessageSerializer(serializers.ModelSerializer):
    source = TelegramSourceSerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            "id", "source", "telegram_message_id", "sender_type",
            "raw_text", "normalized_text", "timestamp",
            "domain", "project", "thread", "message_role",
            "rag_eligibility", "message_value_tier", "sensitivity_level", "retrieval_mode_default",
        ]
        read_only_fields = fields


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ["id", "name", "slug", "description", "is_active"]


class ProjectSerializer(serializers.ModelSerializer):
    domain = DomainSerializer(read_only=True)

    class Meta:
        model = Project
        fields = ["id", "domain", "canonical_name", "slug", "description", "status"]


class KnowledgeItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeItem
        fields = ["id", "domain", "project", "knowledge_type", "title", "body", "confidence", "status"]


class WikiPageSerializer(serializers.ModelSerializer):
    latest_content = serializers.SerializerMethodField()

    class Meta:
        model = WikiPage
        fields = ["id", "wiki_space", "title", "slug", "page_type", "summary", "is_active", "latest_content"]

    def get_latest_content(self, obj):
        rev = obj.revisions.order_by("-created_at").first()
        return rev.content_text if rev else ""


class RetrievalSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetrievalSession
        fields = [
            "id", "user_message", "query_text", "routing_snapshot", "applied_context_pack_ids",
            "final_prompt_text", "model_name", "model_output", "latency_ms", "relevance_score", "created_at",
        ]


class OutboundDeliveryLogSerializer(serializers.ModelSerializer):
    source = TelegramSourceSerializer(read_only=True)

    class Meta:
        model = OutboundDeliveryLog
        fields = ["id", "source", "target_chat_id", "status", "provider_message_id", "error_text", "created_at"]
