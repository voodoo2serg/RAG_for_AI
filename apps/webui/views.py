from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from apps.domains_projects.models import Domain, Project
from apps.wiki.models import WikiPage
from apps.context_packs.models import ContextPack
from apps.chat_events.models import Message, TelegramSource
from apps.retrieval.models import RetrievalSession, RagCorpusEntry, ReviewQueueItem, RetrievalEvaluationCase, RetrievalEvaluationRun
from apps.retrieval.diagnostics import build_corpus_diagnostics


def _tree_context():
    return {"domains": Domain.objects.filter(is_deleted=False).prefetch_related("projects").order_by("display_order", "name")}


@login_required
def dashboard(request):
    ctx = _tree_context()
    ctx["sources"] = TelegramSource.objects.order_by("display_name")
    return render(request, "webui/dashboard.html", ctx)


@login_required
def explorer(request):
    return render(request, "webui/explorer.html", _tree_context())


@login_required
def domain_detail(request, domain_id: int):
    domain = get_object_or_404(Domain, pk=domain_id)
    messages = Message.objects.filter(domain=domain, is_deleted=False).select_related("source").order_by("-timestamp")[:100]
    wiki_pages = WikiPage.objects.filter(wiki_space__scope_type="domain", wiki_space__scope_id=domain.id, is_deleted=False)
    ctx = {**_tree_context(), "domain": domain, "messages": messages, "wiki_pages": wiki_pages}
    return render(request, "webui/domain_detail.html", ctx)


@login_required
def project_detail(request, project_id: int):
    project = get_object_or_404(Project, pk=project_id)
    messages = Message.objects.filter(project=project, is_deleted=False).select_related("source").order_by("-timestamp")[:100]
    wiki_pages = WikiPage.objects.filter(wiki_space__scope_type="project", wiki_space__scope_id=project.id, is_deleted=False)
    ctx = {**_tree_context(), "project": project, "messages": messages, "wiki_pages": wiki_pages}
    return render(request, "webui/project_detail.html", ctx)


@login_required
def wiki_page_detail(request, page_id: int):
    page = get_object_or_404(WikiPage, pk=page_id)
    revision = page.revisions.order_by("-created_at").first()
    ctx = {**_tree_context(), "page": page, "revision": revision}
    return render(request, "webui/wiki_page.html", ctx)


@login_required
def message_viewer(request):
    messages = Message.objects.filter(is_deleted=False).select_related("source", "domain", "project", "thread").order_by("-timestamp")[:200]
    ctx = {**_tree_context(), "messages": messages}
    return render(request, "webui/message_viewer.html", ctx)


@login_required
def rule_viewer(request, scope_type: str, scope_id: int):
    packs = ContextPack.objects.filter(scope_type=scope_type, scope_id=scope_id, is_deleted=False).prefetch_related("rules", "guidelines", "skills", "settings")
    ctx = {**_tree_context(), "packs": packs, "scope_type": scope_type, "scope_id": scope_id}
    return render(request, "webui/rule_viewer.html", ctx)


@login_required
def retrieval_session_detail(request, session_id: int):
    session = get_object_or_404(RetrievalSession, pk=session_id)
    ctx = {**_tree_context(), "session": session}
    return render(request, "webui/retrieval_session.html", ctx)


@login_required
def source_list(request):
    sources = TelegramSource.objects.order_by("display_name")
    ctx = {**_tree_context(), "sources": sources}
    return render(request, "webui/source_list.html", ctx)


@login_required
def source_detail(request, source_id: int):
    source = get_object_or_404(TelegramSource, pk=source_id)
    messages = Message.objects.filter(source=source, is_deleted=False).order_by("-timestamp")[:100]
    ctx = {**_tree_context(), "source": source, "messages": messages}
    return render(request, "webui/source_detail.html", ctx)


@login_required
def rag_corpus_viewer(request):
    entries = RagCorpusEntry.objects.filter(is_deleted=False, is_active=True).select_related("source", "domain", "project", "thread").order_by("-updated_at")[:200]
    ctx = {**_tree_context(), "entries": entries}
    return render(request, "webui/rag_corpus.html", ctx)


@login_required
def retrieval_diagnostics(request):
    query = request.GET.get("q", "")
    project_id = request.GET.get("project_id") or None
    domain_id = request.GET.get("domain_id") or None
    source_id = request.GET.get("source_id") or None
    mode = request.GET.get("mode", "business_mode")
    diagnostics = None
    if query:
        diagnostics = build_corpus_diagnostics(
            query=query,
            project_id=int(project_id) if project_id else None,
            domain_id=int(domain_id) if domain_id else None,
            source_id=int(source_id) if source_id else None,
            retrieval_mode=mode,
            limit=20,
        )
    ctx = {**_tree_context(), "diagnostics": diagnostics, "sources": TelegramSource.objects.order_by("display_name")}
    return render(request, "webui/retrieval_diagnostics.html", ctx)


@login_required
def review_queue(request):
    items = ReviewQueueItem.objects.select_related("source", "project", "domain").all()[:200]
    ctx = {**_tree_context(), "items": items}
    return render(request, "webui/review_queue.html", ctx)


@login_required
def evaluation_center(request):
    runs = RetrievalEvaluationRun.objects.order_by("-created_at")[:50]
    cases = RetrievalEvaluationCase.objects.select_related("source", "project", "domain").order_by("-created_at")[:100]
    ctx = {**_tree_context(), "runs": runs, "cases": cases}
    return render(request, "webui/evaluation_center.html", ctx)
