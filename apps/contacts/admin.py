from django.contrib import admin
from .models import Contact

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("canonical_name", "telegram_handle", "role", "organization")
    search_fields = ("canonical_name", "telegram_handle", "role", "organization")
