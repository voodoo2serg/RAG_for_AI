from django.urls import path
from .views import telegram_webhook, telegram_sources_list

urlpatterns = [
    path("webhook/<slug:source_slug>/", telegram_webhook, name="telegram_webhook"),
    path("telegram-sources/", telegram_sources_list, name="telegram_sources_list"),
]
