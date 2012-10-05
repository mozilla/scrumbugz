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
    'PROD_MODE',
)

# http://packages.python.org/Markdown/extensions/index.html
MARKDOWN_EXTENSIONS = [
    'fenced_code',
    'tables',
    'smart_strong',
    'sane_lists',
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
STATICFILES_DIRS = (
    str(PROJECT_DIR.child('static')),
)

JINGO_EXCLUDE_APPS = (
    'admin',
    'auth',
    'debug_toolbar',
    'floppyforms',
)

JINJA_CONFIG = {
    'extensions': (
        'jinja2.ext.do',
        'jinja2.ext.loopcontrols',
        'jinja2.ext.with_',
    ),
}

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'jingo.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
#    'johnny.middleware.LocalStoreClearMiddleware',
#    'johnny.middleware.QueryCacheMiddleware',
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
    'cronjobs',
    'bootstrap',
    'floppyforms',
    'djcelery',
    'scrum',
    'bugzilla',
    'south',
    'django_nose',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    'django.core.context_processors.tz',
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    "context_processors.context_settings",
    "scrum.context_processors.projects_and_teams",
)

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
    'get_bugmails': {
        'task': 'get_bugmails',
        'schedule': 30,
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
