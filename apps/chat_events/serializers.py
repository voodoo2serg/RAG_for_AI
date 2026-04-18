from rest_framework import serializers
from .models import TelegramSource


class TelegramSourceSerializer(serializers.ModelSerializer):
    """Serializer for TelegramSource list"""
    
    class Meta:
        model = TelegramSource
        fields = ['slug', 'display_name', 'source_kind', 'is_active']
