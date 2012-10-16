from django.conf import settings
from django.conf.urls import *
from django.contrib import admin
from django.views.generic import TemplateView

admin.autodiscover()

handler500 = 'scrum.views.server_error'

urlpatterns = patterns('',
    url(r'^logout/$', 'django.contrib.auth.views.logout', name='logout'),
    url(r'^browserid/', include('django_browserid.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^help/', TemplateView.as_view(template_name='help.html'),
        name='help'),
    url(r'^$', 'scrum.views.home', name='scrum_home'),
    url(r'^bugzilla/', include('bugzilla.urls')),
    url(r'^bugmail/', include('bugmail.urls')),
    url(r'', include('scrum.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^500/$', handler500),
        (r'^404/$', handler404),
    )
