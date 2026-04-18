from django.contrib import admin
from .models import ContextPack, ContextRule, ContextGuideline, ContextSkill, ContextSetting, SourceContextBinding, SourceAgentBinding

admin.site.register(ContextPack)
admin.site.register(ContextRule)
admin.site.register(ContextGuideline)
admin.site.register(ContextSkill)
admin.site.register(ContextSetting)
admin.site.register(SourceContextBinding)
admin.site.register(SourceAgentBinding)
