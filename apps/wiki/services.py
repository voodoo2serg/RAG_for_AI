from .models import WikiSpace, WikiPage, WikiRevision
from apps.core.enums import ScopeType
from apps.domains_projects.models import Domain, Project
from apps.summaries.models import Summary
from apps.knowledge.models import KnowledgeItem


def ensure_domain_wiki(domain: Domain):
    space, _ = WikiSpace.objects.get_or_create(
        scope_type=ScopeType.DOMAIN,
        scope_id=domain.id,
        defaults={"name": f"Domain: {domain.name}", "slug": f"domain-{domain.slug}", "description": domain.description},
    )
    page, created = WikiPage.objects.get_or_create(
        wiki_space=space,
        slug="overview",
        defaults={
            "title": f"{domain.name} — обзор",
            "page_type": WikiPage.PageType.DOMAIN_OVERVIEW,
            "summary": domain.description or "",
        },
    )
    if created:
        rev = WikiRevision.objects.create(
            wiki_page=page,
            content_text=f"# {domain.name}\n\n{domain.description or 'Описание домена пока не заполнено.'}\n",
            author_type="system",
        )
        page.current_revision = rev
        page.save(update_fields=['current_revision', 'updated_at'])
    return page


def ensure_project_wiki(project: Project):
    space, _ = WikiSpace.objects.get_or_create(
        scope_type=ScopeType.PROJECT,
        scope_id=project.id,
        defaults={"name": f"Project: {project.canonical_name}", "slug": f"project-{project.domain.slug}-{project.slug}", "description": project.description},
    )
    page, created = WikiPage.objects.get_or_create(
        wiki_space=space,
        slug="overview",
        defaults={
            "title": f"{project.canonical_name} — обзор",
            "page_type": WikiPage.PageType.PROJECT_OVERVIEW,
            "summary": project.description or "",
        },
    )
    if created:
        rev = WikiRevision.objects.create(
            wiki_page=page,
            content_text=f"# {project.canonical_name}\n\nДомен: **{project.domain.name}**\n\n{project.description or 'Описание проекта пока не заполнено.'}\n",
            author_type="system",
        )
        page.current_revision = rev
        page.save(update_fields=['current_revision', 'updated_at'])
    return page


def refresh_project_wiki_from_knowledge(project: Project):
    page = ensure_project_wiki(project)
    summaries = Summary.objects.filter(project=project, is_deleted=False).order_by('-created_at')[:3]
    knowledge = KnowledgeItem.objects.filter(project=project, is_deleted=False).order_by('-updated_at')[:8]
    lines = [f"# {project.canonical_name}", "", f"Домен: **{project.domain.name}**", ""]
    if project.description:
        lines += [project.description, ""]
    if summaries:
        lines += ["## Последние summaries", ""]
        for s in summaries:
            lines += [f"- {s.summary_text[:300]}"]
        lines += [""]
    if knowledge:
        lines += ["## Ключевые знания", ""]
        for k in knowledge:
            lines += [f"- **{k.title}** ({k.knowledge_type}): {k.body[:250]}"]
        lines += [""]
    content = "\n".join(lines).strip() + "\n"
    latest = page.revisions.order_by('-created_at').first()
    if not latest or latest.content_text != content:
        rev = WikiRevision.objects.create(
            wiki_page=page,
            content_text=content,
            author_type='system',
            source_summary_ids=list(summaries.values_list('id', flat=True)),
            source_knowledge_item_ids=list(knowledge.values_list('id', flat=True)),
        )
        page.current_revision = rev
        page.summary = project.description or page.summary
        page.save(update_fields=['current_revision', 'summary', 'updated_at'])
    return page
