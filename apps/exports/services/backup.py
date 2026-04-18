"""Backup bundle creation and verification service for P2.1 operational safety."""

import hashlib
import json
import logging
import os
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def create_backup_bundle(output_path: Optional[str] = None) -> Dict:
    """Create a complete backup bundle containing DB dump, wiki, context packs, agent profiles, eval data.

    Returns a dict with metadata about the backup.
    """
    from apps.wiki.models import WikiSpace, WikiPage, WikiRevision
    from apps.context_packs.models import ContextPack
    from apps.agent_profiles.models import AgentProfile
    from apps.retrieval.models import RetrievalEvaluationCase, RetrievalEvaluationRun, RetrievalEvaluationResult
    from apps.domains_projects.models import Domain, Project

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if not output_path:
        backup_dir = Path(getattr(settings, "BACKUP_DIR", "/var/backups/tkos"))
        backup_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(backup_dir / f"tkos_backup_{timestamp}.zip")

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": "P2.1",
        "environment": getattr(settings, "ENVIRONMENT", "unknown"),
        "files": [],
        "checksums": {},
    }

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. PostgreSQL dump
        db_dump = _create_db_dump()
        if db_dump:
            arcname = "database/pg_dump.sql"
            zf.writestr(arcname, db_dump)
            metadata["files"].append(arcname)
            metadata["checksums"][arcname] = hashlib.sha256(db_dump.encode()).hexdigest()

        # 2. Export wiki data
        wiki_data = _export_wiki()
        zf.writestr("wiki/wiki_spaces.json", json.dumps(wiki_data, default=str, ensure_ascii=False))
        metadata["files"].append("wiki/wiki_spaces.json")

        # 3. Export context packs
        packs_data = _export_context_packs()
        zf.writestr("context_packs/packs.json", json.dumps(packs_data, default=str, ensure_ascii=False))
        metadata["files"].append("context_packs/packs.json")

        # 4. Export agent profiles
        profiles_data = _export_agent_profiles()
        zf.writestr("agent_profiles/profiles.json", json.dumps(profiles_data, default=str, ensure_ascii=False))
        metadata["files"].append("agent_profiles/profiles.json")

        # 5. Export retrieval eval data
        eval_data = _export_evaluation_data()
        zf.writestr("evaluation/eval_data.json", json.dumps(eval_data, default=str, ensure_ascii=False))
        metadata["files"].append("evaluation/eval_data.json")

        # 6. Metadata manifest
        zf.writestr("MANIFEST.json", json.dumps(metadata, indent=2, default=str))

    # Final checksum of the zip
    with open(output_path, "rb") as f:
        metadata["bundle_sha256"] = hashlib.sha256(f.read()).hexdigest()
    metadata["bundle_path"] = output_path
    metadata["bundle_size_bytes"] = os.path.getsize(output_path)

    logger.info("Backup bundle created: %s (%d bytes)", output_path, metadata["bundle_size_bytes"])
    return metadata


def verify_backup_bundle(backup_path: str) -> Dict:
    """Verify backup bundle integrity. Returns dict with verification results."""
    result = {"path": backup_path, "valid": False, "errors": [], "files_found": []}

    if not os.path.exists(backup_path):
        result["errors"].append("File not found")
        return result

    try:
        with zipfile.ZipFile(backup_path, "r") as zf:
            bad = zf.testzip()
            if bad:
                result["errors"].append(f"Corrupt file: {bad}")
            result["files_found"] = zf.namelist()

            if "MANIFEST.json" in zf.namelist():
                manifest = json.loads(zf.read("MANIFEST.json"))
                result["manifest"] = manifest
                expected = set(manifest.get("files", []))
                actual = set(f for f in result["files_found"] if f not in ("MANIFEST.json",))
                missing = expected - actual
                if missing:
                    result["errors"].append(f"Missing files: {missing}")

        with open(backup_path, "rb") as f:
            result["sha256"] = hashlib.sha256(f.read()).hexdigest()

        result["valid"] = len(result["errors"]) == 0
    except zipfile.BadZipFile:
        result["errors"].append("Not a valid zip file")

    logger.info("Backup verification: %s -> valid=%s errors=%d",
                backup_path, result["valid"], len(result["errors"]))
    return result


