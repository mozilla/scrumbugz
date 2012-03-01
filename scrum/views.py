from operator import itemgetter
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, UpdateView, TemplateView

from scrum.forms import SprintForm, ProjectForm
from scrum.models import Project, Sprint, parse_bz_url

try:
    import simplejson as json
except ImportError:
    import json


class ProtectedCreateView(CreateView):
    def post(self, request, *args, **kwargs):
        @permission_required('%s.add_%s' % (self.model._meta.app_label,
                                            self.model._meta.module_name))
        def wrap(request, *args, **kwargs):
            return super(ProtectedCreateView, self).post(request,
                                                         *args, **kwargs)
        return wrap(request, *args, **kwargs)


class ProtectedUpdateView(UpdateView):
    def post(self, request, *args, **kwargs):
        @permission_required('%s.change_%s' % (self.model._meta.app_label,
                                               self.model._meta.module_name))
        def wrap(request, *args, **kwargs):
            return super(ProtectedUpdateView, self).post(request,
                                                         *args, **kwargs)
        return wrap(request, *args, **kwargs)


class ProjectsMixin(object):
    def get_context_data(self, **kwargs):
        kwargs['projects'] = Project.objects.all()
        if hasattr(self, 'object'):
            kwargs['object'] = self.object
        if 'pslug' in self.kwargs:
            kwargs['project'] = get_object_or_404(Project,
                                                  slug=self.kwargs['pslug'])
        return kwargs


class HomeView(TemplateView):
    template_name = 'scrum/home.html'
home = HomeView.as_view()


class ProjectView(ProjectsMixin, ProtectedCreateView):
    model = Sprint
    form_class = SprintForm
    template_name = 'scrum/project.html'

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        sprint = form.save(commit=False)
        sprint.project = get_object_or_404(Project, slug=self.kwargs['pslug'])
        sprint.save()
        self.object = sprint
        return redirect(self.get_success_url())


class ListProjectsView(ProjectsMixin, ProtectedCreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'scrum/projects_list.html'

    def get_success_url(self):
        return self.object.get_absolute_url()


class SprintView(ProjectsMixin, ProtectedUpdateView):
    model = Sprint
    form_class = SprintForm
    template_name = 'scrum/sprint.html'

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_object(self, queryset=None):
        pslug = self.kwargs.get('pslug')
        sslug = self.kwargs.get('sslug')
        return get_object_or_404(Sprint, project__slug=pslug, slug=sslug)

    def process_bug_data(self):
        data = self.object.get_bugs_data()
        for item in ['users', 'components', 'status', 'basic_status']:
            data[item] = [{'label': k, 'data': v} for k, v in
                          sorted(data[item].iteritems(),
                                 key=itemgetter(1),
                                 reverse=True)]
        return data

    def get_context_data(self, **kwargs):
        context = super(SprintView, self).get_context_data(**kwargs)
        # clear cache if requested
        if self.request.META.get('HTTP_CACHE_CONTROL') == 'no-cache':
            self.object.refresh_bugs()
        context['sprint'] = self.object
        context['bugs'] = self.object.get_bugs()
        context['bugs_data'] = self.process_bug_data()
        context['bugs_data_json'] = json.dumps(context['bugs_data'])
        return context
