import logging
from celery import shared_task
from apps.retrieval.tasks import generate_message_embedding

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_incoming_message(self, message_id: int, agent_profile_slug: str = None):
    from apps.chat_events.models import Message
    from apps.retrieval.context_assembly import get_context_assembler
    from apps.retrieval.services import log_retrieval_session
    from apps.llm.client import get_llm_client
    from apps.chat_events.telegram_client import get_telegram_client

    try:
        msg = Message.objects.select_related("source", "source__default_agent_profile").get(id=message_id)
    except Message.DoesNotExist:
        logger.error("Message %d not found", message_id)
        return

    generate_message_embedding.delay(message_id)

    effective_agent_slug = agent_profile_slug or (msg.source.default_agent_profile.slug if msg.source.default_agent_profile else None)
    assembler = get_context_assembler()
    context = assembler.assemble(
        query=msg.normalized_text,
        project_id=msg.project_id,
        domain_id=msg.domain_id,
        agent_profile_slug=effective_agent_slug,
        source=msg.source,
    )

    if not context.source_count:
        return None

    llm = get_llm_client()
    if not llm.is_available():
        return None

    system_prompt = context.system_prompt or "You are a helpful assistant."
    response_text, latency_ms = llm.respond_with_rag(
        user_query=msg.normalized_text,
        context_text=context.to_prompt_text()[:6000],
        system_prompt=system_prompt,
    )

    if response_text:
        log_retrieval_session(msg, context, model_name=llm.model, model_output=response_text, latency_ms=latency_ms)
        if msg.source.is_outbound_enabled and msg.telegram_chat_id:
            client = get_telegram_client(msg.source)
            client.send_message(chat_id=msg.telegram_chat_id, text=response_text[:4000], reply_to_message_id=msg.telegram_message_id, message=msg)
        return response_text
    return None
