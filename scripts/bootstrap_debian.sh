#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
cp -n .env.example .env || true
python manage.py makemigrations
python manage.py migrate --settings=config.settings.dev
python manage.py seed_domains --settings=config.settings.dev
python manage.py seed_agent_profiles --settings=config.settings.dev
python manage.py seed_global_context --settings=config.settings.dev
echo "Bootstrap complete"
