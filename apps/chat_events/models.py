from django.db import models
from apps.core.models import TimeStampedModel
from apps.core.vector import EmbeddingField
from apps.core.enums import SensitivityLevel, RetrievalMode
from apps.contacts.models import Contact
from apps.domains_projects.models import Domain, Project
from apps.threads.models import Thread


class TelegramSource(TimeStampedModel):
    class SourceKind(models.TextChoices):
        LIVE_BOT = "live_bot", "Live Bot"
        ARCHIVE_IMPORT = "archive_import", "Archive Import"

    slug = models.SlugField(unique=True)
    display_name = models.CharField(max_length=255)
    source_kind = models.CharField(max_length=32, choices=SourceKind.choices)
    bot_username = models.CharField(max_length=255, blank=True)
    telegram_bot_id = models.CharField(max_length=255, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    bot_token_secret = models.ForeignKey(
        "secrets.SecretRecord", null=True, blank=True, on_delete=models.SET_NULL, related_name="telegram_sources"
    )
    default_domain = models.ForeignKey(Domain, null=True, blank=True, on_delete=models.SET_NULL)
    default_project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL)
    default_agent_profile = models.ForeignKey(
        "agent_profiles.AgentProfile", null=True, blank=True, on_delete=models.SET_NULL, related_name="telegram_sources"
    )
    default_context_pack = models.ForeignKey(
        "context_packs.ContextPack", null=True, blank=True, on_delete=models.SET_NULL, related_name="telegram_sources"
    )
    default_retrieval_mode = models.CharField(max_length=64, choices=RetrievalMode.choices, default=RetrievalMode.BUSINESS)
    retrieval_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    archive_bias = models.DecimalField(max_digits=5, decimal_places=2, default=0.85)
    source_prompt_prefix = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_inbound_enabled = models.BooleanField(default=True)
    is_outbound_enabled = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.display_name


class OutboundDeliveryLog(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(TelegramSource, on_delete=models.CASCADE, related_name="deliveries")
    message = models.ForeignKey("Message", null=True, blank=True, on_delete=models.SET_NULL, related_name="outbound_deliveries")
    target_chat_id = models.BigIntegerField()
    text = models.TextField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    provider_message_id = models.CharField(max_length=255, blank=True)
    error_text = models.TextField(blank=True)


class Message(TimeStampedModel):
    class SenderType(models.TextChoices):
        OWNER = "owner", "Owner"
        AGENT = "agent", "Agent"
        SUBAGENT = "subagent", "Subagent"
        SYSTEM = "system", "System"
        EXTERNAL = "external", "External"

    class ValueTier(models.TextChoices):
        T0_NOISE = "T0_NOISE", "Noise"
        T1_EPHEMERAL = "T1_EPHEMERAL", "Ephemeral"
        T2_PROJECT = "T2_PROJECT", "Project"
        T3_DURABLE = "T3_DURABLE", "Durable"
        T4_CRITICAL = "T4_CRITICAL", "Critical"

    class RagEligibility(models.TextChoices):
        EXCLUDED = "excluded", "Excluded"
        ARCHIVE_ONLY = "archive_only", "Archive Only"
        SUMMARY_ONLY = "summary_only", "Summary Only"
        RETRIEVAL_ALLOWED = "retrieval_allowed", "Retrieval Allowed"
        PRIORITY_RETRIEVAL = "priority_retrieval", "Priority Retrieval"

    class MessageRole(models.TextChoices):
        OWNER_IDEA = "owner_idea", "Owner Idea"
        OWNER_DECISION = "owner_decision", "Owner Decision"
        OWNER_INSTRUCTION = "owner_instruction", "Owner Instruction"
        AGENT_REASONING_TRACE = "agent_reasoning_trace", "Agent Reasoning Trace"
        AGENT_OUTPUT = "agent_output", "Agent Output"
        DEBUG_TRACE = "debug_trace", "Debug Trace"
        TEST_RESULT = "test_result", "Test Result"
        CODE_INSTRUCTION = "code_instruction", "Code Instruction"
        OPS_INSTRUCTION = "ops_instruction", "Ops Instruction"
        GIT_EVENT = "git_event", "Git Event"
        PROMPT_FRAGMENT = "prompt_fragment", "Prompt Fragment"
        TASK_ASSIGNMENT = "task_assignment", "Task Assignment"
        CONTACT_REFERENCE = "contact_reference", "Contact Reference"
        SYSTEM_EVENT = "system_event", "System Event"

    source = models.ForeignKey(TelegramSource, on_delete=models.CASCADE, related_name="messages")
    telegram_chat_id = models.BigIntegerField()
    telegram_message_id = models.BigIntegerField()
    reply_to_message_id = models.BigIntegerField(null=True, blank=True)
    sender_type = models.CharField(max_length=32, choices=SenderType.choices)
    sender_contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.SET_NULL)
    raw_text = models.TextField(blank=True)
    normalized_text = models.TextField(blank=True)
    timestamp = models.DateTimeField()
    domain = models.ForeignKey(Domain, null=True, blank=True, on_delete=models.SET_NULL)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL)
    thread = models.ForeignKey(Thread, null=True, blank=True, on_delete=models.SET_NULL)
    routing_confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    value_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    noise_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    rag_eligibility = models.CharField(max_length=32, choices=RagEligibility.choices, default=RagEligibility.RETRIEVAL_ALLOWED)
    message_value_tier = models.CharField(max_length=32, choices=ValueTier.choices, default=ValueTier.T1_EPHEMERAL)
    message_role = models.CharField(max_length=64, choices=MessageRole.choices, default=MessageRole.OWNER_IDEA)
    sensitivity_level = models.CharField(max_length=32, choices=SensitivityLevel.choices, default=SensitivityLevel.INTERNAL)
    retrieval_mode_default = models.CharField(max_length=64, choices=RetrievalMode.choices, default=RetrievalMode.BUSINESS)
    embedding = EmbeddingField(help_text="Dense embedding for semantic retrieval")
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("source", "telegram_chat_id", "telegram_message_id")]
        indexes = [
            models.Index(fields=["source", "timestamp"]),
            models.Index(fields=["domain", "project", "thread"]),
            models.Index(fields=["message_role", "retrieval_mode_default"]),
            models.Index(fields=["project", "timestamp"]),
            models.Index(fields=["source", "project", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.source.slug}:{self.telegram_message_id}"


class MessageContactLink(TimeStampedModel):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="contact_links")
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="message_links")
    relation_type = models.CharField(max_length=64, blank=True)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)

    class Meta:
        unique_together = [("message", "contact")]
