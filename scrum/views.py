from operator import itemgetter
from django.core.urlresolvers import reverse
from django.http import QueryDict
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import (CreateView, FormView, DetailView, ListView,
                                  TemplateView)
from django.views.generic.edit import UpdateView

from scrum.forms import BZUrlForm, SprintForm
from scrum.models import Project, Sprint, parse_bz_url

try:
    import simplejson as json
except ImportError:
    import json


class ProjectsMixin(object):
    def get_context_data(self, **kwargs):
        kwargs['projects'] = Project.objects.all()
        if 'pslug' in self.kwargs:
            kwargs['project'] = get_object_or_404(Project,
                                                  slug=self.kwargs['pslug'])
        return kwargs


class HomeView(ProjectsMixin, TemplateView):
    template_name = 'scrum/home.html'
home = HomeView.as_view()


class ProjectView(ProjectsMixin, FormView):
    form_class = BZUrlForm
    template_name = 'scrum/project.html'

    def form_valid(self, form):
        url = form.cleaned_data['bz_url']
        data = parse_bz_url(url)
        url_data = QueryDict('', mutable=True)
        if 'target_milestone' in data:
            url_data['slug'] = data['target_milestone']
            if 'product' in data:
                url_data['name'] = '{0} - {1}'.format(data['product'],
                                                      data['target_milestone'])
        url_data['bz_url'] = url
        return redirect(reverse('scrum_sprint_new',
                                kwargs={'pslug': self.kwargs['pslug']})
                        + '?' + url_data.urlencode())


class CreateSprintView(ProjectsMixin, CreateView):
    model = Sprint
    form_class = SprintForm
    template_name = 'scrum/sprint_form.html'
    allowed_initial = [
        'name',
        'slug',
        'bz_url',
    ]

    def get_initial(self):
        return dict((k, v) for k, v in self.request.GET.items()
                    if k in self.allowed_initial)

    def get_success_url(self):
        kwargs = self.kwargs.copy()
        kwargs['sslug'] = self.object.slug
        return reverse('scrum_sprint', kwargs=kwargs)

    def form_valid(self, form):
        sprint = form.save(commit=False)
        sprint.project = get_object_or_404(Project, slug=self.kwargs['pslug'])
        sprint.save()
        self.object = sprint
        return redirect(self.get_success_url())


class ListProjectsView(ListView):
    model = Project
    template_name = 'scrum/projects_list.html'
    context_object_name = 'projects'


class SprintView(ProjectsMixin, DetailView):
    model = Sprint
    template_name = 'scrum/sprint.html'

    def get_object(self, queryset=None):
        pslug = self.kwargs.get('pslug')
        sslug = self.kwargs.get('sslug')
        return get_object_or_404(Sprint, project__slug=pslug, slug=sslug)

    def process_bug_data(self):
        data = self.object.get_bugs_data()
        for item in ['users', 'components', 'status', 'basic_status']:
            data[item] = [{'label': k, 'data': v} for k, v in
                          sorted(data[item].iteritems(), key=itemgetter(1))]
        return data


    def get_context_data(self, **kwargs):
        context = super(SprintView, self).get_context_data(**kwargs)
        context['sprint'] = self.object
        context['bugs'] = self.object.get_bugs()
        context['bugs_data'] = self.process_bug_data()
        context['bugs_data_json'] = json.dumps(context['bugs_data'])
        return context
