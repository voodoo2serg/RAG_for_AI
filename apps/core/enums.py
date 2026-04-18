from django.db import models

class ScopeType(models.TextChoices):
    GLOBAL = "global", "Global"
    DOMAIN = "domain", "Domain"
    PROJECT = "project", "Project"
    THREAD = "thread", "Thread"
    AGENT_PROFILE = "agent_profile", "Agent Profile"

class SensitivityLevel(models.TextChoices):
    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Internal"
    CONFIDENTIAL = "confidential", "Confidential"
    SECRET = "secret", "Secret"

class RetrievalMode(models.TextChoices):
    BUSINESS = "business_mode", "Business"
    DEBUG = "debug_mode", "Debug"
    OPS = "ops_mode", "Ops"
    HISTORICAL = "historical_mode", "Historical"
