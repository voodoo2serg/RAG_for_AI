import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandParser, CommandError
from apps.archive_ingest.models import ArchiveImportJob
from apps.chat_events.models import TelegramSource
from apps.archive_ingest.tasks import process_telegram_import


class Command(BaseCommand):
    help = "Import Telegram JSON export into the system (async via Celery)"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("path", help="Path to Telegram JSON export file")
        parser.add_argument("--source-slug", required=True, help="Telegram source slug")
        parser.add_argument("--sync", action="store_true", help="Process synchronously (not recommended for large files)")
        parser.add_argument("--wait", action="store_true", help="Wait for async job to complete")

    def handle(self, *args, **opts):
        path = Path(opts["path"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        source = TelegramSource.objects.filter(slug=opts["source_slug"]).first()
        if not source:
            raise CommandError(f"Unknown source: {opts['source_slug']}")

        # Проверяем JSON
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            total_messages = len([m for m in payload.get("messages", []) if m.get("type") == "message"])
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e}")
        except Exception as e:
            raise CommandError(f"Failed to parse file: {e}")

        # Создаем job
        job = ArchiveImportJob.objects.create(
            status=ArchiveImportJob.Status.QUEUED,
            source_path=str(path),
            total_messages=total_messages,
            meta={
                "source_id": source.id,
                "filename": path.name,
            }
        )

        self.stdout.write(self.style.SUCCESS(f"Created import job #{job.id}"))
        self.stdout.write(f"  File: {path.name}")
        self.stdout.write(f"  Messages: {total_messages}")
        self.stdout.write(f"  Source: {source.slug}")

        if opts["sync"]:
            # Синхронная обработка (для отладки)
            self.stdout.write(self.style.WARNING("Processing synchronously..."))
            process_telegram_import(job.id)
            job.refresh_from_db()
            self.stdout.write(self.style.SUCCESS(f"Done: {job.summary}"))
        else:
            # Асинхронная обработка через Celery
            task = process_telegram_import.delay(job.id)
            self.stdout.write(self.style.SUCCESS(f"Queued async task: {task.id}"))
            
            if opts["wait"]:
                self.stdout.write("Waiting for completion...")
                import time
                while True:
                    time.sleep(1)
                    job.refresh_from_db()
                    if job.is_done:
                        break
                    self.stdout.write(f"  Progress: {job.progress_percent}% ({job.processed_messages}/{job.total_messages})")
                
                status_color = self.style.SUCCESS if job.status == ArchiveImportJob.Status.DONE else self.style.ERROR
                self.stdout.write(status_color(f"Final status: {job.status}"))
                self.stdout.write(f"Summary: {job.summary}")
