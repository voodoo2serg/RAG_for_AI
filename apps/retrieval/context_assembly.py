import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from django.conf import settings

from apps.context_packs.models import ContextPack
from apps.agent_profiles.models import AgentProfile
from apps.retrieval.search import get_search_engine
from apps.wiki.models import WikiPage
from apps.core.enums import RetrievalMode

logger = logging.getLogger(__name__)


@dataclass
class AssembledContext:
    system_prompt: str = ""
    rules: List[str] = field(default_factory=list)
    guidelines: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    corpus_snippets: List[str] = field(default_factory=list)
    knowledge_items: List[str] = field(default_factory=list)
    summaries: List[str] = field(default_factory=list)
    wiki_excerpts: List[str] = field(default_factory=list)
    source_count: int = 0
    applied_context_pack_ids: List[int] = field(default_factory=list)
    selected_corpus_entry_ids: List[int] = field(default_factory=list)
    source_slug: str = ""
    retrieval_mode: str = RetrievalMode.BUSINESS
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    MAX_CONTEXT_CHARS = int(getattr(settings, "MAX_CONTEXT_CHARS", "30000"))

    def to_prompt_text(self) -> str:
        parts = [f"## System Instructions\n{self.system_prompt}"] if self.system_prompt else []
        if self.rules:
            parts.append("## Active Rules\n" + "\n".join(f"- {r}" for r in self.rules))
        if self.guidelines:
            parts.append("## Guidelines\n" + "\n".join(f"- {g}" for g in self.guidelines))
        if self.settings:
            settings_text = "\n".join(f"- {k}: {v}" for k, v in self.settings.items())
            parts.append(f"## Settings\n{settings_text}")
        if self.knowledge_items:
            parts.append("## Knowledge Items\n" + "\n".join(f"- {k}" for k in self.knowledge_items))
        if self.summaries:
            parts.append("## Summaries\n" + "\n".join(f"- {s}" for s in self.summaries))
        if self.wiki_excerpts:
            parts.append("## Wiki\n" + "\n".join(f"- {w}" for w in self.wiki_excerpts))
        if self.corpus_snippets:
            parts.append("## Retrieved Evidence\n" + "\n---\n".join(self.corpus_snippets))
        text = "\n\n".join(parts)
        if len(text) > self.MAX_CONTEXT_CHARS:
            text = text[:self.MAX_CONTEXT_CHARS] + "\n\n[... context truncated due to length limit ...]"
        return text


class ContextAssembler:
    def __init__(self):
        self.search_engine = get_search_engine()

    def assemble(self, query: str, project_id: Optional[int] = None, domain_id: Optional[int] = None, agent_profile_slug: Optional[str] = None, source=None, max_entries: int = 15) -> AssembledContext:
        ctx = AssembledContext(source_slug=getattr(source, "slug", ""))

        agent = AgentProfile.objects.filter(slug=agent_profile_slug, is_active=True).first() if agent_profile_slug else None
        if agent:
            ctx.system_prompt = agent.system_prompt
        if source and source.source_prompt_prefix:
            ctx.system_prompt = (ctx.system_prompt + "\n\n" + source.source_prompt_prefix).strip() if ctx.system_prompt else source.source_prompt_prefix

        packs = self._load_context_packs(domain_id, project_id, source)
        ctx.applied_context_pack_ids = [p.id for p in packs]
        ctx.rules = self._extract_rules(packs)
        ctx.guidelines = self._extract_guidelines(packs)
        ctx.skills = self._extract_skills(packs)
        ctx.settings = self._extract_settings(packs)
        ctx.retrieval_mode = source.default_retrieval_mode if source and source.default_retrieval_mode else RetrievalMode.BUSINESS

        corpus_results = self.search_engine.search_corpus(
            query=query,
            project_id=project_id,
            domain_id=domain_id,
            retrieval_mode=ctx.retrieval_mode,
            source_id=getattr(source, 'id', None),
            limit=max_entries,
        )
        ctx.diagnostics = {"corpus_results": []}
        for result in corpus_results:
            entry = result.obj
            ctx.selected_corpus_entry_ids.append(entry.id)
            snippet = f"[{entry.entry_type}|{entry.message_role or '-'}|score={result.score:.2f}] {entry.title} {entry.text[:400]}".strip()
            ctx.diagnostics['corpus_results'].append({
                'entry_id': entry.id,
                'entry_type': entry.entry_type,
                'title': entry.title,
                'score': round(result.score, 5),
                'source': result.source,
                'breakdown': result.breakdown,
            })
            ctx.corpus_snippets.append(snippet)
            if entry.entry_type == 'knowledge':
                ctx.knowledge_items.append(entry.text[:250])
            elif entry.entry_type == 'summary':
                ctx.summaries.append(entry.text[:250])
            elif entry.entry_type == 'wiki':
                ctx.wiki_excerpts.append(entry.text[:250])

        for wp in self._load_wiki(project_id, domain_id):
            latest = wp.revisions.order_by('-created_at').first()
            if latest:
                excerpt = f"**{wp.title}**: {latest.content_text[:200]}"
                if excerpt not in ctx.wiki_excerpts:
                    ctx.wiki_excerpts.append(excerpt)

        ctx.source_count = len(ctx.selected_corpus_entry_ids)
        return ctx

    def _load_context_packs(self, domain_id, project_id, source):
        qs = ContextPack.objects.filter(is_deleted=False, status='active', scope_type='global', scope_id=0)
        if domain_id:
            qs = qs | ContextPack.objects.filter(is_deleted=False, status='active', scope_type='domain', scope_id=domain_id)
        if project_id:
            qs = qs | ContextPack.objects.filter(is_deleted=False, status='active', scope_type='project', scope_id=project_id)
        if source and getattr(source, 'default_context_pack_id', None):
            qs = qs | ContextPack.objects.filter(pk=source.default_context_pack_id, is_deleted=False)
        return list(qs.prefetch_related('rules', 'guidelines', 'skills', 'settings'))

    def _extract_rules(self, packs):
        return [f"[{pack.name}] {r.title}: {r.body[:200]}" for pack in packs for r in pack.rules.filter(is_active=True).order_by('priority')][:15]

    def _extract_guidelines(self, packs):
        return [f"[{pack.name}] {g.title}: {g.body[:200]}" for pack in packs for g in pack.guidelines.filter(is_active=True)][:10]

    def _extract_skills(self, packs):
        return [f"[{s.skill_key}] {s.title}: {s.description[:100]}" for pack in packs for s in pack.skills.filter(is_enabled=True)][:10]

    def _extract_settings(self, packs):
        settings = {}
        for pack in packs:
            for s in pack.settings.filter(is_active=True):
                settings[s.key] = s.value_json or s.value_text
        return settings

    def _load_wiki(self, project_id, domain_id):
        qs = WikiPage.objects.filter(is_active=True, is_deleted=False)
        if project_id:
            qs = qs.filter(wiki_space__scope_type='project', wiki_space__scope_id=project_id)
        elif domain_id:
            qs = qs.filter(wiki_space__scope_type='domain', wiki_space__scope_id=domain_id)
        return list(qs.prefetch_related('revisions')[:5])


def get_context_assembler() -> ContextAssembler:
    return ContextAssembler()
