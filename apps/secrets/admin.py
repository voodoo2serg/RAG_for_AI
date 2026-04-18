from django.contrib import admin
from .models import SecretRecord, SecretAccessLog
admin.site.register(SecretRecord)
admin.site.register(SecretAccessLog)
