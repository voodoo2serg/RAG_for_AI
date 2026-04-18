import logging
import re
from typing import Iterable

from apps.chat_events.models import Message
from apps.core.enums import RetrievalMode
from apps.retrieval.context_assembly import get_context_assembler
from apps.retrieval.models import RetrievalSession, RagCorpusEntry, ReviewQueueItem
from apps.summaries.models import Summary
from apps.knowledge.models import KnowledgeItem
from apps.wiki.models import WikiPage
from apps.retrieval.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


def label_message_role(text: str, sender_type: str = "external") -> str:
    lower = (text or "").lower()
    if any(kw in lower for kw in ["traceback", "stack trace", "debug", "ошибка", "exception"]):
        return Message.MessageRole.DEBUG_TRACE
    if any(kw in lower for kw in ["тест", "test result", "passed", "failed", "pytest"]):
        return Message.MessageRole.TEST_RESULT
    if any(kw in lower for kw in ["git", "commit", "push", "pull request", "merge request"]):
        return Message.MessageRole.GIT_EVENT
    if any(kw in lower for kw in ["сервер", "deploy", "docker", "nginx", "ssh", "prod"]):
        return Message.MessageRole.OPS_INSTRUCTION
    if any(kw in lower for kw in ["prompt", "system prompt", "инструкция модели"]):
        return Message.MessageRole.PROMPT_FRAGMENT
    if any(kw in lower for kw in ["попроси", "сделай", "надо", "задача", "поручение"]):
        return Message.MessageRole.OWNER_INSTRUCTION
    if any(kw in lower for kw in ["решили", "решение", "фиксируем", "утверждаем"]):
        return Message.MessageRole.OWNER_DECISION
    return Message.MessageRole.OWNER_IDEA


def choose_retrieval_mode(role: str) -> str:
    if role in {Message.MessageRole.DEBUG_TRACE, Message.MessageRole.TEST_RESULT, Message.MessageRole.AGENT_REASONING_TRACE}:
        return RetrievalMode.DEBUG
    if role in {Message.MessageRole.OPS_INSTRUCTION, Message.MessageRole.GIT_EVENT}:
        return RetrievalMode.OPS
    return RetrievalMode.BUSINESS


def full_rag_retrieve(message: Message, agent_profile_slug: str | None = None):
    assembler = get_context_assembler()
    return assembler.assemble(
        query=message.normalized_text,
        project_id=message.project_id,
        domain_id=message.domain_id,
        agent_profile_slug=agent_profile_slug,
        source=message.source,
    )


def log_retrieval_session(message, context, model_name: str, model_output: str, latency_ms: int = 0):
    source_slug = getattr(getattr(message, "source", None), "slug", "unknown")
    RetrievalSession.objects.create(
        user_message=message,
        query_text=message.normalized_text,
        routing_snapshot={
            "source": source_slug,
            "project_id": message.project_id,
            "domain_id": message.domain_id,
            "thread_id": message.thread_id,
            "retrieval_mode": context.retrieval_mode,
        },
        selected_corpus_entry_ids=context.selected_corpus_entry_ids,
        applied_context_pack_ids=context.applied_context_pack_ids,
        final_prompt_text=context.to_prompt_text()[:12000],
        model_name=model_name,
        model_output=model_output[:12000],
        latency_ms=latency_ms,
        runtime_snapshot={
            "source_slug": context.source_slug,
            "retrieval_mode": context.retrieval_mode,
            "source_count": context.source_count,
        },
        diagnostics_snapshot=getattr(context, 'diagnostics', {}),
    )


def refresh_message_labels(message: Message):
    message.message_role = label_message_role(message.normalized_text, message.sender_type)
    message.retrieval_mode_default = choose_retrieval_mode(message.message_role)
    if len((message.normalized_text or '').strip()) > 500:
        message.message_value_tier = Message.ValueTier.T3_DURABLE
    elif any(tok in (message.normalized_text or '').lower() for tok in ['решение', 'архитектура', 'strategy', 'design']):
        message.message_value_tier = Message.ValueTier.T4_CRITICAL
    message.save(update_fields=['message_role', 'retrieval_mode_default', 'message_value_tier', 'updated_at'])
    return message


def _entry_text_title_for_message(message: Message):
    title = re.sub(r'\s+', ' ', (message.normalized_text or '').strip())[:120]
    return title, (message.normalized_text or '')


