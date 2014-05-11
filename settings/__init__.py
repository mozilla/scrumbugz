# flake8: noqa

from __future__ import absolute_import

import os
import sys

if 'SERVER_ENV' in os.environ:
    from .server import *
elif 'TRAVIS' in os.environ:
    from .travis import *
else:
    try:
        from .local import *
    except ImportError:
        from .base import *

BUGZILLA_ALL_URLS = {
    'BUGZILLA_API_URL': '/xmlrpc.cgi',
    'BUGZILLA_SHOW_URL': '/show_bug.cgi?',
    'BUGZILLA_FILE_URL': '/enter_bug.cgi?',
    'BUGZILLA_SEARCH_URL': '/buglist.cgi?',
    'BUGZILLA_ATTACHMENT_URL': '/attachment.cgi?',
}
for attrname, relurl in BUGZILLA_ALL_URLS.items():
    if attrname not in locals():
        globals()[attrname] = BUGZILLA_BASE_URL + relurl

DEFAULT_LOG_LEVEL = 'DEBUG' if DEBUG else 'INFO'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'formatters': {
        'verbose': {
            'format': ('%(levelname)s %(asctime)s %(name)s %(process)d '
                       '%(thread)d %(message)s'),
        },
        'simple': {
            'format': '%(levelname)s %(asctime)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': sys.stdout,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': False,
            'level': 'DEBUG',
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django_browserid': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'nose': {
            'handlers': ['null'],
            'level': 'DEBUG',
            'propagate': False,
        },
        '': {
            'handlers': ['console'],
            'level': os.environ.get('SCRUM_LOG_LEVEL', DEFAULT_LOG_LEVEL),
            'propagate': True,
        },
    }
}

if 'SENTRY_DSN' in locals() and SENTRY_DSN:
    LOGGING['handlers']['sentry'] = {
        'level': 'ERROR',
        'class': 'raven.handlers.logging.SentryHandler',
        'dsn': SENTRY_DSN,
    }
    LOGGING['loggers']['']['handlers'].append('sentry')
