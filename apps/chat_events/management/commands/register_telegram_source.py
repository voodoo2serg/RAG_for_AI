from django.core.management.base import BaseCommand, CommandError
from apps.chat_events.models import TelegramSource
from apps.domains_projects.models import Domain, Project
from apps.agent_profiles.models import AgentProfile
from apps.context_packs.models import ContextPack


class Command(BaseCommand):
    help = "Register or update a Telegram knowledge source"

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("display_name")
        parser.add_argument("--kind", default="live_bot", choices=["live_bot", "archive_import"])
        parser.add_argument("--bot-username", default="")
        parser.add_argument("--webhook-secret", default="")
        parser.add_argument("--default-domain")
        parser.add_argument("--default-project")
        parser.add_argument("--default-agent-profile")
        parser.add_argument("--default-context-pack")
        parser.add_argument("--outbound", action="store_true")

    def handle(self, *args, **opts):
        domain = Domain.objects.filter(slug=opts.get("default_domain")).first() if opts.get("default_domain") else None
        project = Project.objects.filter(slug=opts.get("default_project")).first() if opts.get("default_project") else None
        profile = AgentProfile.objects.filter(slug=opts.get("default_agent_profile")).first() if opts.get("default_agent_profile") else None
        pack = ContextPack.objects.filter(slug=opts.get("default_context_pack")).first() if opts.get("default_context_pack") else None
        src, created = TelegramSource.objects.update_or_create(
            slug=opts["slug"],
            defaults={
                "display_name": opts["display_name"],
                "source_kind": opts["kind"],
                "bot_username": opts["bot_username"],
                "webhook_secret": opts["webhook_secret"],
                "default_domain": domain,
                "default_project": project,
                "default_agent_profile": profile,
                "default_context_pack": pack,
                "is_outbound_enabled": opts["outbound"],
                "is_active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(("Created" if created else "Updated") + f" source {src.slug}"))
