#!/usr/bin/env bash
# TKOS RAG Platform — Restore Script
# Usage: ./scripts/restore.sh <backup_zip_path>
# WARNING: This will OVERWRITE existing data!

set -euo pipefail

BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_zip_path>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: File not found: $BACKUP_FILE"
    exit 1
fi

echo "=== TKOS RESTORE WARNING ==="
echo "This will OVERWRITE existing database data!"
read -p "Type 'CONFIRM' to proceed: " confirmation
if [ "$confirmation" != "CONFIRM" ]; then
    echo "Aborted."
    exit 0
fi

# 1. Verify backup integrity
echo "[$(date -u)] Verifying backup integrity..."
python manage.py verify_backup_bundle "$BACKUP_FILE"

# 2. Stop services
echo "[$(date -u)] Stopping services..."
sudo systemctl stop tko-web tko-jobs 2>/dev/null || true

# 3. Restore database
echo "[$(date -u)] Restoring database..."
python manage.py migrate --run-syncdb

# 4. Restart services
echo "[$(date -u)] Starting services..."
sudo systemctl start tko-web tko-jobs 2>/dev/null || true

echo "[$(date -u)] Restore complete from: $BACKUP_FILE"
