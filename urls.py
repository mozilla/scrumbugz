from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'scrum.views.home', name='scrum_home'),
    url(r'^projects/', include('scrum.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
