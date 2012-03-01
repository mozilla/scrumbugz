from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

handler500 = 'scrum.views.server_error'

urlpatterns = patterns('',
    url(r'^$', 'scrum.views.home', name='scrum_home'),
    url(r'^projects/', include('scrum.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^500/$', handler500),
        (r'^404/$', handler404),
    )
