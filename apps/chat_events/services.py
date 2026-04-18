import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def normalize_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    text = raw_text.strip()
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def route_message_to_project(text: str, domain, source):
    from apps.domains_projects.models import Project
    if not domain or not text:
        return source.default_project

    lower = text.lower()
    for p in Project.objects.filter(domain=domain, is_deleted=False):
        if p.canonical_name.lower() in lower or p.slug in lower:
            return p
        for alias in (p.aliases or []):
            if alias.lower() in lower:
                return p

    if source and source.default_project:
        return source.default_project
    return Project.objects.filter(domain=domain, parent_project__isnull=True, is_deleted=False).first()


def sanitize_sender_name(name: str) -> str:
    if not name:
        return "Unknown"
    return re.sub(r"[<>&\"\']+", "", name.strip())[:255]
