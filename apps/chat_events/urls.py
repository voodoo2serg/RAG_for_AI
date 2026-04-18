from django.urls import path
from .views import telegram_webhook

urlpatterns = [
    path("webhook/<slug:source_slug>/", telegram_webhook, name="telegram_webhook"),
]
