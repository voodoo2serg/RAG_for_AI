from django.contrib import admin
from .models import WikiSpace, WikiPage, WikiRevision, WikiLink
admin.site.register(WikiSpace)
admin.site.register(WikiPage)
admin.site.register(WikiRevision)
admin.site.register(WikiLink)
