
from django.contrib import admin
from .models import RagCorpusEntry, RetrievalSession, RetrievalEvaluationCase, RetrievalEvaluationRun, RetrievalEvaluationResult, ReviewQueueItem, RetrievalFeedback

@admin.register(RagCorpusEntry)
class RagCorpusEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "entry_type", "title", "source", "project", "storage_tier", "redaction_status", "is_reviewed", "is_active")
    list_filter = ("entry_type", "storage_tier", "redaction_status", "is_active", "source")
    search_fields = ("title", "text")

@admin.register(RetrievalSession)
class RetrievalSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user_message", "model_name", "relevance_score", "created_at")
    search_fields = ("query_text", "model_output")

@admin.register(RetrievalEvaluationCase)
class RetrievalEvaluationCaseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "source", "retrieval_mode")
    search_fields = ("name", "query_text")

@admin.register(RetrievalEvaluationRun)
class RetrievalEvaluationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "query_count", "average_recall_at_5", "average_mrr", "created_at")

@admin.register(RetrievalEvaluationResult)
class RetrievalEvaluationResultAdmin(admin.ModelAdmin):
    list_display = ("id", "run", "case", "recall_at_5", "mrr")

@admin.register(ReviewQueueItem)
class ReviewQueueItemAdmin(admin.ModelAdmin):
    list_display = ("id", "queue_type", "title", "status", "source", "project", "priority", "created_at")
    list_filter = ("queue_type", "status", "source")
    search_fields = ("title",)

@admin.register(RetrievalFeedback)
class RetrievalFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "rating", "reviewer", "created_at")
