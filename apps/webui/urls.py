from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("explorer/", views.explorer, name="explorer"),
    path("projects/<int:project_id>/", views.project_detail, name="project_detail"),
    path("domains/<int:domain_id>/", views.domain_detail, name="domain_detail"),
    path("wiki/<int:page_id>/", views.wiki_page_detail, name="wiki_page_detail"),
    path("messages/", views.message_viewer, name="message_viewer"),
    path("rules/<str:scope_type>/<int:scope_id>/", views.rule_viewer, name="rule_viewer"),
    path("retrieval/<int:session_id>/", views.retrieval_session_detail, name="retrieval_session_detail"),
    path("sources/", views.source_list, name="source_list"),
    path("sources/<int:source_id>/", views.source_detail, name="source_detail"),
    path("rag-corpus/", views.rag_corpus_viewer, name="rag_corpus_viewer"),
    path("retrieval/diagnostics/", views.retrieval_diagnostics, name="retrieval_diagnostics"),
    path("review-queue/", views.review_queue, name="review_queue"),
    path("evaluation-center/", views.evaluation_center, name="evaluation_center"),
]
