from django.core.management.base import BaseCommand
from apps.domains_projects.models import Domain
from apps.wiki.services import ensure_domain_wiki

DOMAINS = [
    ("Дом", "home"),
    ("Работа", "work"),
    ("Финансы", "finance"),
    ("Здоровье", "health"),
    ("Семья", "family"),
    ("Исследования", "research"),
    ("Контент", "content"),
    ("Прочее", "misc"),
]

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for idx, (name, slug) in enumerate(DOMAINS, start=1):
            domain, _ = Domain.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "display_order": idx}
            )
            ensure_domain_wiki(domain)
        self.stdout.write(self.style.SUCCESS("Seeded domains"))
