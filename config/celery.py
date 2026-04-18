import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.dev"))

app = Celery("tkos")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Default task limits for safety
app.conf.task_soft_time_limit = 300
app.conf.task_time_limit = 360
