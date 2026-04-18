from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = "Checks vector retrieval readiness (PostgreSQL + pgvector)"

    def handle(self, *args, **options):
        engine = settings.DATABASES['default']['ENGINE']
        self.stdout.write(f"DB engine: {engine}")
        self.stdout.write(f"ENABLE_PGVECTOR: {getattr(settings, 'ENABLE_PGVECTOR', False)}")
        if 'postgresql' not in engine:
            self.stdout.write(self.style.WARNING('PostgreSQL not configured; running in fallback mode'))
            return
        with connection.cursor() as cursor:
            cursor.execute("SELECT extname FROM pg_extension WHERE extname='vector'")
            row = cursor.fetchone()
        if row:
            self.stdout.write(self.style.SUCCESS('pgvector extension is installed'))
        else:
            self.stdout.write(self.style.ERROR('pgvector extension is missing'))
