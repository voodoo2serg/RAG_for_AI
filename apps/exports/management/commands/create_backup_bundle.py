"""Create a backup bundle of the entire system."""

from django.core.management.base import BaseCommand
from apps.exports.services.backup import create_backup_bundle
import json


class Command(BaseCommand):
    help = "Create a backup bundle (DB dump + wiki + context packs + profiles + eval data)"

    def add_arguments(self, parser):
        parser.add_argument("--output", type=str, default=None, help="Output zip file path")

    def handle(self, *args, **options):
        self.stdout.write("Creating backup bundle...")
        metadata = create_backup_bundle(output_path=options.get("output"))
        self.stdout.write(self.style.SUCCESS(
            f"Backup created: {metadata['bundle_path']}\n"
            f"  Size: {metadata['bundle_size_bytes']} bytes\n"
            f"  Files: {len(metadata['files'])}\n"
            f"  SHA256: {metadata['bundle_sha256'][:32]}..."
        ))
