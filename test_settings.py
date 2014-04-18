import os

DEBUG = False
JS_DEBUG = False
ALLOWED_HOSTS = ['localhost']
DJANGO_LIVE_TEST_SERVER_ADDRESS = 'localhost:9090'
SELENIUM_SAUCE_VERSION = '2.41.0'
SELENIUM_TIMEOUT = 10

# This is a public repository!  Never commit real data for these!
SELENIUM_SAUCE_CONNECT_PATH = ''
SELENIUM_SAUCE_USERNAME = ''
SELENIUM_SAUCE_API_KEY = ''

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

USE_TZ = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

ROOT_PATH = os.path.abspath(os.path.dirname(__file__))
LOG_DIR = os.path.join(ROOT_PATH, 'log')

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(ROOT_PATH, 'sbo_selenium', 'static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'test_urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.staticfiles',
    'sbo_selenium',
    'django_nose',
)

try:
    import sbo_sphinx  # flake8: noqa
    INSTALLED_APPS += ('sbo_sphinx',)
except:
    pass

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# This is itself a UUID that is safe to pass to uuid.uuid3
SECRET_KEY = '8ff1e795-3e84-4ef2-b64d-c802b9d4469c'

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'simple': {
            'format': '[%(levelname)s] [%(asctime)s] [%(name)s]: %(message)s'
        },
    },
    'handlers': {
        # nose installs handlers that only show output for failed tests, but they
        # can omit errors in setup and teardown; log everything to file also
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'tests.log'),
            'formatter': 'simple',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'sbo_selenium': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'selenium': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

NOSE_ARGS = [
    '--nocapture',
    '--failure-detail',
    '--verbosity=3',
]
