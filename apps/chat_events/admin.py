from django.contrib import admin
from .models import TelegramSource, Message, MessageContactLink, OutboundDeliveryLog


@admin.register(TelegramSource)
class TelegramSourceAdmin(admin.ModelAdmin):
    list_display = ("slug", "display_name", "source_kind", "is_active", "is_inbound_enabled", "is_outbound_enabled", "default_domain", "default_project", "default_agent_profile")
    search_fields = ("slug", "display_name", "bot_username")
    list_filter = ("source_kind", "is_active", "is_inbound_enabled", "is_outbound_enabled")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "telegram_message_id", "timestamp", "project", "message_role", "retrieval_mode_default")
    search_fields = ("raw_text", "normalized_text")
    list_filter = ("source", "message_role", "retrieval_mode_default", "rag_eligibility")


admin.site.register(MessageContactLink)
admin.site.register(OutboundDeliveryLog)
