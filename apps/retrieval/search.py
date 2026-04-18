from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.core.enums import RetrievalMode, SensitivityLevel
from apps.retrieval.embeddings import get_embedding_service
from apps.retrieval.models import RagCorpusEntry
from apps.retrieval.redaction import should_exclude_entry
from apps.retrieval.reranker import get_reranker, RerankRequest

logger = logging.getLogger(__name__)

try:
    from pgvector.django import CosineDistance  # type: ignore
except Exception:  # pragma: no cover
    CosineDistance = None

ROLE_WEIGHTS = {
    RetrievalMode.BUSINESS: {
        "owner_idea": 1.25,
        "owner_decision": 1.30,
        "owner_instruction": 1.10,
        "agent_reasoning_trace": 0.45,
        "debug_trace": 0.35,
    },
    RetrievalMode.DEBUG: {
        "agent_reasoning_trace": 1.30,
        "debug_trace": 1.25,
        "test_result": 1.20,
        "code_instruction": 1.05,
        "owner_idea": 0.60,
    },
    RetrievalMode.OPS: {
        "ops_instruction": 1.30,
        "git_event": 1.10,
        "owner_instruction": 1.00,
    },
    RetrievalMode.HISTORICAL: {},
}

ENTRY_WEIGHTS = {
    RetrievalMode.BUSINESS: {"knowledge": 1.20, "summary": 1.10, "wiki": 1.05, "message": 1.00, "rule": 1.15},
    RetrievalMode.DEBUG: {"message": 1.20, "summary": 1.05, "knowledge": 0.90, "wiki": 0.85, "rule": 1.00},
    RetrievalMode.OPS: {"rule": 1.20, "wiki": 1.05, "message": 1.00, "summary": 0.95, "knowledge": 0.90},
    RetrievalMode.HISTORICAL: {"message": 1.00, "summary": 1.10, "knowledge": 1.00, "wiki": 1.00, "rule": 0.95},
}

@dataclass
class SearchResult:
    obj: RagCorpusEntry
    score: float
    source: str = "corpus"
    breakdown: Dict[str, float] = field(default_factory=dict)


