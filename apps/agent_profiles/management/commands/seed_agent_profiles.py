from django.core.management.base import BaseCommand
from apps.agent_profiles.models import AgentProfile

PROFILES = [
    ("Main Assistant", "main-assistant", "Главный агент", "Ты главный агент системы."),
    ("Testing Agent", "testing-agent", "Тестовый агент", "Ты агент тестирования. Не изменяй существующий код."),
    ("Debug Agent", "debug-agent", "Агент дебага", "Ты агент дебага. Ищи причины ошибок."),
    ("Review Agent", "review-agent", "Агент ревью", "Ты агент ревью."),
]

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for name, slug, purpose, prompt in PROFILES:
            AgentProfile.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "purpose": purpose,
                    "human_readable_text": purpose,
                    "system_prompt": prompt,
                }
            )
        self.stdout.write(self.style.SUCCESS("Seeded agent profiles"))