def upsert_message_corpus_entry(message: Message):
    title, text = _entry_text_title_for_message(message)
    entry, _ = RagCorpusEntry.objects.update_or_create(
        source_object_type=RagCorpusEntry.SourceObjectType.MESSAGE,
        source_object_id=message.id,
        defaults={
            'entry_type': RagCorpusEntry.EntryType.MESSAGE,
            'source': message.source,
            'domain': message.domain,
            'project': message.project,
            'thread': message.thread,
            'text': text[:4000],
            'title': title,
            'message_role': message.message_role,
            'retrieval_mode': message.retrieval_mode_default,
            'sensitivity_level': message.sensitivity_level,
            'trust_score': 0.80 if message.sender_type == Message.SenderType.OWNER else 0.65,
            'freshness_score': 0.90,
            'source_weight': getattr(message.source, 'retrieval_weight', 1.00),
            'retrieval_weight': 1.15 if message.message_value_tier == Message.ValueTier.T4_CRITICAL else 1.00,
            'metadata': {
                'source_slug': message.source.slug,
                'message_value_tier': message.message_value_tier,
                'telegram_message_id': message.telegram_message_id,
            },
            'embedding': message.embedding or [],
        }
    )
    return entry


def upsert_summary_corpus_entry(summary: Summary):
    entry, _ = RagCorpusEntry.objects.update_or_create(
        source_object_type=RagCorpusEntry.SourceObjectType.SUMMARY,
        source_object_id=summary.id,
        defaults={
            'entry_type': RagCorpusEntry.EntryType.SUMMARY,
            'domain': summary.domain,
            'project': summary.project,
            'thread': summary.thread,
            'text': summary.summary_text[:4000],
            'title': f'{summary.summary_level} summary',
            'retrieval_mode': RetrievalMode.BUSINESS,
            'trust_score': 0.95,
            'freshness_score': 0.85,
            'source_weight': 1.00,
            'retrieval_weight': 1.10,
            'metadata': {'summary_level': summary.summary_level, 'version': summary.version},
        }
    )
    return entry


def upsert_knowledge_corpus_entry(item: KnowledgeItem):
    entry, _ = RagCorpusEntry.objects.update_or_create(
        source_object_type=RagCorpusEntry.SourceObjectType.KNOWLEDGE,
        source_object_id=item.id,
        defaults={
            'entry_type': RagCorpusEntry.EntryType.KNOWLEDGE,
            'domain': item.domain,
            'project': item.project,
            'thread': item.thread,
            'text': item.body[:4000],
            'title': item.title[:255],
            'retrieval_mode': RetrievalMode.BUSINESS,
            'message_role': item.knowledge_type,
            'trust_score': float(item.confidence or 0.5),
            'freshness_score': 0.75,
            'source_weight': 1.00,
            'retrieval_weight': 1.20 if item.status == 'accepted' else 0.95,
            'metadata': {'knowledge_type': item.knowledge_type, 'status': item.status},
            'embedding': item.embedding or [],
        }
    )
    return entry


def upsert_wiki_corpus_entry(page: WikiPage):
    rev = page.revisions.order_by('-created_at').first()
    if not rev:
        return None
    text = rev.content_text or ''
    entry, _ = RagCorpusEntry.objects.update_or_create(
        source_object_type=RagCorpusEntry.SourceObjectType.WIKI_PAGE,
        source_object_id=page.id,
        defaults={
            'entry_type': RagCorpusEntry.EntryType.WIKI,
            'text': text[:4000],
            'title': page.title[:255],
            'retrieval_mode': RetrievalMode.BUSINESS,
            'trust_score': 0.90,
            'freshness_score': 0.80,
            'source_weight': 1.00,
            'retrieval_weight': 1.05,
            'metadata': {'page_type': page.page_type, 'wiki_space_id': page.wiki_space_id},
        }
    )
    return entry


def rebuild_rag_corpus():
    count = 0
    for msg in Message.objects.filter(is_deleted=False).iterator(chunk_size=500):
        refresh_message_labels(msg)
        upsert_message_corpus_entry(msg)
        count += 1
    for summary in Summary.objects.filter(is_deleted=False).iterator(chunk_size=500):
        upsert_summary_corpus_entry(summary)
        count += 1
    for item in KnowledgeItem.objects.filter(is_deleted=False).iterator(chunk_size=500):
        upsert_knowledge_corpus_entry(item)
        count += 1
    for page in WikiPage.objects.filter(is_deleted=False, is_active=True).iterator(chunk_size=200):
        upsert_wiki_corpus_entry(page)
        count += 1
    return count


def enqueue_retrieval_outlier(session: RetrievalSession, threshold: float = 0.15):
    score = float(session.relevance_score or 0)
    if score <= threshold:
        ReviewQueueItem.objects.create(
            queue_type=ReviewQueueItem.QueueType.RETRIEVAL_OUTLIER,
            title=f"Low-confidence retrieval session #{session.id}",
            payload={"session_id": session.id, "score": score},
            priority=20,
            source=session.user_message.source if getattr(session.user_message, "source_id", None) else None,
            project=session.user_message.project,
            domain=session.user_message.domain,
        )
