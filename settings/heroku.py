from __future__ import absolute_import

import os

import dj_database_url

from .base import *


PROD_MODE = os.environ.get('PROD_MODE')

if PROD_MODE:
    ENFORCE_HOSTNAME = 'scrumbu.gs'
    ENABLE_GA = True
else:
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

# SENTRY
SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN:
    INSTALLED_APPS += ('raven.contrib.django',)

INSTALLED_APPS += ('storages',)

BUGMAIL_HOST = os.environ['BUGMAIL_HOST']
BUGMAIL_USER = os.environ['BUGMAIL_USER']
BUGMAIL_PASS = os.environ['BUGMAIL_PASS']
