from operator import itemgetter

from django import http
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.template import loader
from django.template.context import Context
from django.views.generic import (CreateView, DeleteView, DetailView,
                                  ListView, TemplateView, UpdateView)

from scrum.forms import BZURLForm, ProjectForm, SprintForm
from scrum.models import BugzillaURL, BZError, Project, Sprint, parse_bz_url

try:
    import simplejson as json
except ImportError:
    import json


class ProtectedCreateView(CreateView):
    def dispatch(self, request, *args, **kwargs):
        @permission_required('%s.add_%s' % (self.model._meta.app_label,
                                            self.model._meta.module_name))
        def wrap(request, *args, **kwargs):
            return super(ProtectedCreateView, self).dispatch(request,
                                                             *args, **kwargs)
        return wrap(request, *args, **kwargs)


class ProtectedUpdateView(UpdateView):
    def dispatch(self, request, *args, **kwargs):
        @permission_required('%s.change_%s' % (self.model._meta.app_label,
                                               self.model._meta.module_name))
        def wrap(request, *args, **kwargs):
            return super(ProtectedUpdateView, self).dispatch(request,
                                                             *args, **kwargs)
        return wrap(request, *args, **kwargs)


class ProtectedDeleteView(DeleteView):
    def dispatch(self, request, *args, **kwargs):
        @permission_required('%s.delete_%s' % (self.model._meta.app_label,
                                               self.model._meta.module_name))
        def wrap(request, *args, **kwargs):
            return super(ProtectedDeleteView, self).dispatch(request,
                                                             *args, **kwargs)
        return wrap(request, *args, **kwargs)


class ProjectOrSprintMixin(object):
    def get_project_or_sprint(self):
        """Returns a project or sprint object based on the url kwargs."""
        if (not hasattr(self, 'target_obj') or
            not hasattr(self, 'target_obj_type')):
            pslug = self.kwargs.get('pslug')
            sslug = self.kwargs.get('sslug')
            if sslug:
                self.target_obj = get_object_or_404(Sprint, project__slug=pslug, slug=sslug)
                self.target_obj_type = 'sprint'
            else:
                self.target_obj = get_object_or_404(Project, slug=pslug)
                self.target_obj_type = 'project'
        return self.target_obj, self.target_obj_type


class ProjectsMixin(ProjectOrSprintMixin):
    model = Project
    slug_url_kwarg = 'pslug'

    def get_context_data(self, **kwargs):
        context = super(ProjectsMixin, self).get_context_data(**kwargs)
        context['projects'] = Project.objects.all()
        if hasattr(self, 'project'):
            context['project'] = self.project
        return context


class HomeView(TemplateView):
    template_name = 'scrum/home.html'
home = HomeView.as_view()


class ProjectView(ProjectsMixin, DetailView):
    template_name = 'scrum/project.html'


class ListProjectsView(ProjectsMixin, ListView):
    template_name = 'scrum/projects_list.html'
    context_object_name = 'projects'


class CreateProjectView(ProjectsMixin, ProtectedCreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'scrum/project_form.html'


class EditProjectView(ProjectsMixin, ProtectedUpdateView):
    form_class = ProjectForm
    template_name = 'scrum/project_form.html'


class CreateSprintView(ProjectsMixin, ProtectedCreateView):
    model = Sprint
    form_class = SprintForm
    template_name = 'scrum/sprint_form.html'

    def get_context_data(self, **kwargs):
        context = super(CreateSprintView, self).get_context_data(**kwargs)
        context['project'] = self.project
        return context

    def get_initial(self):
        self.project = self.get_project_or_sprint()[0]
        return {
            'project': self.project,
        }


class SprintMixin(ProjectOrSprintMixin):
    model = Sprint
    context_object_name = 'sprint'

    def get_object(self, queryset=None):
        pslug = self.kwargs.get('pslug')
        sslug = self.kwargs.get('sslug')
        sprint = get_object_or_404(Sprint, project__slug=pslug, slug=sslug)
        self.project = sprint.project
        return sprint


class SprintView(SprintMixin, DetailView):
    template_name = 'scrum/sprint.html'

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
        refresh = False
        if self.request.META.get('HTTP_CACHE_CONTROL') == 'no-cache':
            refresh = True
        try:
            context['project'] = self.project
            context['bugs'] = self.object.get_bugs(refresh)
            context['bugs_data'] = self.process_bug_data()
            context['bugs_data_json'] = json.dumps(context['bugs_data'])
            context['bzerror'] = False
        except BZError:
            context['bzerror'] = True
        return context


class EditSprintView(SprintMixin, ProjectsMixin, ProtectedUpdateView):
    form_class = SprintForm
    template_name = 'scrum/sprint_form.html'


class CreateBZUrlView(ProjectOrSprintMixin, ProtectedCreateView):
    model = BugzillaURL
    form_class = BZURLForm
    template_name = 'scrum/bzurl_list.html'

    def get(self, request, *args, **kwargs):
        if not request.is_ajax():
            return HttpResponseForbidden()
        return super(CreateBZUrlView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not request.is_ajax():
            return HttpResponseForbidden()
        return super(CreateBZUrlView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        obj, objtype = self.get_project_or_sprint()
        kwargs['target_obj'] = obj
        kwargs['target_obj_type'] = objtype
        return super(CreateBZUrlView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        url = form.save(commit=False)
        url.set_project_or_sprint(*self.get_project_or_sprint())
        url.save()
        return HttpResponse(status=204)

    def form_invalid(self, form):
        return HttpResponse(json.dumps(form.errors), status=400)


def server_error(request):
    context = {
        'STATIC_URL': getattr(settings, 'STATIC_URL', '/static/'),
        'ENABLE_GA': getattr(settings, 'ENABLE_GA', False),
    }
    t = loader.get_template('500.html')
    return http.HttpResponseServerError(t.render(Context(context)))
