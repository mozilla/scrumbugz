import os
from unipath import Path


PROJECT_DIR = Path(__file__).absolute().ancestor(2)

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

BZ_API_URL = 'https://api-dev.bugzilla.mozilla.org/latest/'
BZ_SHOW_URL = 'https://bugzilla.mozilla.org/show_bug.cgi?'
BZ_FILE_URL = 'https://bugzilla.mozilla.org/enter_bug.cgi?'
CACHE_BUGS_FOR = 2  # hours

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

CONTEXT_SETTINGS = (
    'CACHE_BUGS_FOR',
    'DEBUG',
    'ENABLE_GA',
    'BZ_SHOW_URL',
    'BZ_FILE_URL',
)

TIME_ZONE = 'America/New_York'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = False
USE_L10N = False

MEDIA_ROOT = PROJECT_DIR.child('media')
MEDIA_URL = '/media/'

STATIC_ROOT = PROJECT_DIR.child('static_root')
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    str(PROJECT_DIR.child('static')),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
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
    'bootstrapform',
    'floppyforms',
    'scrum',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    "context_processors.context_settings",
)

