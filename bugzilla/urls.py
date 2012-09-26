from django.conf.urls import patterns, url

from bugzilla.views import GetAllProductsView


urlpatterns = patterns('',
    url(r'products/$', GetAllProductsView.as_view()),
)
