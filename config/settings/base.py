from pathlib import Path
import os
import structlog
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

ENVIRONMENT = os.environ.get("APP_ENV", "dev").lower()
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-dev-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "pgvector",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "apps.core",
    "apps.accounts",
    "apps.chat_events",
    "apps.domains_projects",
    "apps.threads",
    "apps.contacts",
    "apps.wiki",
    "apps.context_packs",
    "apps.agent_profiles",
    "apps.knowledge",
    "apps.summaries",
    "apps.retrieval",
    "apps.prompts",
    "apps.archive_ingest",
    "apps.secrets",
    "apps.artifacts",
    "apps.jobs",
    "apps.webui",
    "apps.exports",
    "apps.llm",
    "apps.health",
    "apps.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.RequestIDMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("DB_NAME", BASE_DIR / "dev.sqlite3"),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", ""),
    }
}

CACHES = {
    "default": {
        "BACKEND": os.environ.get("CACHE_BACKEND", "django.core.cache.backends.locmem.LocMemCache"),
        "LOCATION": os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"),
    }
}

CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "2048"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.7"))

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "1536"))
ENABLE_PGVECTOR = os.environ.get("ENABLE_PGVECTOR", "true").lower() == "true"
VECTOR_SEARCH_PROBES = int(os.environ.get("VECTOR_SEARCH_PROBES", "10"))

MAX_CONTEXT_CHARS = int(os.environ.get("MAX_CONTEXT_CHARS", "30000"))

SECRET_MASTER_KEY = os.environ.get("SECRET_MASTER_KEY", "")
ALLOW_PLAINTEXT_SECRETS_IN_DEV = os.environ.get("ALLOW_PLAINTEXT_SECRETS_IN_DEV", "false").lower() == "true"

S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
S3_BUCKET_RAW = os.environ.get("S3_BUCKET_RAW", "tko-raw")
S3_BUCKET_ATTACHMENTS = os.environ.get("S3_BUCKET_ATTACHMENTS", "tko-attachments")
S3_BUCKET_EXPORTS = os.environ.get("S3_BUCKET_EXPORTS", "tko-exports")
S3_BUCKET_SNAPSHOTS = os.environ.get("S3_BUCKET_SNAPSHOTS", "tko-snapshots")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "()": "structlog.stdlib.ProcessorFormatter",
            "processor": structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        },
        "console": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "console"},
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "apps": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

CORS_ALLOW_ALL_ORIGINS = os.environ.get("CORS_ALLOW_ALL_ORIGINS", "false").lower() == "true"


if ENVIRONMENT in {"prod", "production", "staging"}:
    if not SECRET_MASTER_KEY:
        raise ImproperlyConfigured("SECRET_MASTER_KEY is required in production/staging")
    if SECRET_KEY == "unsafe-dev-key-change-me":
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production/staging")
