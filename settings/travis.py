from __future__ import absolute_import
from .base import *


DEBUG = True
TEMPLATE_DEBUG = DEBUG

SECRET_KEY = "shhhhhh"

DATABASES = {
     'default': {
         'ENGINE': 'django.db.backends.sqlite3',
         'NAME': PROJECT_DIR.child('scrumbugs.db'),
     }
}
# required for sqlite
USE_TZ = True

CACHES = {
     'default': {
         'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
     },
}

SOUTH_TESTS_MIGRATE = False
