from django.conf.urls import patterns, url

from bugmail.views import BugmailStatsView


urlpatterns = patterns('',
    url(r'^stats/$', BugmailStatsView.as_view(),
        name='scrum_bugmail_stats'),
)