def _create_db_dump() -> Optional[str]:
    """Create a PostgreSQL dump using pg_dump. Returns SQL string or None."""
    db_settings = settings.DATABASES.get("default", {})
    if "postgresql" not in db_settings.get("ENGINE", ""):
        logger.warning("Skipping DB dump — not PostgreSQL")
        return None
    try:
        env = os.environ.copy()
        env["PGPASSWORD"] = db_settings.get("PASSWORD", "")
        cmd = [
            "pg_dump",
            "-h", db_settings.get("HOST", "127.0.0.1"),
            "-p", str(db_settings.get("PORT", "5432")),
            "-U", db_settings.get("USER", ""),
            "-d", db_settings.get("NAME", ""),
            "--no-owner",
            "--no-privileges",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
        if result.returncode != 0:
            logger.error("pg_dump failed: %s", result.stderr[:500])
            return None
        return result.stdout
    except FileNotFoundError:
        logger.warning("pg_dump not found — skipping DB dump")
        return None
    except subprocess.TimeoutExpired:
        logger.error("pg_dump timed out")
        return None


def _export_wiki() -> List[Dict]:
    from apps.wiki.models import WikiSpace, WikiPage
    spaces = []
    for ws in WikiSpace.objects.filter(is_deleted=False).prefetch_related("pages__revisions"):
        pages = []
        for page in ws.pages.filter(is_deleted=False):
            revisions = [
                {"id": r.id, "content_text": r.content_text[:5000], "author_type": r.author_type,
                 "created_at": r.created_at.isoformat()}
                for r in (page.revisions.all() if hasattr(page, 'revisions') else [])
            ]
            pages.append({
                "id": page.id, "title": page.title, "slug": page.slug,
                "page_type": page.page_type, "summary": page.summary, "revisions": revisions,
            })
        spaces.append({"id": ws.id, "scope_type": ws.scope_type, "scope_id": ws.scope_id,
                        "name": ws.name, "pages": pages})
    return spaces


def _export_context_packs() -> List[Dict]:
    from apps.context_packs.models import ContextPack
    packs = []
    for cp in ContextPack.objects.filter(is_deleted=False).prefetch_related("rules", "guidelines"):
        rules = [{"title": r.title, "body": r.body[:500], "priority": r.priority}
                 for r in cp.rules.filter(is_active=True)]
        guidelines = [{"title": g.title, "body": g.body[:500]}
                      for g in cp.guidelines.filter(is_active=True)]
        packs.append({
            "id": cp.id, "name": cp.name, "scope_type": cp.scope_type,
            "scope_id": cp.scope_id, "status": cp.status,
            "rules": rules, "guidelines": guidelines,
        })
    return packs


def _export_agent_profiles() -> List[Dict]:
    from apps.agent_profiles.models import AgentProfile
    profiles = []
    for ap in AgentProfile.objects.filter(is_active=True):
        profiles.append({
            "id": ap.id, "slug": ap.slug, "name": ap.name,
            "system_prompt": ap.system_prompt[:2000],
        })
    return profiles


def _export_evaluation_data() -> Dict:
    from apps.retrieval.models import RetrievalEvaluationCase, RetrievalEvaluationRun
    cases = []
    for c in RetrievalEvaluationCase.objects.filter(is_deleted=False)[:100]:
        cases.append({"id": c.id, "query": c.query, "expected_entry_ids": c.expected_entry_ids})
    runs = []
    for r in RetrievalEvaluationRun.objects.filter(is_deleted=False)[:50]:
        runs.append({"id": r.id, "query_count": r.query_count, "avg_recall": str(r.avg_recall_at_5 or 0),
                     "avg_mrr": str(r.avg_mrr or 0)})
    return {"cases": cases, "runs": runs}
