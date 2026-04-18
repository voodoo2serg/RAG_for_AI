from django.db import models
from apps.core.models import TimeStampedModel
from apps.core.vector import EmbeddingField
from apps.domains_projects.models import Domain, Project
from apps.threads.models import Thread

class KnowledgeItem(TimeStampedModel):
    class KnowledgeType(models.TextChoices):
        FACT = "fact", "Fact"
        DECISION = "decision", "Decision"
        TASK = "task", "Task"
        RULE = "rule", "Rule"
        HEURISTIC = "heuristic", "Heuristic"
        HYPOTHESIS = "hypothesis", "Hypothesis"
        PROMPT = "prompt", "Prompt"
        LESSON = "lesson", "Lesson"

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL)
    thread = models.ForeignKey(Thread, null=True, blank=True, on_delete=models.SET_NULL)
    knowledge_type = models.CharField(max_length=32, choices=KnowledgeType.choices)
    title = models.CharField(max_length=255)
    body = models.TextField()
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0.5)
    status = models.CharField(max_length=32, default="candidate")
    source_message_ids = models.JSONField(default=list, blank=True)
    embedding = EmbeddingField(help_text="Dense embedding for semantic retrieval")

    class Meta:
        indexes = [
            models.Index(fields=["domain", "project"]),
            models.Index(fields=["knowledge_type", "status"]),
        ]

    def __str__(self):
        return self.title
