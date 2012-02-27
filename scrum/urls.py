from django.conf.urls.defaults import patterns, url

from scrum.views import (ListProjectsView,
                         ProjectView, SprintView)

urlpatterns = patterns('',
    url(r'^$', ListProjectsView.as_view(), name='scrum_projects_list'),
    url(r'^(?P<pslug>[-\w]+)/$', ProjectView.as_view(), name='scrum_project'),
    url(r'^(?P<pslug>[-\w]+)/(?P<sslug>[-\w\.]+)/$', SprintView.as_view(),
        name='scrum_sprint'),
)
