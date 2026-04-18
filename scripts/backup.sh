#!/usr/bin/env bash
# TKOS RAG Platform — Full Backup Script
# Usage: ./scripts/backup.sh [output_dir]

set -euo pipefail

BACKUP_DIR="${1:-/var/backups/tkos}"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/tkos_backup_${TIMESTAMP}.zip"

mkdir -p "$BACKUP_DIR"

echo "[$(date -u)] Starting backup..."

# Run via Django management command
python manage.py create_backup_bundle --output "$BACKUP_FILE"

echo "[$(date -u)] Backup created: $BACKUP_FILE"
ls -lh "$BACKUP_FILE"
