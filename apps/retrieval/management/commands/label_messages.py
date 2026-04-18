from django.core.management.base import BaseCommand
from apps.chat_events.models import Message
from apps.retrieval.services import refresh_message_labels


class Command(BaseCommand):
    help = "Refresh message roles and retrieval modes"

    def handle(self, *args, **kwargs):
        total = 0
        for msg in Message.objects.filter(is_deleted=False):
            refresh_message_labels(msg)
            total += 1
        self.stdout.write(self.style.SUCCESS(f"Relabeled {total} messages"))
