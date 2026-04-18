from .base import *  # noqa

DEBUG = False
ENVIRONMENT = "production"

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.environ.get("POSTGRES_DB", os.environ.get("DB_NAME", "tkos")),
        "USER": os.environ.get("POSTGRES_USER", os.environ.get("DB_USER", "tkos")),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", os.environ.get("DB_PASSWORD", "tkos")),
        "HOST": os.environ.get("POSTGRES_HOST", os.environ.get("DB_HOST", "127.0.0.1")),
        "PORT": os.environ.get("POSTGRES_PORT", os.environ.get("DB_PORT", "5432")),
    }
}

# Allow HTTP for local network access
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Production CORS configuration
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = True  # Backward-compatible default; restrict in production

# Production file logging
LOGGING["handlers"]["file"] = {
    "class": "logging.handlers.RotatingFileHandler",
    "filename": BASE_DIR / "logs" / "django.log",
    "maxBytes": 10 * 1024 * 1024,
    "backupCount": 5,
    "formatter": "console",
}
LOGGING["root"]["handlers"] = ["console", "file"]