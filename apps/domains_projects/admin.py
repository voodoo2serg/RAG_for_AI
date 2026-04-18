from django.contrib import admin
from .models import Domain, Project, ProjectRelation

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "display_order", "is_active")
    search_fields = ("name", "slug")

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("canonical_name", "domain", "parent_project", "status", "importance_score")
    list_filter = ("domain", "status")
    search_fields = ("canonical_name", "slug", "description")

@admin.register(ProjectRelation)
class ProjectRelationAdmin(admin.ModelAdmin):
    list_display = ("source_project", "relation_type", "target_project", "confidence")
