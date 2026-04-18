import logging
from celery import shared_task
from apps.chat_events.models import Message
from apps.retrieval.embeddings import get_embedding_service
from apps.retrieval.services import upsert_message_corpus_entry

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_message_embedding(self, message_id: int):
    try:
        msg = Message.objects.get(id=message_id, is_deleted=False)
        svc = get_embedding_service()
        if not svc.is_available() or not msg.normalized_text.strip():
            return
        embedding = svc.generate(msg.normalized_text)
        if embedding:
            msg.embedding = embedding
            msg.save(update_fields=["embedding", "updated_at"])
            upsert_message_corpus_entry(msg)
            logger.info("Generated embedding for message %d", message_id)
    except Exception as e:
        logger.error("Embedding generation failed for message %d: %s", message_id, e)
        raise self.retry(exc=e)


@shared_task(bind=True)
def batch_generate_embeddings(self, project_id: int = None, batch_size: int = 100):
    qs = Message.objects.filter(
        is_deleted=False,
        rag_eligibility__in=["retrieval_allowed", "priority_retrieval"],
        embedding__isnull=True,
        normalized_text__gt="",
    )
    if project_id:
        qs = qs.filter(project_id=project_id)

    total = qs.count()
    logger.info("Batch embedding: %d messages to process", total)

    for i in range(0, total, batch_size):
        batch = list(qs[i:i + batch_size])
        for msg in batch:
            generate_message_embedding.delay(msg.id)

    logger.info("Batch embedding: queued %d tasks", total)
