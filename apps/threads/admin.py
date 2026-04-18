from django.contrib import admin
from .models import Thread

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "domain", "project", "status", "last_activity_at")
    list_filter = ("domain", "status")
    search_fields = ("title", "reconstruction_hint")
