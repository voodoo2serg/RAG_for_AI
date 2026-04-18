import logging
from pathlib import Path
from django.conf import settings
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend

from apps.archive_ingest.models import ArchiveImportJob
from apps.archive_ingest.serializers import (
    ArchiveImportJobSerializer, 
    ArchiveImportJobCreateSerializer,
    FileUploadSerializer,
    BulkUploadSerializer
)
from apps.archive_ingest.tasks import process_telegram_import
from apps.chat_events.models import TelegramSource
from django.utils import timezone

logger = logging.getLogger(__name__)


class ArchiveImportJobViewSet(viewsets.ModelViewSet):
    """
    API для управления импортом Telegram экспортов.
    
    Supports:
    - GET /api/import-jobs/ — список задач импорта
    - POST /api/import-jobs/ — создать задачу из JSON
    - POST /api/import-jobs/upload/ — загрузить файл и создать задачу
    - GET /api/import-jobs/{id}/progress/ — получить прогресс
    """
    queryset = ArchiveImportJob.objects.all()
    serializer_class = ArchiveImportJobSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'source_path']
    parser_classes = [JSONParser, MultiPartParser]

    def get_serializer_class(self):
        if self.action == 'create':
            return ArchiveImportJobCreateSerializer
        return ArchiveImportJobSerializer

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def upload(self, request):
        """
        Загрузить Telegram JSON файл и создать задачу импорта.
        
        Request:
            file: Telegram JSON export file
            source_slug: Telegram source slug
        
        Response:
            job_id: ID созданной задачи
            status: queued
            messages_count: количество сообщений в файле
        """
        serializer = FileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uploaded_file = serializer.validated_data['file']
        source_slug = serializer.validated_data['source_slug']
        
        # Проверяем source
        source = TelegramSource.objects.filter(slug=source_slug).first()
        if not source:
            return Response(
                {'error': f'Unknown source: {source_slug}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Сохраняем файл
        upload_dir = Path(settings.MEDIA_ROOT) / 'uploads' / 'telegram_exports'
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{uploaded_file.name}"
        file_path = upload_dir / filename
        
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Парсим JSON для подсчета сообщений
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            messages = [m for m in payload.get('messages', []) if m.get('type') == 'message']
            total_messages = len(messages)
        except json.JSONDecodeError as e:
            file_path.unlink()
            return Response(
                {'error': f'Invalid JSON file: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            file_path.unlink()
            return Response(
                {'error': f'Failed to parse file: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Создаем задачу импорта
        with transaction.atomic():
            job = ArchiveImportJob.objects.create(
                status=ArchiveImportJob.Status.QUEUED,
                source_path=str(file_path),
                total_messages=total_messages,
                meta={
                    'source_id': source.id,
                    'filename': uploaded_file.name,
                    'uploaded_by': request.user.id if request.user.is_authenticated else None,
                }
            )
        
        # Запускаем асинхронную обработку
        task = process_telegram_import.delay(job.id)
        
        logger.info(f"Created import job #{job.id} for file {uploaded_file.name} ({total_messages} messages)")
        
        return Response({
            'job_id': job.id,
            'status': job.status,
            'task_id': task.id,
            'filename': uploaded_file.name,
            'messages_count': total_messages,
            'progress_percent': 0,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """
        Получить прогресс импорта.
        
        Response:
            job_id: ID задачи
            status: текущий статус
            progress_percent: процент выполнения
            processed: обработано сообщений
            total: всего сообщений
            summary: описание/результат
        """
        job = self.get_object()
        return Response({
            'job_id': job.id,
            'status': job.status,
            'progress_percent': job.progress_percent,
            'processed': job.processed_messages,
            'total': job.total_messages,
            'summary': job.summary,
            'meta': job.meta,
            'created_at': job.created_at,
            'updated_at': job.updated_at,
        })

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Повторить failed задачу импорта."""
        job = self.get_object()
        
        if job.status != ArchiveImportJob.Status.FAILED:
            return Response(
                {'error': 'Only failed jobs can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Сбрасываем статус
        job.status = ArchiveImportJob.Status.QUEUED
        job.processed_messages = 0
        job.summary = ''
        job.save(update_fields=['status', 'processed_messages', 'summary', 'updated_at'])
        
        # Перезапускаем
        task = process_telegram_import.delay(job.id)
        
        return Response({
            'job_id': job.id,
            'status': job.status,
            'task_id': task.id,
        })

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def bulk_upload(self, request):
        """
        Массовая загрузка нескольких Telegram JSON файлов.
        
        Request:
            files: список файлов (multipart/form-data, multiple files with same key 'files')
            source_slug: Telegram source slug
        
        Response:
            batch_id: ID батча
            jobs: список созданных задач [{job_id, filename, messages_count, status}]
            total_files: количество файлов
            total_messages: общее количество сообщений
        """
        serializer = BulkUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        files = serializer.validated_data['files']
        source_slug = serializer.validated_data['source_slug']
        
        # Проверяем source
        source = TelegramSource.objects.filter(slug=source_slug).first()
        if not source:
            return Response(
                {'error': f'Unknown source: {source_slug}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        upload_dir = Path(settings.MEDIA_ROOT) / 'uploads' / 'telegram_exports'
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        batch_id = timezone.now().strftime('%Y%m%d_%H%M%S_%f')
        jobs = []
        total_messages = 0
        
        for uploaded_file in files:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"{timestamp}_{uploaded_file.name}"
            file_path = upload_dir / filename
            
            try:
                # Сохраняем файл
                with open(file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                
                # Парсим JSON
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                messages = [m for m in payload.get('messages', []) if m.get('type') == 'message']
                file_messages = len(messages)
                total_messages += file_messages
                
                # Создаем задачу
                with transaction.atomic():
                    job = ArchiveImportJob.objects.create(
                        status=ArchiveImportJob.Status.QUEUED,
                        source_path=str(file_path),
                        total_messages=file_messages,
                        meta={
                            'source_id': source.id,
                            'filename': uploaded_file.name,
                            'batch_id': batch_id,
                            'uploaded_by': request.user.id if request.user.is_authenticated else None,
                        }
                    )
                
                # Запускаем обработку
                task = process_telegram_import.delay(job.id)
                
                jobs.append({
                    'job_id': job.id,
                    'filename': uploaded_file.name,
                    'messages_count': file_messages,
                    'status': job.status,
                    'task_id': task.id,
                })
                
            except json.JSONDecodeError as e:
                file_path.unlink() if file_path.exists() else None
                jobs.append({
                    'filename': uploaded_file.name,
                    'error': f'Invalid JSON: {str(e)}',
                    'status': 'error',
                })
            except Exception as e:
                file_path.unlink() if file_path.exists() else None
                jobs.append({
                    'filename': uploaded_file.name,
                    'error': str(e),
                    'status': 'error',
                })
        
        logger.info(f"Bulk upload batch {batch_id}: {len([j for j in jobs if 'job_id' in j])} files, {total_messages} messages")
        
        return Response({
            'batch_id': batch_id,
            'jobs': jobs,
            'total_files': len(files),
            'successful': len([j for j in jobs if 'job_id' in j]),
            'failed': len([j for j in jobs if 'error' in j]),
            'total_messages': total_messages,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def batch_status(self, request):
        """
        Получить статус батча загрузки.
        
        Query params:
            batch_id: ID батча
        
        Response:
            batch_id: ID батча
            total: всего задач
            completed: завершено
            processing: в обработке
            failed: с ошибками
            jobs: детали по каждой задаче
        """
        batch_id = request.query_params.get('batch_id')
        if not batch_id:
            return Response(
                {'error': 'batch_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        jobs = ArchiveImportJob.objects.filter(meta__batch_id=batch_id)
        
        result = {
            'batch_id': batch_id,
            'total': jobs.count(),
            'completed': jobs.filter(status=ArchiveImportJob.Status.DONE).count(),
            'processing': jobs.filter(
                status__in=[
                    ArchiveImportJob.Status.QUEUED,
                    ArchiveImportJob.Status.PENDING,
                    ArchiveImportJob.Status.PARSING,
                    ArchiveImportJob.Status.PROCESSING,
                    ArchiveImportJob.Status.CHUNKING,
                ]
            ).count(),
            'failed': jobs.filter(status=ArchiveImportJob.Status.FAILED).count(),
            'overall_progress': 0,
            'jobs': [],
        }
        
        total_messages = 0
        processed_messages = 0
        
        for job in jobs:
            result['jobs'].append({
                'job_id': job.id,
                'filename': job.meta.get('filename', 'unknown'),
                'status': job.status,
                'progress_percent': job.progress_percent,
                'processed': job.processed_messages,
                'total': job.total_messages,
            })
            total_messages += job.total_messages
            processed_messages += job.processed_messages
        
        if total_messages > 0:
            result['overall_progress'] = int((processed_messages / total_messages) * 100)
        
        return Response(result)
        """
        Получить статус очереди импорта.
        
        Response:
            queued: количество задач в очереди
            processing: количество обрабатываемых
            done: количество завершенных
            failed: количество с ошибками
        """
        stats = {
            'queued': ArchiveImportJob.objects.filter(status=ArchiveImportJob.Status.QUEUED).count(),
            'processing': ArchiveImportJob.objects.filter(
                status__in=[
                    ArchiveImportJob.Status.PENDING,
                    ArchiveImportJob.Status.PARSING,
                    ArchiveImportJob.Status.PROCESSING,
                    ArchiveImportJob.Status.CHUNKING,
                ]
            ).count(),
            'done': ArchiveImportJob.objects.filter(status=ArchiveImportJob.Status.DONE).count(),
            'failed': ArchiveImportJob.objects.filter(status=ArchiveImportJob.Status.FAILED).count(),
        }
        return Response(stats)
