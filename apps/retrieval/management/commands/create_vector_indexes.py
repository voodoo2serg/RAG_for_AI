from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Create pgvector ANN indexes for retrieval corpus when running on PostgreSQL."

    def handle(self, *args, **options):
        engine = settings.DATABASES["default"]["ENGINE"]
        if "postgresql" not in engine:
            self.stdout.write("Skipping: non-PostgreSQL database")
            return
        sql = """
        CREATE INDEX IF NOT EXISTS retrieval_ragcorpusentry_embedding_ivfflat
        ON retrieval_ragcorpusentry USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """
        with connection.cursor() as cur:
            cur.execute(sql)
        self.stdout.write(self.style.SUCCESS("Vector index ensured"))
