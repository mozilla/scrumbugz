from __future__ import absolute_import
import os

if 'HEROKU' in os.environ:
    from .heroku import *
elif 'TRAVIS' in os.environ:
    from .travis import *
else:
    try:
        from .local import *
    except ImportError:
        from .base import *

DEFAULT_LOG_LEVEL = 'DEBUG' if DEBUG else 'INFO'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'formatters': {
        'verbose': {
            'format': ('%(levelname)s %(asctime)s %(module)s %(process)d '
                       '%(thread)d %(message)s'),
        },
        'simple': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s',
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
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        '': {
            'handlers': ['console'],
            'level': os.environ.get('SCRUM_LOG_LEVEL', DEFAULT_LOG_LEVEL),
            'propagate': True,
        },
    }
}

if 'SENTRY_DSN' in locals():
    LOGGING['handlers']['sentry'] = {
        'level': 'ERROR',
        'class': 'raven.handlers.logging.SentryHandler',
        'dsn': SENTRY_DSN,
    }
    LOGGING['loggers']['']['handlers'].append('sentry')
