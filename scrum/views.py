from django import http
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.template import loader
from django.template.context import Context
from django.utils import simplejson as json
from django.views.generic import (CreateView, DeleteView, DetailView,
                                  ListView, TemplateView, UpdateView)

from scrum.forms import (CreateProjectForm, CreateSprintForm, BZURLForm,
                         ProjectForm, SprintBugsForm, SprintForm)
from scrum.models import BugzillaURL, BZError, Project, Sprint


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
        if not hasattr(self, 'target_obj'):
            pslug = self.kwargs.get('pslug')
            sslug = self.kwargs.get('sslug')
            if sslug:
                self.target_obj = get_object_or_404(Sprint,
                                                    project__slug=pslug,
                                                    slug=sslug)
                self.target_obj_type = 'sprint'
            else:
                self.target_obj = get_object_or_404(Project, slug=pslug)
                self.target_obj_type = 'project'
        return self.target_obj, self.target_obj_type


class BugsDataMixin(object):
    def get_context_data(self, **kwargs):
        context = super(BugsDataMixin, self).get_context_data(**kwargs)
        bugs_kwargs = {}
        # clear cache if requested
        if self.request.META.get('HTTP_CACHE_CONTROL') == 'no-cache':
            bugs_kwargs['refresh'] = True
        if 'all' in self.request.GET:
            bugs_kwargs['scrum_only'] = False
        try:
            context['bugs'] = self.object.get_bugs(**bugs_kwargs)
            context['bugs_data'] = self.object.get_graph_bug_data()
            context['bugs_data_json'] = json.dumps(context['bugs_data'])
            context['bzerror'] = False
        except BZError:
            context['bzerror'] = True
        return context


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


class ProjectView(BugsDataMixin, ProjectsMixin, DetailView):
    template_name = 'scrum/project.html'


class ListProjectsView(ProjectsMixin, ListView):
    template_name = 'scrum/projects_list.html'
    context_object_name = 'projects'


class CreateProjectView(ProjectsMixin, ProtectedCreateView):
    model = Project
    form_class = CreateProjectForm
    template_name = 'scrum/project_form.html'


class EditProjectView(ProjectsMixin, ProtectedUpdateView):
    form_class = ProjectForm
    template_name = 'scrum/project_form.html'


class CreateSprintView(ProjectsMixin, ProtectedCreateView):
    model = Sprint
    form_class = CreateSprintForm
    template_name = 'scrum/sprint_form.html'

    def get_context_data(self, **kwargs):
        context = super(CreateSprintView, self).get_context_data(**kwargs)
        context['project'] = self.project
        return context

    def get_initial(self):
        self.project = self.get_project_or_sprint()[0]
        return super(CreateSprintView, self).get_initial()

    def form_valid(self, form):
        sprint = form.save(commit=False)
        sprint.project = self.project
        sprint.save()
        return redirect(sprint)


class SprintMixin(ProjectOrSprintMixin):
    model = Sprint
    context_object_name = 'sprint'

    def get_object(self, queryset=None):
        pslug = self.kwargs.get('pslug')
        sslug = self.kwargs.get('sslug')
        sprint = get_object_or_404(Sprint, project__slug=pslug, slug=sslug)
        self.project = sprint.project
        return sprint


class SprintView(BugsDataMixin, SprintMixin, DetailView):
    template_name = 'scrum/sprint.html'

    def get_context_data(self, **kwargs):
        context = super(SprintView, self).get_context_data(**kwargs)
        context['project'] = self.project
        if not context['bzerror']:
            context['bugs_data'].update(self.object.get_burndown_data())
            context['bugs_data_json'] = json.dumps(context['bugs_data'])
        return context


class EditSprintView(SprintMixin, ProjectsMixin, ProtectedUpdateView):
    form_class = SprintForm
    template_name = 'scrum/sprint_form.html'


class ManageSprintBugsView(SprintMixin, ProjectsMixin, ProtectedUpdateView):
    form_class = SprintBugsForm
    template_name = 'scrum/sprint_bugs.html'


class CreateBZUrlView(ProjectOrSprintMixin, ProtectedCreateView):
    model = BugzillaURL
    form_class = BZURLForm
    template_name = 'scrum/bzurl_list.html'

    def get(self, request, *args, **kwargs):
        if not request.is_ajax():
            return HttpResponseForbidden()
        return super(CreateBZUrlView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        obj, objtype = self.get_project_or_sprint()
        kwargs['target_obj'] = obj
        kwargs['target_obj_type'] = objtype
        kwargs['bzurls'] = obj.urls.all()
        return super(CreateBZUrlView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        url = form.save(commit=False)
        url.set_project_or_sprint(*self.get_project_or_sprint())
        url.save()
        if self.request.is_ajax():
            return self.render_to_response(self.get_context_data(form=form))
        else:
            return redirect(self.target_obj.get_edit_url())

    def form_invalid(self, form):
        if self.request.is_ajax():
            return HttpResponse(json.dumps(form.errors), status=400)
        else:
            target_obj = self.get_project_or_sprint()[0]
            messages.error(self.request, form['url'].errors[0])
            return redirect(target_obj.get_edit_url())


class DeleteBZUlrView(ProtectedDeleteView):
    model = BugzillaURL
    success_url = '/'

    def __init__(self):
        # remove GET from allowed methods to throw 405
        # copy list or modify global copy
        self.http_method_names = self.http_method_names[:]
        self.http_method_names.remove('get')
        super(DeleteBZUlrView, self).__init__()

    def delete(self, request, *args, **kwargs):
        if request.is_ajax():
            super(DeleteBZUlrView, self).delete(request, *args, **kwargs)
            return HttpResponse(status=204)
        return HttpResponseForbidden()


def server_error(request):
    context = {
        'STATIC_URL': getattr(settings, 'STATIC_URL', '/static/'),
        'ENABLE_GA': getattr(settings, 'ENABLE_GA', False),
    }
    t = loader.get_template('500.html')
    return http.HttpResponseServerError(t.render(Context(context)))
