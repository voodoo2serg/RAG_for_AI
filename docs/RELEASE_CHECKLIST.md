# TKOS Release Checklist (P2.1)

## Before Release

- [ ] `python manage.py check` passes cleanly
- [ ] All migrations apply without error
- [ ] `python manage.py seed_roles` succeeds
- [ ] `python manage.py seed_domains` succeeds
- [ ] `python manage.py seed_agent_profiles` succeeds
- [ ] `python manage.py seed_global_context` succeeds
- [ ] Backup bundle created and verified
- [ ] Dead-letter queue empty or all items acknowledged
- [ ] Source delivery test executed for each active bot
- [ ] Approval expiry check tested
- [ ] Smoke tests pass (`python manage.py test tests/`)

## Release Day

- [ ] Full database backup taken before deploy
- [ ] Deployment environment variables verified
- [ ] Healthcheck passes after deploy: `GET /health/ready/`
- [ ] Dashboard reviewed: `/dashboard/`
- [ ] Operator team notified

## Rollback Triggers

If any of these occur, rollback immediately:

1. Migration failure
2. Webhook ingestion failure (messages not stored)
3. Outbound delivery collapse
4. Approval flow broken
5. Backup verification regression
