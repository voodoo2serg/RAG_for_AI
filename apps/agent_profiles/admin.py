from django.contrib import admin
from .models import AgentProfile, AgentProfileRule, AgentProfilePermission

admin.site.register(AgentProfile)
admin.site.register(AgentProfileRule)
admin.site.register(AgentProfilePermission)
