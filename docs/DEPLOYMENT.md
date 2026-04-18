# TKOS Deployment Guide — Debian 13

## Prerequisites

- Debian 13 (Trixie)
- PostgreSQL 16+ with pgvector
- Redis 7+
- Python 3.12+
- Nginx
- Domain name with SSL certificate

## Quick Install

```bash
# 1. Clone repo
sudo mkdir -p /opt/tkos
sudo chown $USER:$USER /opt/tkos
git clone https://github.com/voodoo2serg/RAG_for_AI.git /opt/tkos
cd /opt/tkos

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/prod.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set all required variables (SECRET_KEY, OPENAI_API_KEY, etc.)

# 4. Initialize database
python manage.py migrate

# 5. Seed data
python manage.py seed_roles
python manage.py seed_domains
python manage.py seed_agent_profiles
python manage.py seed_global_context

# 6. Create superuser
python manage.py createsuperuser

# 7. Collect static files
python manage.py collectstatic --noinput

# 8. Register Telegram bot
python manage.py register_telegram_source my-bot \
    --display-name "My Bot" --kind live_bot --default-domain work
```

## Systemd Services

```bash
# Copy service files
sudo cp deploy/systemd/tko-*.service /etc/systemd/system/
sudo cp deploy/systemd/tko-*.timer /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable tko-web tko-jobs.timer
sudo systemctl start tko-web tko-jobs.timer
```

## Nginx

```bash
sudo cp deploy/nginx/tko.conf /etc/nginx/sites-available/tkos
sudo ln -s /etc/nginx/sites-available/tkos /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## Verify

```bash
# Health check
curl http://127.0.0.1:8000/health/ready/

# Check logs
sudo journalctl -u tko-web -f
```

## Restart / Rollback

```bash
# Update code
cd /opt/tkos && git pull origin main
source .venv/bin/activate && pip install -r requirements/prod.txt
python manage.py migrate
sudo systemctl restart tko-web

# Rollback
git checkout <previous-commit>
python manage.py migrate
sudo systemctl restart tko-web
```
