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
    def SELENIUM_POLL_FREQUENCY(self):
        """Default operation retry frequency"""
        return getattr(django_settings, 'SELENIUM_POLL_FREQUENCY', 0.5)

    @property
    def SELENIUM_JAR_PATH(self):
        """Absolute path to the Selenium server jar file"""
        return getattr(django_settings, 'SELENIUM_JAR_PATH', '')

    @property
    def SELENIUM_SAUCE_API_KEY(self):
        """API key for the Sauce Labs account to use for running tests"""
        return getattr(django_settings, 'SELENIUM_SAUCE_API_KEY', '')

    @property
    def SELENIUM_SAUCE_CONNECT_PATH(self):
        """Absolute path to the Sauce Connect binary (for Sauce Labs)"""
        return getattr(django_settings, 'SELENIUM_SAUCE_CONNECT_PATH', '')

    @property
    def SELENIUM_SAUCE_USERNAME(self):
        """Username for the Sauce Labs account to use for running tests"""
        return getattr(django_settings, 'SELENIUM_SAUCE_USERNAME', '')

    @property
    def SELENIUM_SAUCE_VERSION(self):
        """Version of Selenium to use in the Sauce Labs virtual machines.  If
        omitted, uses the current default version used by Sauce Labs."""
        return getattr(django_settings, 'SELENIUM_SAUCE_VERSION', '')

    @property
    def SELENIUM_SCREENSHOT_DIR(self):
        """Directory in which to store screenshots"""
        return getattr(django_settings, 'SELENIUM_SCREENSHOT_DIR', '')

    @property
    def SELENIUM_TIMEOUT(self):
        """Default operation timeout in seconds"""
        return getattr(django_settings, 'SELENIUM_TIMEOUT', 10)

    @property
    def SELENIUM_PAGE_LOAD_TIMEOUT(self):
        """Connection timeout for page load GET requests in seconds"""
        return getattr(django_settings, 'SELENIUM_PAGE_LOAD_TIMEOUT', 10)


settings = LazySettings()
