from django.contrib import admin

from scrum.models import Project, Sprint, Team


admin.site.register(Project)
admin.site.register(Sprint)
admin.site.register(Team)
