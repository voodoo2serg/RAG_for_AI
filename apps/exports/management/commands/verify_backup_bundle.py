"""Verify integrity of a backup bundle."""

from django.core.management.base import BaseCommand
from apps.exports.services.backup import verify_backup_bundle


class Command(BaseCommand):
    help = "Verify backup bundle integrity"

    def add_arguments(self, parser):
        parser.add_argument("backup_path", type=str, help="Path to backup zip file")

    def handle(self, *args, **options):
        result = verify_backup_bundle(options["backup_path"])
        if result["valid"]:
            self.stdout.write(self.style.SUCCESS(
                f"Backup valid: {result['path']}\n"
                f"  Files: {len(result['files_found'])}\n"
                f"  SHA256: {result['sha256'][:32]}..."
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"Backup INVALID: {result['path']}\n"
                f"  Errors: {result['errors']}"
            ))
