# TKOS Operational Runbook

## Daily Checks (5 min)

1. **Failed jobs** — Check `http://HOST/jobs/` for failed/dead-letter jobs. Requeue or investigate.
2. **Dead-letter queue** — `python manage.py requeue_failed_jobs --max-count 20` if stale.
3. **Approval queue** — Review pending approval requests in `/approvals/`.
4. **Source health** — Check Telegram bot delivery rates in `/sources/`.
5. **Retrieval diagnostics** — `python manage.py corpus_diagnostics` for corpus health snapshot.

## Weekly Checks (15 min)

1. **Verify latest backup** — `python manage.py verify_backup_bundle /path/to/latest.zip`
2. **Test restore** — In staging: `./scripts/restore.sh /path/to/latest.zip`
3. **Archive import failures** — Check for partially imported archives.
4. **Top retrieval failures** — `python manage.py evaluate_retrieval` for quality trend.
5. **Expired grants** — `python manage.py check_secret_expiry` (or run via cron).

## Incident First Response (Ordered)

1. **Freeze** — Block dangerous approvals if secrets/ops actions involved.
2. **Check** — Open dashboard (`/dashboard/`), review failed jobs.
3. **Identify** — Which Telegram sources are impacted?
4. **Preserve** — Export retrieval sessions and logs for root cause analysis.
5. **Restore** — Only after root cause classification. `./scripts/restore.sh <backup>`.

## Rollback Triggers

Any of these trigger an immediate rollback:

- Migration failure during deploy
- Webhook ingestion failure (messages not being stored)
- Outbound delivery collapse (bot not responding)
- Approval flow broken (secrets inaccessible)
- Backup verification regression

## Useful Commands

```bash
python manage.py check                          # Django system check
python manage.py migrate                        # Apply migrations
python manage.py seed_roles                     # Ensure RBAC roles exist
python manage.py create_backup_bundle           # Create backup
python manage.py verify_backup_bundle <path>    # Verify backup
python manage.py requeue_failed_jobs            # Requeue dead-letter jobs
python manage.py run_jobs --max-jobs 100        # Process pending jobs
python manage.py corpus_diagnostics             # Corpus health
python manage.py vector_healthcheck             # pgvector status
```
