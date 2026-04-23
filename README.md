# RAG for AI — Telegram Knowledge OS

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Django 5.1](https://img.shields.io/badge/Django-5.1-green.svg)](https://djangoproject.com)
[![PostgreSQL + pgvector](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-blue.svg)](https://postgresql.org)
[![Celery](https://img.shields.io/badge/Celery-5.x-37814A.svg)](https://docs.celeryq.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Telegram-native, project-centric Knowledge OS with transparent RAG for AI chatbot assistants.**

RAG for AI transforms your Telegram conversations into a structured, searchable knowledge base and powers an AI chatbot that answers questions grounded in your actual context — with full provenance tracking for every response.

---

## 🚀 Production Hardening (v2.2)

### Security Fixes
- ✅ **HTTPS enforcement** — `SECURE_SSL_REDIRECT`, HSTS, secure cookies
- ✅ **CORS whitelist** — strict origin validation (no `ALLOW_ALL`)
- ✅ **Session security** — `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`

### LLM Resilience
- ✅ **Retry with exponential backoff** — tenacity integration
- ✅ **Circuit breaker** — pybreaker for fault isolation
- ✅ **Fallback provider** — secondary LLM endpoint
- ✅ **Graceful degradation** — cached responses, fallback messages
- ✅ **Request timeout** — 30s default, configurable

### Testing
- ✅ **60+ tests** across 8 test modules:
  - `test_retrieval.py` — RAG pipeline (search, context assembly, reranker)
  - `test_chat_events.py` — Telegram webhook, message processing
  - `test_jobs.py` — Job queue (retry, dead-letter, heartbeat)
  - `test_llm.py` — LLM client (chat, respond_with_rag, resilience)
  - `test_rbac.py` — Permissions, approval flow
  - `test_backup.py` — Backup/restore operations
  - `test_webui.py` — Web UI views, permissions
  - `test_api.py` — API endpoints, auth, rate limiting

### Monitoring
- ✅ **Prometheus metrics** — django-prometheus integration
- ✅ **Sentry integration** — error tracking and alerting
- ✅ **Structured logging** — JSON format with correlation IDs

### API Documentation
- ✅ **OpenAPI 3.0** — drf-spectacular with Swagger UI
- ✅ **API versioning** — `/api/v1/` prefix support

---

## 📖 Documentation

- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — Production deployment guide
- [RUNBOOK.md](docs/RUNBOOK.md) — Operational procedures
- [RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) — Release checklist
- [AUDIT.md](docs/AUDIT.md) — Full security and architecture audit

---

## 🛡️ Security

- **RBAC** — 7 system roles with scoped permissions
- **Approval Policies** — Scope-based approval workflows
- **Secret Encryption** — Fernet (AES-128-CBC) with audit logging
- **Rate Limiting** — 60 req/min per IP on webhooks
- **Webhook Verification** — Timing-attack-safe HMAC comparison
- **Redaction** — Automatic sensitive content detection
- **CSRF Protection** — Enabled on all browser-facing views
- **Production Hardening** — HSTS, XSS filter, secure cookies

---

## 🧪 Testing

```bash
# Run all tests
python manage.py test tests/

# Run specific test module
python manage.py test tests.test_retrieval

# Run with coverage
coverage run manage.py test tests/
coverage report

# Run smoke tests only
python manage.py test tests.test_smoke_p2_1
```

---

## 📊 Monitoring

### Health Checks
- `GET /health/` — Liveness check
- `GET /health/ready/` — Readiness (DB + Redis)
- `GET /health/llm/` — LLM provider status

### Prometheus Metrics
- `django_http_requests_total` — Request count
- `django_http_request_duration_seconds` — Request latency
- `celery_task_total` — Celery task metrics

### Sentry Integration
Configure `SENTRY_DSN` in environment to enable error tracking.

---

## 🏗️ Architecture

### Technology Stack
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Web Framework | Django 5.1+ | Core application |
| Database | PostgreSQL 16 + pgvector | Data + vector search |
| Cache/Broker | Redis 7 | Caching, Celery broker |
| Task Queue | Celery 5 | Async processing |
| Object Storage | MinIO (S3-compatible) | Attachments |
| LLM | OpenAI API (compatible) | Chat + embeddings |
| Monitoring | Prometheus + Sentry | Metrics + errors |

### System Layers
20 Django apps organized by domain:
- **ingest** — Telegram messages, archive import
- **retrieval** — RAG pipeline with hybrid search
- **security** — RBAC, secrets, approval
- **operations** — Jobs, backup, health checks

---

## ⚡ Quick Start

### Docker Compose (Recommended)
```bash
# Clone and configure
git clone https://github.com/voodoo2serg/RAG_for_AI.git
cd RAG_for_AI
cp .env.example .env
# Edit .env with your settings

# Start all services
docker compose up --build -d

# Create admin user
docker compose exec web python manage.py createsuperuser

# Run tests
docker compose exec web python manage.py test tests/
```

### Local Development
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt

make install
make migrate
make seed
make dev        # Start dev server
make worker     # Start Celery worker
make test       # Run tests
```

---

## 📝 License

MIT License — see [LICENSE](LICENSE) file.

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

**Requirements:**
- All tests must pass
- New features require tests
- Follow existing code style

---

*Production-hardened with ❤️ by the RAG for AI team.*
