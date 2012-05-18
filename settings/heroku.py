from __future__ import absolute_import
import os
import urlparse

from .base import *


urlparse.uses_netloc.append('postgres')
url = urlparse.urlparse(os.environ['DATABASE_URL'])

ENFORCE_HOSTNAME = 'scrumbu.gs'
ENABLE_GA = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': url.path[1:],
        'USER': url.username,
        'PASSWORD': url.password,
        'HOST': url.hostname,
        'PORT': url.port,
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django_pylibmc.memcached.PyLibMCCache'
    }
}

SECRET_KEY = os.environ['SECRET_KEY']
STATIC_URL = '//s3.amazonaws.com/%s/' % AWS_STORAGE_BUCKET_NAME
ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

# SENTRY
SENTRY_DSN = os.environ['SENTRY_DSN']
INSTALLED_APPS += ('raven.contrib.django',)
