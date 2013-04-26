from django.conf import settings as django_settings


class LazySettings(object):

    @property
    def DJANGO_LIVE_TEST_SERVER_ADDRESS(self):
        """Address at which to run the test server"""
        return getattr(django_settings, 'DJANGO_LIVE_TEST_SERVER_ADDRESS',
                       'localhost:9001')

    @property
    def SELENIUM_DEFAULT_BROWSER(self):
        """Default browser to use when running tests"""
        return getattr(django_settings, 'SELENIUM_DEFAULT_BROWSER', ['chrome'])

    @property
    def SELENIUM_DEFAULT_TESTS(self):
        """Default Selenium test package to run"""
        return getattr(django_settings, 'SELENIUM_DEFAULT_TESTS', [])

    @property
    def SELENIUM_LOG_FILE(self):
        """Log file for Selenium test logging, errors, etc."""
        return getattr(django_settings, 'SELENIUM_LOG_FILE', '')

    @property
    def SELENIUM_POLL_FREQUENCY(self):
        """Default operation retry frequency"""
        return getattr(django_settings, 'SELENIUM_POLL_FREQUENCY', 0.5)

    @property
    def SELENIUM_SCREENSHOT_DIR(self):
        """Directory in which to store screenshots"""
        return getattr(django_settings, 'SELENIUM_SCREENSHOT_DIR', '')

    @property
    def SELENIUM_TIMEOUT(self):
        """Default operation timeout in seconds"""
        return getattr(django_settings, 'SELENIUM_TIMEOUT', 10)


settings = LazySettings()
