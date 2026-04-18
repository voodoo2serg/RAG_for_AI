import json
from pathlib import Path
from datetime import datetime, timezone
from django.core.management.base import BaseCommand, CommandParser, CommandError
from apps.archive_ingest.models import ArchiveImportJob
from apps.chat_events.models import Message, TelegramSource
from apps.domains_projects.models import Domain, Project
from apps.threads.models import Thread
from apps.retrieval.services import label_message_role, choose_retrieval_mode
from apps.wiki.services import ensure_domain_wiki, ensure_project_wiki, refresh_project_wiki_from_knowledge
from apps.retrieval.services import upsert_message_corpus_entry

def slugify_basic(text: str) -> str:
    return (
        text.lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("_", "-")
    )

class Command(BaseCommand):
    help = "Import Telegram JSON export into the system"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("path")
        parser.add_argument("--source-slug", required=True)

    def handle(self, *args, **opts):
        path = Path(opts["path"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        source = TelegramSource.objects.filter(slug=opts["source_slug"]).first()
        if not source:
            raise CommandError(f"Unknown source: {opts['source_slug']}")

        payload = json.loads(path.read_text(encoding="utf-8"))
        messages = payload.get("messages", [])
        job = ArchiveImportJob.objects.create(status="running", source_path=str(path), total_messages=len(messages))

        for item in messages:
            if item.get("type") != "message":
                continue
            text = item.get("text", "")
            if isinstance(text, list):
                text = "".join([part.get("text", "") if isinstance(part, dict) else str(part) for part in text])
            text = (text or "").strip()
            date = item.get("date")
            try:
                timestamp = datetime.fromisoformat(date.replace("Z", "+00:00")) if date else datetime.now(timezone.utc)
            except Exception:
                timestamp = datetime.now(timezone.utc)

            # simple routing
            domain = source.default_domain or Domain.objects.filter(slug="work").first() or Domain.objects.first()
            project = source.default_project
            lower = text.lower()
            for p in Project.objects.filter(domain=domain):
                if p.canonical_name.lower() in lower or p.slug in lower:
                    project = p
                    break

            if not project and domain:
                project = Project.objects.filter(domain=domain, parent_project__isnull=True).first()

            title = (text[:80] or "Imported thread").strip()
            thread = None
            if project:
                thread, _ = Thread.objects.get_or_create(
                    project=project,
                    title=title[:80],
                    defaults={"domain": domain, "reconstruction_hint": "import"},
                )
                ensure_project_wiki(project)
            if domain:
                ensure_domain_wiki(domain)

            role = label_message_role(text)
            mode = choose_retrieval_mode(role)

            msg, _ = Message.objects.get_or_create(
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
            upsert_message_corpus_entry(msg)
            if project:
                refresh_project_wiki_from_knowledge(project)
            job.processed_messages += 1

        job.status = "done"
        job.summary = f"Imported {job.processed_messages} messages from {path.name}"
        job.save(update_fields=["status", "processed_messages", "summary", "updated_at"])
        self.stdout.write(self.style.SUCCESS(job.summary))
