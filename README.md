# RAG for AI — Telegram Knowledge OS

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Django 5.1](https://img.shields.io/badge/Django-5.1-green.svg)](https://djangoproject.com)
[![PostgreSQL + pgvector](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-blue.svg)](https://postgresql.org)
[![Celery](https://img.shields.io/badge/Celery-5.x-37814A.svg)](https://docs.celeryq.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Telegram-native, project-centric Knowledge OS with transparent RAG for AI chatbot assistants.**

RAG for AI transforms your Telegram conversations into a structured, searchable knowledge base and powers an AI chatbot that answers questions grounded in your actual context — with full provenance tracking for every response.

---

## Overview

RAG for AI is a Django-based system that ingests Telegram messages, classifies them into a hierarchical knowledge structure (Domain > Project > Thread), and provides a Retrieval-Augmented Generation (RAG) pipeline that combines semantic search, keyword matching, and recency scoring to deliver contextually relevant AI responses.

The system is designed around several core principles:

- **Telegram-native**: First-class Telegram integration via webhooks with multi-bot support. Each bot has its own source configuration, domain routing, agent profile, and context pack.
- **Project-centric**: Organize knowledge by domains, projects, and conversation threads. Supports parent/child project relationships and project aliases.
- **Transparent RAG**: Every AI response includes full provenance — which messages, wiki pages, and knowledge items contributed to the answer. Each RetrievalSession stores the complete diagnostic snapshot.
- **Context-aware**: Four retrieval modes (business, debug, ops, historical) automatically selected based on message classification. Each mode applies different ranking weights for optimal relevance.
- **Secret-safe**: Fernet-encrypted secret storage with access audit logging and policy enforcement. Production mode refuses to operate without a configured master key.
- **Extensible**: Agent profiles define bot personas, context packs bundle rules/guidelines/skills/settings, and a pluggable reranker interface allows future ML-based ranking improvements.

---

## Architecture

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | Django 5.1+ | Core application, Admin, Web UI |
| Database | PostgreSQL 16 + pgvector + pg_trgm | Data store, vector search, fuzzy matching |
| Cache/Broker | Redis 7 | Caching, Celery message broker |
| Task Queue | Celery 5 | Async embedding generation, imports, summaries |
| Object Storage | MinIO (S3-compatible) | Attachments, exports, artifacts |
| LLM | OpenAI API (compatible) | Chat completions, embeddings |
| API | Django REST Framework | RESTful API endpoints |
| Containerization | Docker + Docker Compose | Development and production deployment |

### System Layers

The system is organized into 20 Django apps, each responsible for a distinct domain:

```
apps/
  core/              # Base models (TimeStampedModel), enums, middleware, vector field
  accounts/          # User accounts, RBAC (Role, ScopePermission, ApprovalPolicy)
  chat_events/       # Telegram sources, messages, outbound delivery with retry tracking
  domains_projects/  # Domain > Project hierarchy with aliases and relations
  threads/           # Conversation thread reconstruction
  contacts/          # Contact management
  wiki/              # Wiki spaces, pages, revisions (with current_revision tracking)
  context_packs/     # Rules, guidelines, skills, settings (scoped to domain/project/source)
  agent_profiles/    # Bot personas with system prompts and permissions
  knowledge/         # Extracted facts, decisions, heuristics (with embeddings)
  summaries/         # Thread/project/monthly summaries
  retrieval/         # RAG pipeline: search, embeddings, context assembly, reranker,
                     #   diagnostics, evaluation, redaction, review queue
  prompts/           # Prompt templates with versioning
  archive_ingest/    # Telegram JSON export import
  secrets/           # Encrypted secret storage, approval service with expiry/revocation
  artifacts/         # File attachments in MinIO/S3
  jobs/              # Background job queue with retry, idempotency, dead-letter
  webui/             # Web dashboard with RBAC permission mixins
  exports/           # Data export, backup/restore service
  llm/               # LLM client (OpenAI-compatible)
  health/            # Health check endpoints
  api/               # REST API (DRF viewsets + search)
```

### Data Model

The core data model follows a hierarchical structure:

```
Domain (Work, Home, Finance, Health...)
  > Project (with sub-projects, aliases)
       > Thread (reconstructed from conversations by time-gap clustering)
            > Message (15 roles, 5 value tiers, 5 sensitivity levels)

WikiSpace (scoped to domain/project/thread)
  > WikiPage (typed: overview, architecture, decision log, operations...)
       > WikiRevision (with source tracing, current_revision FK)

ContextPack (scoped: global > domain > project > source-default)
  > Rules, Guidelines, Skills, Settings
AgentProfile (persona with system prompt, permissions, autonomy level)
KnowledgeItem (extracted facts, decisions, tasks — with embeddings)
RagCorpusEntry (unified RAG-eligible corpus with trust/freshness/reviewed scoring)
RetrievalSession (full RAG provenance for every LLM response)
RetrievalEvaluationCase/Run/Result (systematic retrieval quality measurement)
ReviewQueueItem (human-in-the-loop outlier review)

--- RBAC & Access Control (P2.1) ---
Role (7 system roles: super_admin, operator, reviewer, analyst, viewer, bot_admin, security_admin)
UserRoleBinding (user-role mapping with audit trail)
ScopePermission (action + resource_type + scope_type for fine-grained access)
ApprovalPolicy (scope-based approval workflows)

--- Job System (P2.1) ---
JobQueue (7 statuses: queued/running/done/failed/retry/dead_letter/cancelled)
  - idempotency_key (dedup), attempt_count, max_attempts
  - last_heartbeat_at, worker_name, trace_id (observability)

--- Delivery Tracking (P2.1) ---
OutboundDeliveryAttempt (per-attempt delivery tracking with rate-limit handling)

--- Backup/Restore (P2.1) ---
Backup bundle: PostgreSQL dump + wiki + context packs + agent profiles + eval data + manifest
```

### RAG Pipeline

The RAG pipeline follows a four-stage process:

```
1. INGEST
   Telegram Message > Normalize > Classify (role, tier, sensitivity)
                   > Route (domain/project/thread) > Store + Embed (async)

2. INDEX
   Embedding Generation (Celery + OpenAI) > Vector Storage (pgvector)
   Full-text Index (PostgreSQL tsvector + pg_trgm)

3. RETRIEVE
   Query > Hybrid Search (semantic 50% + keyword 30% + recency 20%)
        > Multi-signal Scoring (role weight * entry weight * freshness
          * trust * source weight * retrieval weight * storage tier * reviewed)
        > Context Assembly (context packs + wiki + knowledge + corpus snippets)
        > Re-ranking (heuristic reranker with future ML/cross-encoder slot)

4. GENERATE
   Assembled Context + System Prompt > LLM API > Response
   > RetrievalSession logged (full provenance + diagnostics)
   > Response sent to Telegram chat
   > Low-confidence sessions enqueued for human review
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16 with [pgvector](https://github.com/pgvector/pgvector) extension
- Redis 7
- MinIO (or any S3-compatible storage)
- OpenAI API key (or compatible LLM provider)

### Option A: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/<your-username>/RAG_for_AI.git
cd RAG_for_AI

# Copy environment template and configure
cp .env.example .env
# Edit .env — set OPENAI_API_KEY, DJANGO_SECRET_KEY, SECRET_MASTER_KEY, etc.

# Start all services (PostgreSQL + pgvector, Redis, MinIO, Django, Celery)
docker compose up --build -d

# Create admin user
docker compose exec web python manage.py createsuperuser

# Register a Telegram bot source
docker compose exec web python manage.py register_telegram_source my-bot \
    --display-name "My Bot" \
    --kind live_bot \
    --default-domain work

# Import historical messages from Telegram JSON export
docker compose exec web python manage.py import_telegram_export /path/to/result.json

# Reconstruct threads from imported messages
docker compose exec web python manage.py rebuild_threads_and_reason

# Build the unified RAG corpus
docker compose exec web python manage.py reindex_rag_corpus

# Generate embeddings
docker compose exec web python manage.py generate_embeddings
```

Access the application at **http://localhost:8000**

### Option B: Local Development

```bash
# Clone and set up virtual environment
git clone https://github.com/<your-username>/RAG_for_AI.git
cd RAG_for_AI
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# For local dev with SQLite (limited — no vector search):
make install
make migrate
make seed
make dev

# For full PostgreSQL setup:
# 1. Create PostgreSQL database with pgvector extension
# 2. Set DB_ENGINE=django.db.backends.postgresql in .env
# 3. Run: make migrate && make seed

# In a separate terminal, start Celery worker:
make worker
```

---

## Configuration

### Key Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | No | dev | Environment: dev / staging / production |
| `DJANGO_SECRET_KEY` | Yes | - | Django secret key (generate random 50+ chars) |
| `DJANGO_DEBUG` | No | false | Enable debug mode |
| `DB_ENGINE` | No | sqlite3 | Database backend (use postgresql for production) |
| `DB_NAME` | No | tkos | Database name |
| `DB_USER` | No | tkos | Database user |
| `DB_PASSWORD` | No | tkos | Database password |
| `REDIS_URL` | Yes | redis://127.0.0.1:6379/0 | Redis connection URL |
| `TELEGRAM_BOT_TOKEN` | Yes | - | Telegram bot token |
| `TELEGRAM_WEBHOOK_SECRET` | No | - | Webhook secret for verification |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `LLM_MODEL` | No | gpt-4o-mini | LLM model to use |
| `LLM_BASE_URL` | No | - | Custom LLM API endpoint (vLLM, Ollama, etc.) |
| `LLM_MAX_TOKENS` | No | 2048 | Max tokens for LLM responses |
| `EMBEDDING_MODEL` | No | text-embedding-3-small | Embedding model |
| `EMBEDDING_DIMENSION` | No | 1536 | Embedding vector dimension |
| `ENABLE_PGVECTOR` | No | true | Enable pgvector SQL path |
| `SECRET_MASTER_KEY` | Prod only | - | Fernet key for secret encryption |
| `MAX_CONTEXT_CHARS` | No | 30000 | Token budget for LLM context assembly |
| `S3_ENDPOINT_URL` | No | - | MinIO/S3 endpoint |

See `.env.example` for the complete list with comments.

### Telegram Webhook Setup

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com/telegram/webhook/my-bot/", "secret_token": "${TELEGRAM_WEBHOOK_SECRET}"}'
```

---

## API Reference

The REST API is available at `/api/` with token authentication.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/messages/` | List messages (filterable by project, domain, role, date) |
| GET/POST | `/api/knowledge/` | Knowledge items CRUD |
| GET | `/api/wiki/` | Wiki pages with latest content |
| GET | `/api/projects/` | Projects (filterable by domain, status) |
| GET | `/api/domains/` | Domains |
| GET | `/api/retrieval-sessions/` | RAG session history with diagnostics |
| GET | `/api/search/?q=query&project_id=1` | Hybrid search across corpus |
| GET | `/health/` | Liveness check |
| GET | `/health/ready/` | Readiness check (DB + Redis) |
| POST | `/telegram/webhook/{source_slug}/` | Telegram webhook receiver |

---

## Management Commands

### Core Pipeline

| Command | Description |
|---------|-------------|
| `seed_domains` | Create default domains (Work, Home, Finance, etc.) |
| `seed_agent_profiles` | Create default agent profiles |
| `seed_global_context` | Create global context pack with default rules |
| `register_telegram_source <slug>` | Register a Telegram bot source |
| `import_telegram_export <path>` | Import Telegram JSON export |
| `rebuild_threads_and_reason` | Reconstruct threads by time-gap clustering |
| `reindex_rag_corpus` | Build unified RAG corpus from messages/knowledge/wiki |
| `generate_embeddings` | Generate OpenAI embeddings for RAG-eligible content |

### RAG Operations

| Command | Description |
|---------|-------------|
| `label_messages` | (Re-)classify message roles and value tiers |
| `corpus_diagnostics` | Print corpus health statistics |
| `vector_healthcheck` | Verify pgvector extension availability |
| `create_vector_indexes` | Create ANN indexes for pgvector |
| `compact_rag_corpus` | Merge redundant corpus entries |
| `evaluate_retrieval` | Run evaluation suite against search engine |
| `create_source_eval_pack <slug>` | Bootstrap evaluation data per source |
| `build_review_queue` | Populate operator review queue |

### P2.1 Operational Commands

| Command | Description |
|---------|-------------|
| `seed_roles` | Create 7 default RBAC roles with scoped permissions |
| `run_jobs` | Poll and execute pending jobs (loop mode available) |
| `requeue_failed_jobs` | Requeue dead-lettered jobs for retry |
| `create_backup_bundle` | Create full system backup (DB + wiki + packs + profiles) |
| `verify_backup_bundle <path>` | Verify backup bundle integrity |

---

## Security

- **RBAC**: 7 system roles (super_admin, operator, reviewer, analyst, viewer, bot_admin, security_admin) with fine-grained scoped permissions
- **Approval Policies**: Scope-based approval workflows for secrets and sensitive operations
- **Authentication**: All Web UI and API endpoints require authentication (session + token)
- **Rate Limiting**: Telegram webhook is rate-limited (60 req/min per IP)
- **Webhook Verification**: Timing-attack-safe secret comparison via `hmac.compare_digest()`
- **Secret Encryption**: Fernet symmetric encryption (AES-128-CBC) with mandatory production key
- **Access Logging**: All secret accesses are logged with actor, mode, and reason
- **Sensitivity Levels**: Messages classified as PUBLIC / INTERNAL / CONFIDENTIAL / SECRET
- **Redaction**: Regex-based sensitive content detection (API keys, tokens, passwords, SSH keys, GitHub tokens, Slack tokens, Google API keys, etc.)
- **CSRF Protection**: Enabled on all browser-facing views
- **Soft Delete**: Data is never hard-deleted, only marked as `is_deleted`
- **Production Hardening**: HSTS, XSS filter, content-type nosniff, X-Frame DENY, secure cookies
- **Backup/Restore**: Full system backup with integrity verification and documented restore flow
- **Job Resilience**: Idempotency keys, exponential backoff retry, dead-letter queue, heartbeat monitoring
- **Delivery Tracking**: Per-attempt outbound delivery logs with rate-limit backoff handling

---

## Development

### Project Structure

```
RAG_for_AI/
  apps/                  # Django applications (20 apps)
  config/                # Django settings (base/dev/prod), Celery, URLs
  requirements/          # Python dependencies (base/dev/prod)
  scripts/               # Shell scripts (backup.sh, restore.sh, bootstrap_debian.sh)
  deploy/                # Deployment: systemd services, nginx config
  docs/                  # Documentation: deployment, runbook, release checklist
  static/                # Static files (CSS)
  templates/             # Django templates (Web UI)
  tests/                 # E2E smoke tests
  docker-compose.yml     # Full stack: PostgreSQL + Redis + MinIO + Django + Celery
  Dockerfile             # Multi-stage production image (non-root user)
  Makefile               # Common development commands
  manage.py              # Django management script
  .env.example           # Environment template with documentation
```

### Make Targets

```bash
make help          # Show all available commands
make install       # Install Python dependencies
make dev           # Start development server
make migrate       # Run database migrations
make seed          # Run all seed commands
make worker        # Start Celery worker (dev settings)
make worker-beat   # Start Celery beat scheduler (dev settings)
make embeddings    # Generate embeddings
make test          # Run tests
make lint          # Code quality checks
make docker-up     # Start with Docker Compose
make docker-down   # Stop Docker Compose
make superuser     # Create admin user
```

---

## Roadmap

### Completed (P0 - P2.1)

- [x] P0: Core data model with hierarchical knowledge structure
- [x] P0: Telegram webhook with multi-bot source support
- [x] P0: Secret encryption broker with audit logging
- [x] P0: Request ID middleware for observability
- [x] P1: RagCorpusEntry unified corpus model
- [x] P1: Corpus-driven hybrid retrieval (semantic + keyword)
- [x] P1: Thread reconstruction service
- [x] P1.1: Production pgvector integration with EmbeddingField
- [x] P1.1: PostgreSQL + pgvector SQL path with SQLite fallback
- [x] P1.2: Trust/freshness/source/storage/reviewed multi-signal scoring
- [x] P1.2: Retrieval diagnostics UI and CLI
- [x] P1.2: Evaluation suite (Recall@5, MRR)
- [x] P2.0 Prep: Review queue for human-in-the-loop quality control
- [x] P2.0 Prep: Source-specific evaluation packs
- [x] P2.0 Prep: Corpus compaction and lifecycle management
- [x] P2.0 Prep: Reranker abstraction (pluggable)
- [x] P2.0 Prep: Redaction-aware retrieval filtering
- [x] P2.1: RBAC with 7 roles, scoped permissions, approval policies
- [x] P2.1: Job queue with idempotency, retry, dead-letter, heartbeat
- [x] P2.1: Telegram outbound delivery with per-attempt tracking and rate-limit handling
- [x] P2.1: Backup/restore service (DB dump + wiki + context packs + profiles + eval)
- [x] P2.1: Secret approval with expiry, revocation, and audit trail
- [x] P2.1: Production deployment (systemd + nginx + Debian 13 guide)
- [x] P2.1: E2E smoke tests (RBAC, job lifecycle, delivery)
- [x] P2.1: Operational runbook and release checklist
- [x] Security: Timing-safe webhook verification, production hardening headers
- [x] Infrastructure: Multi-stage Dockerfile (non-root), task time limits
- [x] Context assembly: Token budget management with configurable truncation

### Planned (P2.2+)

- [ ] LLM-based knowledge extraction from threads
- [ ] Automatic wiki page generation and updates
- [ ] Automatic summarization (thread/project/monthly)
- [ ] HTMX-powered interactive Web UI
- [ ] Real-time notification via WebSocket
- [ ] Multi-tenant support (organizations)
- [ ] Full-text search in Web UI
- [ ] Wiki editor with markdown preview
- [ ] Retrieval session inspector in Web UI
- [ ] Dashboard with analytics and charts
- [ ] Import from multiple Telegram groups/bots
- [ ] Contact auto-resolution from conversations
- [ ] MinIO file storage integration (attachments)
- [ ] Data export (JSON, CSV, PDF)
- [ ] Cross-encoder / ML-based reranking
- [ ] Comprehensive test suite (>80% coverage)

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure all new code includes appropriate tests and follows the existing code style.
