from django.core.management.base import BaseCommand, CommandParser
from apps.chat_events.models import Message
from apps.retrieval.embeddings import get_embedding_service


class Command(BaseCommand):
    help = "Generate embeddings for all RAG-eligible messages that lack them"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("--project-id", type=int, default=None, help="Limit to a specific project")
        parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
        parser.add_argument("--limit", type=int, default=0, help="Max messages to process (0 = unlimited)")

    def handle(self, *args, **opts):
        svc = get_embedding_service()
        if not svc.is_available():
            self.stderr.write(self.style.ERROR("Embedding service not available. Set OPENAI_API_KEY."))
            return

        qs = Message.objects.filter(
            is_deleted=False,
            rag_eligibility__in=["retrieval_allowed", "priority_retrieval"],
            embedding__isnull=True,
            normalized_text__gt="",
        )
        if opts["project_id"]:
            qs = qs.filter(project_id=opts["project_id"])

        total = qs.count()
        if opts["limit"]:
            total = min(total, opts["limit"])
            qs = qs[:opts["limit"]]

        self.stdout.write(f"Found {total} messages without embeddings")

        count = 0
        for msg in qs:
            embedding = svc.generate(msg.normalized_text)
            if embedding:
                msg.embedding = embedding
                msg.save(update_fields=["embedding", "updated_at"])
                count += 1
                if count % 50 == 0:
                    self.stdout.write(f"  Processed {count}/{total}")
            else:
                self.stderr.write(f"  Failed for message {msg.id}")

        self.stdout.write(self.style.SUCCESS(f"Generated {count}/{total} embeddings"))
