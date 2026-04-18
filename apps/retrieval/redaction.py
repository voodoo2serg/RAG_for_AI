import re
from apps.core.enums import SensitivityLevel

# Patterns that match whole-word boundaries only
REDACTION_PATTERNS = [
    re.compile(r'\bapi[_\s]?key\b', re.IGNORECASE),
    re.compile(r'\bpassword\b', re.IGNORECASE),
    re.compile(r'\bpasswd\b', re.IGNORECASE),
    re.compile(r'\bsecret\b', re.IGNORECASE),
    re.compile(r'\bsmtp\b', re.IGNORECASE),
    re.compile(r'\bbearer\s+\S+', re.IGNORECASE),
    re.compile(r'\bssh[_\s]?(?:key|config|pass|secret|private|authorized)?\b', re.IGNORECASE),
]

# Secret-like patterns (regex-based detection)
SECRET_VALUE_PATTERNS = [
    re.compile(r'\b[A-Za-z0-9+/]{40,}={0,2}\b'),  # Base64 encoded secrets
    re.compile(r'\b(?:sk|pk|pk_test|pk_live|sk_test|sk_live)[_-][A-Za-z0-9]{20,}\b'),  # Stripe-style keys
    re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b'),  # GitHub tokens
    re.compile(r'\bxox[bpas]-[A-Za-z0-9-]{10,}\b'),  # Slack tokens
    re.compile(r'\bAIza[A-Za-z0-9_-]{35}\b'),  # Google API keys
]


def is_sensitive_text(text: str) -> bool:
    lower = (text or "").lower()
    # Check redaction tokens (whole-word)
    for pattern in REDACTION_PATTERNS:
        if pattern.search(lower):
            return True
    # Check for secret-like value patterns
    for pattern in SECRET_VALUE_PATTERNS:
        if pattern.search(text):
            return True
    return False


def redact_text(text: str) -> str:
    result = text or ""
    for pattern in REDACTION_PATTERNS:
        result = pattern.sub('[REDACTED]', result)
    for pattern in SECRET_VALUE_PATTERNS:
        result = pattern.sub('[REDACTED]', result)
    return result


def should_exclude_entry(entry, allow_confidential: bool = False) -> bool:
    level = getattr(entry, "sensitivity_level", SensitivityLevel.INTERNAL)
    if level == SensitivityLevel.SECRET:
        return True
    if level == SensitivityLevel.CONFIDENTIAL and not allow_confidential:
        return True
    if is_sensitive_text(getattr(entry, "text", "")) or is_sensitive_text(getattr(entry, "title", "")):
        return True
    return False
