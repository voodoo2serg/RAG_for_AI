from django.core.management.base import BaseCommand
from apps.domains_projects.models import Project
from apps.threads.services import ThreadReconstructionService
from apps.retrieval.services import rebuild_rag_corpus
from apps.wiki.services import refresh_project_wiki_from_knowledge


class Command(BaseCommand):
    help = "Rebuild threads, refresh wiki and rebuild RAG corpus"

    def add_arguments(self, parser):
        parser.add_argument('--project-id', type=int, default=None)

    def handle(self, *args, **kwargs):
        service = ThreadReconstructionService()
        total = 0
        projects = Project.objects.filter(is_deleted=False)
        if kwargs.get('project_id'):
            projects = projects.filter(id=kwargs['project_id'])
        for project in projects:
            total += service.rebuild_for_project(project.id)
            refresh_project_wiki_from_knowledge(project)
        corpus_count = rebuild_rag_corpus()
        self.stdout.write(self.style.SUCCESS(f"Rebuilt {total} thread groups and refreshed {corpus_count} corpus entries"))
