.PHONY: help install dev migrate makemigrations seed run worker worker-beat embeddings shell test lint clean docker-up docker-down docker-logs superuser

help: ## Show this help
        @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
        python -m venv .venv
        .venv/bin/pip install -r requirements/dev.txt

dev: ## Run development server
        .venv/bin/python manage.py runserver --settings=config.settings.dev

migrate: ## Run database migrations
        .venv/bin/python manage.py migrate --settings=config.settings.dev

makemigrations: ## Create new migrations
        .venv/bin/python manage.py makemigrations --settings=config.settings.dev

seed: ## Run all seed commands
        .venv/bin/python manage.py seed_domains --settings=config.settings.dev
        .venv/bin/python manage.py seed_agent_profiles --settings=config.settings.dev
        .venv/bin/python manage.py seed_global_context --settings=config.settings.dev

run: dev ## Alias for dev

worker: ## Run Celery worker
        DJANGO_SETTINGS_MODULE=config.settings.dev .venv/bin/celery -A config.celery worker --loglevel=info

worker-beat: ## Run Celery beat scheduler
        DJANGO_SETTINGS_MODULE=config.settings.dev .venv/bin/celery -A config.celery beat --loglevel=info

embeddings: ## Generate embeddings for all messages
        .venv/bin/python manage.py generate_embeddings --settings=config.settings.dev

shell: ## Open Django shell
        .venv/bin/python manage.py shell --settings=config.settings.dev

test: ## Run tests
        .venv/bin/python manage.py test --settings=config.settings.dev -v 2

lint: ## Run code checks
        .venv/bin/python -m flake8 apps/ config/ --max-line-length=120 --ignore=E501,W503

clean: ## Clean generated files
        find . -type d -name __pycache__ -exec rm -rf {} +
        rm -rf .venv/ staticfiles/ *.egg-info/

docker-up: ## Start all services with Docker Compose
        docker compose up --build -d

docker-down: ## Stop all services
        docker compose down

docker-logs: ## Show logs
        docker compose logs -f web worker

superuser: ## Create admin user
        .venv/bin/python manage.py createsuperuser --settings=config.settings.dev
