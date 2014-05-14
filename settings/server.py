from __future__ import absolute_import

import os

import dj_database_url

from .base import *  # noqa

DEBUG = False
ENABLE_GA = True
SITE_URL = 'https://scrumbu.gs'
ALLOWED_HOSTS = ['scrumbu.gs', 'localhost']
PROD_MODE = True
BROWSERID_AUDIENCES = [
    'https://scrumbu.gs',
]

DATABASES = {'default': dj_database_url.config()}
CACHES['default']['LOCATION'] = [
    'amy:11211',
    'fry:11211',
]

SECRET_KEY = os.getenv('SECRET_KEY')

SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

# Static media
STATICFILES_STORAGE = 'scrum.storage.GzipManifestPipelineStorage'
BUGMAIL_API_KEY = os.getenv('BUGMAIL_API_KEY')
STATIC_URL = os.getenv('STATIC_URL')

# Celery
BROKER_URL = os.getenv('BROKER_URL')
CELERY_RESULT_BACKEND = BROKER_URL

# SENTRY
SENTRY_DSN = os.getenv('SENTRY_DSN')
MORE_APPS = ['raven.contrib.django']
SENTRY_AUTO_LOG_STACKS = True

INSTALLED_APPS += tuple(MORE_APPS)

if os.environ.get('BUGZILLA_BASE_URL'):
    BUGZILLA_BASE_URL = os.environ['BUGZILLA_BASE_URL']
    BUG_OPEN_STATUSES = [
        'UNCONFIRMED',
        'CONFIRMED',
        'IN_PROGRESS',
    ]
    BUG_CLOSED_STATUSES = [
        'RESOLVED',
        'VERIFIED',
    ]
