import os

DEBUG = False
JS_DEBUG = False

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

INSTALLED_APPS = (
    'sbo_selenium',
    'django_nose',
)

try:
    import sbo_sphinx
    INSTALLED_APPS += ('sbo_sphinx',)
except:
    pass

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# This is itself a UUID that is safe to pass to uuid.uuid3
SECRET_KEY = '8ff1e795-3e84-4ef2-b64d-c802b9d4469c'

# Sphinx documentation settings
ROOT_PATH = os.path.abspath(os.path.dirname(__file__))
SPHINX_EXTERNAL_FILES = ['README.rst']
SPHINX_INPUT_DIR = 'docs'
SPHINX_OUTPUT_DIR = 'docs/_build'
SPHINX_MASTER_DOC = 'index'
SPHINX_PROJECT_NAME = 'sbo-selenium'
SPHINX_PROJECT_VERSION = '0.1'
SPHINX_PYTHON_EXCLUDE = [
    'dist',
    'storage',
    've',
    'manage.py',
    'setup.py',
    'test_settings.py',
]

NOSE_ARGS = [
    '--nocapture',
    '--failure-detail',
    '--verbosity=3',
]
