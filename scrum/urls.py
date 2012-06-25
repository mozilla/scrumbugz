from django.conf.urls.defaults import patterns, url

from scrum.views import (CreateBZUrlView, CreateProjectView, CreateSprintView,
                         DeleteBZUlrView, EditProjectView, EditSprintView,
                         ListProjectsView, ProjectView, SprintView)


urlpatterns = patterns('',
    url(r'^$', ListProjectsView.as_view(), name='scrum_projects_list'),
    url(r'^new/$', CreateProjectView.as_view(), name='scrum_project_new'),
    url(r'^url/(?P<pk>\d+)/delete/$', DeleteBZUlrView.as_view(),
        name='scrum_url_delete'),
    url(r'^(?P<pslug>[-\w]+)/$', ProjectView.as_view(), name='scrum_project'),
    url(r'^(?P<pslug>[-\w]+)/new/$', CreateSprintView.as_view(),
        name='scrum_sprint_new'),
    url(r'^(?P<pslug>[-\w]+)/edit/$', EditProjectView.as_view(),
        name='scrum_project_edit'),
    url(r'^(?P<pslug>[-\w]+)/urls/$', CreateBZUrlView.as_view(),
        name='scrum_project_urls'),
    url(r'^(?P<pslug>[-\w]+)/(?P<sslug>[-\w\.]+)/$', SprintView.as_view(),
        name='scrum_sprint'),
    url(r'^(?P<pslug>[-\w]+)/(?P<sslug>[-\w\.]+)/edit/$',
        EditSprintView.as_view(), name='scrum_sprint_edit'),
    url(r'^(?P<pslug>[-\w]+)/(?P<sslug>[-\w\.]+)/urls/$',
        CreateBZUrlView.as_view(), name='scrum_sprint_urls'),
)
