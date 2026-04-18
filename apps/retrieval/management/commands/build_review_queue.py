
from django.core.management.base import BaseCommand
from apps.retrieval.models import RetrievalSession, ReviewQueueItem

class Command(BaseCommand):
    help = "Create review queue items from low-confidence retrieval sessions"

    def handle(self, *args, **kwargs):
        created = 0
        open_ids = set(ReviewQueueItem.objects.filter(queue_type=ReviewQueueItem.QueueType.RETRIEVAL_OUTLIER, status=ReviewQueueItem.Status.OPEN).values_list("payload", flat=True))
        for session in RetrievalSession.objects.filter(relevance_score__lt=0.20)[:200]:
            ReviewQueueItem.objects.create(
                queue_type=ReviewQueueItem.QueueType.RETRIEVAL_OUTLIER,
                title=f"Review retrieval session #{session.id}",
                payload={"session_id": session.id, "reason": "low_relevance"},
                priority=30,
                source=session.user_message.source if getattr(session.user_message, "source_id", None) else None,
                project=session.user_message.project,
                domain=session.user_message.domain,
            )
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Created {created} review queue items"))
