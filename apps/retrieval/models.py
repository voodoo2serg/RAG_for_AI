from django.db import models
from apps.core.models import TimeStampedModel
from apps.core.vector import EmbeddingField
from apps.chat_events.models import Message, TelegramSource
from apps.domains_projects.models import Domain, Project
from apps.threads.models import Thread
from apps.core.enums import RetrievalMode, SensitivityLevel


class RagCorpusEntry(TimeStampedModel):
    class EntryType(models.TextChoices):
        MESSAGE = "message", "Message"
        SUMMARY = "summary", "Summary"
        KNOWLEDGE = "knowledge", "Knowledge"
        WIKI = "wiki", "Wiki"
        RULE = "rule", "Rule"

    class SourceObjectType(models.TextChoices):
        MESSAGE = "message", "Message"
        SUMMARY = "summary", "Summary"
        KNOWLEDGE = "knowledge", "Knowledge"
        WIKI_PAGE = "wiki_page", "Wiki Page"
        CONTEXT_RULE = "context_rule", "Context Rule"

    entry_type = models.CharField(max_length=32, choices=EntryType.choices)
    source_object_type = models.CharField(max_length=32, choices=SourceObjectType.choices)
    source_object_id = models.PositiveIntegerField()
    source = models.ForeignKey(TelegramSource, null=True, blank=True, on_delete=models.SET_NULL, related_name="rag_entries")
    domain = models.ForeignKey(Domain, null=True, blank=True, on_delete=models.SET_NULL, related_name="rag_entries")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="rag_entries")
    thread = models.ForeignKey(Thread, null=True, blank=True, on_delete=models.SET_NULL, related_name="rag_entries")
    text = models.TextField()
    title = models.CharField(max_length=255, blank=True)
    message_role = models.CharField(max_length=64, blank=True)
    retrieval_mode = models.CharField(max_length=64, choices=RetrievalMode.choices, default=RetrievalMode.BUSINESS)
    sensitivity_level = models.CharField(max_length=32, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    trust_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.50)
    freshness_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.50)
    source_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    retrieval_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    storage_tier = models.CharField(max_length=16, default="hot")
    redaction_status = models.CharField(max_length=16, default="clean")
    duplicate_group_key = models.CharField(max_length=128, blank=True)
    last_indexed_at = models.DateTimeField(null=True, blank=True)
    is_reviewed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    embedding = EmbeddingField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["entry_type", "is_active"]),
            models.Index(fields=["source_object_type", "source_object_id"]),
            models.Index(fields=["domain", "project", "thread"]),
            models.Index(fields=["retrieval_mode", "message_role"]),
            models.Index(fields=["source", "project"]),
            models.Index(fields=["trust_score", "freshness_score"]),
            models.Index(fields=["source_weight", "retrieval_weight"]),
            models.Index(fields=["storage_tier", "redaction_status"]),
            models.Index(fields=["duplicate_group_key"]),
        ]
        unique_together = [("source_object_type", "source_object_id")]

    def __str__(self):
        return f"{self.entry_type}:{self.source_object_type}:{self.source_object_id}"


class RetrievalSession(TimeStampedModel):
    user_message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="retrieval_sessions")
    query_text = models.TextField()
    routing_snapshot = models.JSONField(default=dict, blank=True)
    selected_corpus_entry_ids = models.JSONField(default=list, blank=True)
    selected_message_ids = models.JSONField(default=list, blank=True)
    selected_summary_ids = models.JSONField(default=list, blank=True)
    selected_knowledge_item_ids = models.JSONField(default=list, blank=True)
    selected_prompt_ids = models.JSONField(default=list, blank=True)
    applied_context_pack_ids = models.JSONField(default=list, blank=True)
    final_prompt_text = models.TextField(blank=True)
    model_name = models.CharField(max_length=128, blank=True)
    model_output = models.TextField(blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    relevance_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    runtime_snapshot = models.JSONField(default=dict, blank=True)
    diagnostics_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"RS:{self.id}"



class RetrievalEvaluationCase(TimeStampedModel):
    name = models.CharField(max_length=255)
    query_text = models.TextField()
    retrieval_mode = models.CharField(max_length=64, choices=RetrievalMode.choices, default=RetrievalMode.BUSINESS)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="retrieval_eval_cases")
    domain = models.ForeignKey(Domain, null=True, blank=True, on_delete=models.SET_NULL, related_name="retrieval_eval_cases")
    source = models.ForeignKey(TelegramSource, null=True, blank=True, on_delete=models.SET_NULL, related_name="retrieval_eval_cases")
    expected_corpus_entry_ids = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class RetrievalEvaluationRun(TimeStampedModel):
    name = models.CharField(max_length=255)
    query_count = models.PositiveIntegerField(default=0)
    average_recall_at_5 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    average_mrr = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    summary = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name


class RetrievalEvaluationResult(TimeStampedModel):
    run = models.ForeignKey(RetrievalEvaluationRun, on_delete=models.CASCADE, related_name="results")
    case = models.ForeignKey(RetrievalEvaluationCase, on_delete=models.CASCADE, related_name="results")
    retrieved_entry_ids = models.JSONField(default=list, blank=True)
    recall_at_5 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    mrr = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    diagnostics = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("run", "case")]


class RetrievalFeedback(TimeStampedModel):
    session = models.ForeignKey(RetrievalSession, on_delete=models.CASCADE, related_name="feedback")
    rating = models.SmallIntegerField(default=0)
    note = models.TextField(blank=True)
    reviewer = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return f"Feedback:{self.session_id}:{self.rating}"


class ReviewQueueItem(TimeStampedModel):
    class QueueType(models.TextChoices):
        PROJECT_MERGE = "project_merge", "Project Merge"
        THREAD_REVIEW = "thread_review", "Thread Review"
        MESSAGE_RELABEL = "message_relabel", "Message Relabel"
        KNOWLEDGE_PROMOTION = "knowledge_promotion", "Knowledge Promotion"
        WIKI_DRAFT = "wiki_draft", "Wiki Draft"
        RETRIEVAL_OUTLIER = "retrieval_outlier", "Retrieval Outlier"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        APPLIED = "applied", "Applied"

    queue_type = models.CharField(max_length=32, choices=QueueType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    title = models.CharField(max_length=255)
    payload = models.JSONField(default=dict, blank=True)
    priority = models.IntegerField(default=100)
    source = models.ForeignKey(TelegramSource, null=True, blank=True, on_delete=models.SET_NULL, related_name="review_queue_items")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="review_queue_items")
    domain = models.ForeignKey(Domain, null=True, blank=True, on_delete=models.SET_NULL, related_name="review_queue_items")

    class Meta:
        ordering = ["priority", "-created_at"]

    def __str__(self):
        return self.title
