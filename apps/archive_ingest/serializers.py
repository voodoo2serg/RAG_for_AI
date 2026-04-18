from rest_framework import serializers
from apps.archive_ingest.models import ArchiveImportJob


class ArchiveImportJobSerializer(serializers.ModelSerializer):
    """Serializer для отображения задач импорта."""
    progress_percent = serializers.ReadOnlyField()
    is_done = serializers.ReadOnlyField()
    is_running = serializers.ReadOnlyField()
    
    class Meta:
        model = ArchiveImportJob
        fields = [
            'id', 'status', 'source_path', 'total_messages', 
            'processed_messages', 'progress_percent', 'summary',
            'meta', 'is_done', 'is_running',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ArchiveImportJobCreateSerializer(serializers.ModelSerializer):
    """Serializer для создания задачи импорта."""
    
    class Meta:
        model = ArchiveImportJob
        fields = ['source_path', 'meta']


class FileUploadSerializer(serializers.Serializer):
    """Serializer для загрузки файла."""
    file = serializers.FileField()
    source_slug = serializers.CharField(max_length=100)
    
    def validate_file(self, value):
        """Проверка что файл - JSON."""
        if not value.name.endswith('.json'):
            raise serializers.ValidationError("File must be a JSON file (.json)")
        if value.size > 100 * 1024 * 1024:  # 100MB limit
            raise serializers.ValidationError("File too large (max 100MB)")
        return value


class BulkUploadSerializer(serializers.Serializer):
    """Serializer для массовой загрузки файлов."""
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False
    )
    source_slug = serializers.CharField(max_length=100)
    
    def validate_files(self, value):
        """Проверка что все файлы - JSON."""
        for file in value:
            if not file.name.endswith('.json'):
                raise serializers.ValidationError(f"File {file.name} must be a JSON file (.json)")
            if file.size > 100 * 1024 * 1024:  # 100MB limit
                raise serializers.ValidationError(f"File {file.name} too large (max 100MB)")
        return value
