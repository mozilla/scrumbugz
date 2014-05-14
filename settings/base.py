from datetime import timedelta

import djcelery
from unipath import Path


djcelery.setup_loader()
PROJECT_DIR = Path(__file__).absolute().ancestor(2)

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

BUGZILLA_BASE_URL = 'https://bugzilla.mozilla.org'
CACHE_BUGS_FOR = 4  # hours

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
MESSAGE_STORAGE = 'django.contrib.messages.storage.fallback.FallbackStorage'

CONTEXT_SETTINGS = (
    'CACHE_BUGS_FOR',
    'DEBUG',
    'ENABLE_GA',
    'BUGZILLA_SHOW_URL',
    'BUGZILLA_FILE_URL',
    'BUGZILLA_ATTACHMENT_URL',
    'PROD_MODE',
)

# http://packages.python.org/Markdown/extensions/index.html
MARKDOWN_EXTENSIONS = [
    'fenced_code',
    'tables',
    'smart_strong',
    'sane_lists',
    'headerid',
]

CACHES = {
    'default': {
        'BACKEND': 'scrum.cache_backend.PyLibMCCacheFix',
        'TIMEOUT': 500,
        'BINARY': True,
        'OPTIONS': {
            'tcp_nodelay': True,
            'ketama': True,
        },
    },
}
PYLIBMC_MIN_COMPRESS_LEN = 150 * 1024
CACHE_COUNT_TIMEOUT = 10  # seconds, not too long.

TIME_ZONE = 'America/New_York'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = False
USE_L10N = False
USE_TZ = True

MEDIA_ROOT = PROJECT_DIR.child('media')
MEDIA_URL = '/media/'

STATIC_ROOT = PROJECT_DIR.child('static_root')
STATIC_URL = '/static/'

JINGO_EXCLUDE_APPS = (
    'admin',
    'auth',
    'context_processors',  # needed for django tests
    'debug_toolbar',
    'floppyforms',
    'registration',  # needed for django tests
    'browserid',
)

JINJA_CONFIG = {
    'extensions': (
        'jinja2.ext.do',
        'jinja2.ext.loopcontrols',
        'jinja2.ext.with_',
        'pipeline.jinja2.ext.PipelineExtension',
    ),
}

STATICFILES_FINDERS = (
    # 'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'jingo.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'middleware.EnforceHostnameMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    PROJECT_DIR.child('templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'scrum',
    'cronjobs',
    'bootstrap',
    'floppyforms',
    'djcelery',
    'bugmail',
    'bugzilla',
    'south',
    'django_nose',
    'django_browserid',
    'pipeline',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'context_processors.context_settings',
    'scrum.context_processors.projects_and_teams',
)

AUTHENTICATION_BACKENDS = (
    'django_browserid.auth.BrowserIDBackend',
    'django.contrib.auth.backends.ModelBackend',
)
LOGIN_REDIRECT_URL = LOGIN_REDIRECT_URL_FAILURE = '/'
LOGIN_URL = LOGOUT_URL = '/'

BROWSERID_REQUEST_ARGS = {
    'siteName': 'ScrumBugs',
    'siteLogo': 'https://s3.amazonaws.com/scrumbugz-static/img/scrumbugs_favicon.png',
}

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_ARGS = [
    '--logging-clear-handlers',
]

# Celery
CELERY_DISABLE_RATE_LIMITS = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERY_TASK_RESULT_EXPIRES = 60
CELERY_TIMEZONE = 'UTC'
CELERYD_CONCURRENCY = 4
CELERYBEAT_SCHEDULE = {
    'get-bugmails': {
        'task': 'get_bugmails',
        'schedule': timedelta(minutes=5),
    },
    'clean-bugmails': {
        'task': 'clean_bugmail_log',
        'schedule': timedelta(days=5),
    },
}

BUG_OPEN_STATUSES = [
    'UNCONFIRMED',
    'CONFIRMED',
    'ASSIGNED',
    'REOPENED',
    'READY',
    'NEW',
]
BUG_CLOSED_STATUSES = [
    'RESOLVED',
    'VERIFIED',
    'CLOSED',
]

PIPELINE_JS = {
    'base': {
        'source_filenames': (
            'js/jquery-2.1.1.min.js',
            'js/jquery-migrate-1.2.1.min.js',
            'js/lodash-2.4.1.min.js',
            'js/bootstrap.min.js',
            'js/jquery.cookie.js',
            'js/site.js',
            'browserid/api.js',
            'browserid/browserid.js',
        ),
        'output_filename': 'js/base.min.js',
    },
    'forms': {
        'source_filenames': (
            'js/jquery.tools.min.js',
            'js/spin.min.js',
            'js/forms.js',
        ),
        'output_filename': 'js/forms.min.js',
    },
    'graphs': {
        'source_filenames': (
            'js/jquery.flot.min.js',
            'js/jquery.flot.pie.min.js',
            'js/jquery.flot.resize.min.js',
            'js/jquery.stupidtable.min.js',
            'js/sprint.js',
            'js/bugs_updated.js',
        ),
        'output_filename': 'js/graphs.min.js',
    },
    'bugs': {
        'source_filenames': (
            'js/jquery.timeago.js',
            'js/bugs_updated.js',
        ),
        'output_filename': 'js/bugs.min.js',
    },
    'teams': {
        'source_filenames': (
            'js/jquery.stupidtable.min.js',
            'js/project.js',
            'js/bugs_updated.js',
        ),
        'output_filename': 'js/teams.min.js',
    },
    'bugs_management': {
        'source_filenames': (
            'js/sprint_bug_management.js',
        ),
        'output_filename': 'js/bugs.mgmnt.min.js',
    }
}

PIPELINE_CSS = {
    'base': {
        'source_filenames': (
            'css/bootstrap.css',
            'css/site.css',
            'css/bootstrap-responsive.css',
            'browserid/persona-buttons.css',
        ),
        'output_filename': 'css/base.min.css',
    }
}

PIPELINE_DISABLE_WRAPPER = True
