from scrum.models import Project, Team


def projects_and_teams(request):
    return {
        'projects': Project.objects.all(),
        'teams': Team.objects.all(),
    }
