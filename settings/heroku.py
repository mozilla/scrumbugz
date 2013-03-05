from __future__ import absolute_import

import os

import dj_database_url

from .base import *


PROD_MODE = os.environ.get('PROD_MODE')

if PROD_MODE:
    ENFORCE_HOSTNAME = 'scrumbu.gs'
    ENABLE_GA = True
    SITE_URL = 'http://scrumbu.gs'
    ALLOWED_HOSTS = ['scrumbu.gs']
else:
    SITE_URL = 'http://scrumbugz-dev.herokuapp.com'
    ALLOWED_HOSTS = ['scrumbugz-dev.herokuapp.com']

ADMINS = (
    ('Paul', 'pmac@mozilla.com'),
)
MANAGERS = ADMINS

DATABASES = {'default': dj_database_url.config()}

SECRET_KEY = os.environ['SECRET_KEY']

# Static media
STATICFILES_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
DEFAULT_FILE_STORAGE = STATICFILES_STORAGE
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']
STATIC_URL = '//s3.amazonaws.com/%s/' % AWS_STORAGE_BUCKET_NAME

MORE_APPS = ['storages']

# Celery
BROKER_URL = os.environ['REDISTOGO_URL']
CELERY_RESULT_BACKEND = BROKER_URL

# SENTRY
SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN:
    MORE_APPS.append('raven.contrib.django',)
    SENTRY_AUTO_LOG_STACKS = True

INSTALLED_APPS += tuple(MORE_APPS)

if os.environ.get('MEMCACHIER_SERVERS'):
    os.environ['MEMCACHE_SERVERS'] = os.environ.get('MEMCACHIER_SERVERS')
    os.environ['MEMCACHE_USERNAME'] = os.environ.get('MEMCACHIER_USERNAME')
    os.environ['MEMCACHE_PASSWORD'] = os.environ.get('MEMCACHIER_PASSWORD')

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
