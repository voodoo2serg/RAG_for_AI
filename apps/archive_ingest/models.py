from django.db import models
from apps.core.models import TimeStampedModel


class ArchiveImportJob(TimeStampedModel):
    """
    Модель для отслеживания импорта Telegram экспорта.
    Поддерживает фоновую обработку через Celery с чанками.
    """
    
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PENDING = "pending", "Pending"
        PARSING = "parsing", "Parsing"
        PROCESSING = "processing", "Processing"
        CHUNKING = "chunking", "Chunking"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    status = models.CharField(
        max_length=32, 
        choices=Status.choices,
        default=Status.QUEUED
    )
    source_path = models.CharField(max_length=512, blank=True)
    total_messages = models.IntegerField(default=0)
    processed_messages = models.IntegerField(default=0)
    imported_artifacts = models.IntegerField(default=0)
    summary = models.TextField(blank=True)
    
    # JSON поле для хранения метаданных:
    # - source_id: ID TelegramSource
    # - total_chunks: всего чанков
    # - current_chunk: текущий обрабатываемый чанк
    # - errors: список ошибок
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "archive_import_jobs"
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"[{self.status}] {self.source_path} ({self.processed_messages}/{self.total_messages})"
    
    @property
    def progress_percent(self):
        """Процент выполнения"""
        if self.total_messages == 0:
            return 0
        return int((self.processed_messages / self.total_messages) * 100)
    
    @property
    def is_done(self):
        return self.status in [self.Status.DONE, self.Status.FAILED]
    
    @property
    def is_running(self):
        return self.status in [
            self.Status.PENDING, 
            self.Status.PARSING, 
            self.Status.PROCESSING, 
            self.Status.CHUNKING
        ]
