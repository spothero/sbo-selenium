from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from nose.tools import assert_raises_regexp
from selenium.common.exceptions import TimeoutException

from sbo_selenium import SeleniumTestCase


@override_settings(SELENIUM_TIMEOUT=1)
class TestErrors(SeleniumTestCase):
    """
    Test cases for useful handling of error conditions.
    """

    def test_condition_timeout_custom_message(self):
        """ It should be possible to set a custom error message for a condition timeout """
        self.get(reverse('good_accessibility'))
        msg = 'Custom message'
        assert_raises_regexp(TimeoutException, msg, self.wait_for_condition, 'return no_such_variable', msg)

    def test_condition_timeout_default_message(self):
        """ A condition timeout should have a reasonable default message"""
        self.get(reverse('good_accessibility'))
        msg = '"return no_such_variable" never became true'
        assert_raises_regexp(TimeoutException, msg, self.wait_for_condition, 'return no_such_variable')