class SearchEngine:
    def __init__(self):
        self.embedding_svc = get_embedding_service()

    def search_corpus(
        self,
        query: str,
        project_id: Optional[int] = None,
        domain_id: Optional[int] = None,
        retrieval_mode: str = RetrievalMode.BUSINESS,
        source_id: Optional[int] = None,
        limit: int = 20,
        exclude_sensitive: bool = True,
    ) -> List[SearchResult]:
        qs = RagCorpusEntry.objects.filter(is_deleted=False, is_active=True)
        if project_id:
            qs = qs.filter(project_id=project_id)
        elif domain_id:
            qs = qs.filter(domain_id=domain_id)
        if source_id:
            qs = qs.filter(Q(source_id=source_id) | Q(source_id__isnull=True))
        if exclude_sensitive:
            qs = qs.exclude(sensitivity_level__in=[SensitivityLevel.SECRET, SensitivityLevel.CONFIDENTIAL])
        qs = qs.order_by("-storage_tier", "-retrieval_weight", "-updated_at")

        keyword_candidates = self._keyword_candidates(qs, query, retrieval_mode, limit=limit * 4)
        semantic_candidates = self._semantic_candidates(qs, query, retrieval_mode, limit=limit * 4)
        merged = {}
        for item in keyword_candidates + semantic_candidates:
            cur = merged.get(item.obj.id)
            if cur is None or item.score > cur.score:
                merged[item.obj.id] = item
        ranked = sorted(merged.values(), key=lambda r: r.score, reverse=True)
        ranked = [r for r in ranked if not should_exclude_entry(r.obj, allow_confidential=not exclude_sensitive)]
        reranker = get_reranker()
        source_slug = getattr(getattr(ranked[0].obj, 'source', None), 'slug', '') if ranked else ""
        ranked = reranker.rerank(RerankRequest(query=query, retrieval_mode=retrieval_mode, source_slug=source_slug), ranked)
        return ranked[:limit]

    def diagnostics(self, *args, **kwargs) -> Dict[str, object]:
        results = self.search_corpus(*args, **kwargs)
        return {
            "query": kwargs.get("query") if "query" in kwargs else (args[0] if args else ""),
            "count": len(results),
            "hot_count": sum(1 for r in results if getattr(r.obj, "storage_tier", "hot") == "hot"),
            "cold_count": sum(1 for r in results if getattr(r.obj, "storage_tier", "hot") == "cold"),
            "results": [
                {
                    "entry_id": r.obj.id,
                    "title": r.obj.title,
                    "entry_type": r.obj.entry_type,
                    "storage_tier": getattr(r.obj, "storage_tier", "hot"),
                    "score": round(r.score, 5),
                    "source": r.source,
                    "breakdown": {k: round(v, 5) for k, v in r.breakdown.items()},
                }
                for r in results
            ],
        }

    def _keyword_candidates(self, qs, query: str, retrieval_mode: str, limit: int) -> List[SearchResult]:
        words = [w.strip().lower() for w in query.split() if len(w.strip()) >= 3][:12]
        if not words:
            return []
        q = Q()
        for w in words:
            q |= Q(text__icontains=w) | Q(title__icontains=w)
        hits = []
        for entry in qs.filter(q)[: limit * 2]:
            text_lower = f"{entry.title} {entry.text}".lower()
            match_count = sum(1 for w in words if w in text_lower)
            lexical = 0.40 * (match_count / max(len(words), 1))
            score, breakdown = self._apply_weights(entry, lexical, retrieval_mode)
            breakdown["lexical"] = lexical
            hits.append(SearchResult(entry, score, source="keyword", breakdown=breakdown))
        return sorted(hits, key=lambda r: r.score, reverse=True)[:limit]

    def _semantic_candidates(self, qs, query: str, retrieval_mode: str, limit: int) -> List[SearchResult]:
        if not self.embedding_svc.is_available():
            return []
        qemb = self.embedding_svc.generate(query)
        if not qemb:
            return []
        if self._supports_pgvector_sql():
            return self._semantic_candidates_pgvector(qs, qemb, retrieval_mode, limit)
        return self._semantic_candidates_fallback(qs, qemb, retrieval_mode, limit)

    def _supports_pgvector_sql(self) -> bool:
        engine = settings.DATABASES["default"]["ENGINE"]
        return "postgresql" in engine and getattr(settings, "ENABLE_PGVECTOR", True) and CosineDistance is not None

    def _semantic_candidates_pgvector(self, qs, qemb, retrieval_mode: str, limit: int) -> List[SearchResult]:
        annotated = (
            qs.exclude(embedding__isnull=True)
            .annotate(vector_distance=CosineDistance("embedding", qemb))
            .order_by("vector_distance")[:limit]
        )
        results = []
        for entry in annotated:
            distance = float(getattr(entry, "vector_distance", 1.0) or 1.0)
            sim = max(0.0, 1.0 - distance)
            score, breakdown = self._apply_weights(entry, sim * 0.60, retrieval_mode)
            breakdown["semantic_similarity"] = sim
            results.append(SearchResult(entry, score, source="semantic_pgvector", breakdown=breakdown))
        return sorted(results, key=lambda r: r.score, reverse=True)[:limit]

    def _semantic_candidates_fallback(self, qs, qemb, retrieval_mode: str, limit: int) -> List[SearchResult]:
        logger.warning("Using fallback Python semantic search; pgvector SQL path unavailable")
        results = []
        for entry in qs[:1000]:
            if not entry.embedding:
                continue
            sim = self.embedding_svc.cosine_similarity(qemb, entry.embedding)
            if sim <= 0.05:
                continue
            score, breakdown = self._apply_weights(entry, sim * 0.60, retrieval_mode)
            breakdown["semantic_similarity"] = sim
            results.append(SearchResult(entry, score, source="semantic_fallback", breakdown=breakdown))
        return sorted(results, key=lambda r: r.score, reverse=True)[:limit]

    def _apply_weights(self, entry: RagCorpusEntry, base_score: float, retrieval_mode: str):
        role_weight = self._role_weight(entry.message_role, retrieval_mode)
        entry_weight = self._entry_weight(entry.entry_type, retrieval_mode)
        freshness = self._freshness_multiplier(entry)
        trust = float(entry.trust_score or Decimal("0.5")) + 0.5
        source_weight = self._source_weight(entry)
        retrieval_weight = float(entry.retrieval_weight or Decimal("1.0"))
        storage_bonus = 1.03 if getattr(entry, "storage_tier", "hot") == "hot" else 0.93
        reviewed_bonus = 1.02 if getattr(entry, "is_reviewed", False) else 1.0
        score = base_score * role_weight * entry_weight * freshness * trust * source_weight * retrieval_weight * storage_bonus * reviewed_bonus
        breakdown = {
            "base_score": base_score,
            "role_weight": role_weight,
            "entry_weight": entry_weight,
            "freshness": freshness,
            "trust": trust,
            "source_weight": source_weight,
            "retrieval_weight": retrieval_weight,
            "storage_bonus": storage_bonus,
            "reviewed_bonus": reviewed_bonus,
        }
        return score, breakdown

    def _freshness_multiplier(self, entry: RagCorpusEntry) -> float:
        age_days = max((timezone.now() - entry.updated_at).total_seconds() / 86400.0, 0.0)
        freshness_decay = 1.0 / (1.0 + age_days / 60.0)
        stored_freshness = float(entry.freshness_score or Decimal("0.5"))
        return max(min((freshness_decay + stored_freshness) / 2.0, 1.25), 0.50)

    def _role_weight(self, role: str, retrieval_mode: str) -> float:
        return ROLE_WEIGHTS.get(retrieval_mode, {}).get(role, 1.0)

    def _entry_weight(self, entry_type: str, retrieval_mode: str) -> float:
        return ENTRY_WEIGHTS.get(retrieval_mode, {}).get(entry_type, 1.0)

    def _source_weight(self, entry: RagCorpusEntry) -> float:
        if entry.source_id and entry.source:
            base = float(getattr(entry.source, "retrieval_weight", Decimal("1.0")) or Decimal("1.0"))
            if entry.source.source_kind == "archive_import":
                bias = float(getattr(entry.source, "archive_bias", Decimal("0.85")) or Decimal("0.85"))
                return base * bias
            return base
        return float(entry.source_weight or Decimal("1.0"))


def get_search_engine() -> SearchEngine:
    return SearchEngine()
