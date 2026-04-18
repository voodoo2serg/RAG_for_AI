import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from celery import shared_task, chain, group, chord
from celery.exceptions import MaxRetriesExceededError
from django.db import transaction

from apps.archive_ingest.models import ArchiveImportJob
from apps.chat_events.models import Message, TelegramSource
from apps.domains_projects.models import Domain, Project
from apps.threads.models import Thread
from apps.retrieval.services import label_message_role, choose_retrieval_mode
from apps.wiki.services import ensure_domain_wiki, ensure_project_wiki, refresh_project_wiki_from_knowledge
from apps.retrieval.services import upsert_message_corpus_entry

logger = logging.getLogger(__name__)

BATCH_SIZE = 50  # Обрабатываем сообщения пачками по 50


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_message_chunk(self, job_id: int, chunk_start: int, chunk_data: list, source_id: int):
    """Обработка одного чанка сообщений"""
    try:
        job = ArchiveImportJob.objects.get(id=job_id)
        source = TelegramSource.objects.get(id=source_id)
        
        processed = 0
        for item in chunk_data:
            if item.get("type") != "message":
                continue
                
            text = item.get("text", "")
            if isinstance(text, list):
                text = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in text])
            text = (text or "").strip()
            
            if not text:
                continue
                
            date = item.get("date")
            try:
                timestamp = datetime.fromisoformat(date.replace("Z", "+00:00")) if date else datetime.now(timezone.utc)
            except Exception:
                timestamp = datetime.now(timezone.utc)

            # Routing
            domain = source.default_domain or Domain.objects.filter(slug="work").first() or Domain.objects.first()
            project = source.default_project
            lower = text.lower()
            
            if not project and domain:
                for p in Project.objects.filter(domain=domain):
                    if p.canonical_name.lower() in lower or p.slug in lower:
                        project = p
                        break
                if not project:
                    project = Project.objects.filter(domain=domain, parent_project__isnull=True).first()

            thread = None
            if project:
                title = (text[:80] or "Imported thread").strip()
                thread, _ = Thread.objects.get_or_create(
                    project=project,
                    title=title[:80],
                    defaults={"domain": domain, "reconstruction_hint": "import"},
                )

            role = label_message_role(text)
            mode = choose_retrieval_mode(role)

            msg, created = Message.objects.get_or_create(
                source=source,
                telegram_chat_id=1,
                telegram_message_id=int(item.get("id") or 0),
                defaults={
                    "sender_type": Message.SenderType.EXTERNAL,
                    "raw_text": text,
                    "normalized_text": text,
                    "timestamp": timestamp,
                    "domain": domain,
                    "project": project,
                    "thread": thread,
                    "message_role": role,
                    "retrieval_mode_default": mode,
                    "raw_payload": item,
                },
            )
            
            if created:
                upsert_message_corpus_entry(msg)
                processed += 1

        # Update progress
        with transaction.atomic():
            job.processed_messages += processed
            job.save(update_fields=["processed_messages", "updated_at"])
            
        logger.info(f"Job {job_id}: processed chunk {chunk_start}-{chunk_start + len(chunk_data)}, total: {job.processed_messages}")
        return {"job_id": job_id, "chunk_start": chunk_start, "processed": processed}
        
    except Exception as e:
        logger.error(f"Chunk processing failed for job {job_id}, chunk {chunk_start}: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=2)
def finalize_import(self, job_id: int, source_id: int):
    """Финализация импорта — обновление wiki и статуса"""
    try:
        job = ArchiveImportJob.objects.get(id=job_id)
        source = TelegramSource.objects.get(id=source_id)
        
        # Refresh wiki for all affected projects
        projects = set()
        for msg in Message.objects.filter(source=source, created_at__gte=job.created_at):
            if msg.project:
                projects.add(msg.project)
                
        for project in projects:
            refresh_project_wiki_from_knowledge(project)
            
        job.status = "done"
        job.summary = f"Imported {job.processed_messages} messages from {job.source_path}"
        job.save(update_fields=["status", "summary", "updated_at"])
        
        logger.info(f"Import job {job_id} completed: {job.summary}")
        return {"job_id": job_id, "status": "done", "processed": job.processed_messages}
        
    except Exception as e:
        logger.error(f"Finalization failed for job {job_id}: {e}")
        job.status = "failed"
        job.summary = f"Failed: {str(e)}"
        job.save(update_fields=["status", "summary", "updated_at"])
        raise


@shared_task
def process_telegram_import(import_job_id: int):
    """
    Основная задача импорта Telegram экспорта.
    Разбивает файл на чанки и обрабатывает их параллельно.
    """
    try:
        job = ArchiveImportJob.objects.get(id=import_job_id)
        job.status = "parsing"
        job.save(update_fields=["status", "updated_at"])
        
        path = Path(job.source_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
            
        payload = json.loads(path.read_text(encoding="utf-8"))
        messages = [m for m in payload.get("messages", []) if m.get("type") == "message"]
        job.total_messages = len(messages)
        job.status = "processing"
        job.save(update_fields=["total_messages", "status", "updated_at"])
        
        logger.info(f"Import job {import_job_id}: {len(messages)} messages to process")
        
        # Получаем source из пути или используем default
        source = TelegramSource.objects.filter(id=job.meta.get("source_id")).first() if job.meta else None
        if not source:
            source = TelegramSource.objects.first()
        
        if not messages:
            finalize_import.delay(import_job_id, source.id if source else None)
            return
            
        # Разбиваем на чанки
        chunks = []
        for i in range(0, len(messages), BATCH_SIZE):
            chunk = messages[i:i + BATCH_SIZE]
            chunks.append((i, chunk))
            
        # Создаем задачи для каждого чанка
        # Используем chain чтобы обрабатывать последовательно (не перегружать БД)
        # или можно использовать group для параллельной обработки с ограничением
        
        job.status = "chunking"
        job.meta = {**(job.meta or {}), "total_chunks": len(chunks), "source_id": source.id if source else None}
        job.save(update_fields=["status", "meta", "updated_at"])
        
        # Обрабатываем чанки последовательно через цепочку
        # Это предотвращает перегрузку при 18+ файлов
        callback = finalize_import.s(import_job_id, source.id if source else None)
        
        # Создаем цепочку задач
        tasks = []
        for chunk_start, chunk_data in chunks:
            task = process_message_chunk.s(import_job_id, chunk_start, chunk_data, source.id if source else None)
            tasks.append(task)
            
        # Запускаем последовательно через chain
        # Каждый чанк ждет завершения предыдущего
        if tasks:
            chain(*(tasks + [callback])).delay()
        else:
            callback.delay()
            
        logger.info(f"Import job {import_job_id}: queued {len(chunks)} chunks")
        
    except Exception as e:
        logger.error(f"Import processing failed for job {import_job_id}: {e}")
        job = ArchiveImportJob.objects.get(id=import_job_id)
        job.status = "failed"
        job.summary = f"Failed to start: {str(e)}"
        job.save(update_fields=["status", "summary", "updated_at"])
        raise


@shared_task
def cleanup_old_imports(days: int = 7):
    """Очистка старых завершенных импортов"""
    from django.utils import timezone
    cutoff = timezone.now() - timezone.timedelta(days=days)
    
    old_jobs = ArchiveImportJob.objects.filter(
        status__in=["done", "failed"],
        updated_at__lt=cutoff
    )
    count = old_jobs.count()
    old_jobs.delete()
    
    logger.info(f"Cleaned up {count} old import jobs")
    return count