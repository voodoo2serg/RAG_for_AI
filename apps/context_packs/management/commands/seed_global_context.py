from django.core.management.base import BaseCommand
from apps.context_packs.models import ContextPack, ContextRule, ContextGuideline, ContextSetting
from apps.core.enums import ScopeType

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        pack, _ = ContextPack.objects.get_or_create(
            scope_type=ScopeType.GLOBAL,
            scope_id=0,
            slug="global-default",
            defaults={
                "name": "Global Default",
                "description": "Global defaults",
                "human_readable_text": "Глобальные правила и настройки системы.",
                "status": "active",
            },
        )
        ContextRule.objects.get_or_create(
            context_pack=pack,
            title="Provenance required",
            defaults={"rule_type": "must", "body": "Каждый ответ должен быть трассируем до исходных сообщений или summaries.", "priority": 100, "is_active": True},
        )
        ContextGuideline.objects.get_or_create(
            context_pack=pack,
            title="Prefer simple architecture",
            defaults={"body": "Предпочитать простые монолитные решения и не плодить базовые системы.", "confidence": 1.0, "is_active": True},
        )
        ContextSetting.objects.get_or_create(
            context_pack=pack,
            key="retrieval_transparency_required",
            defaults={"value_json": True, "value_type": "bool", "is_active": True},
        )
        self.stdout.write(self.style.SUCCESS("Seeded global context"))
