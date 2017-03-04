from __future__ import absolute_import

import io
import json
import logging
import os
import psutil
import re
import socket
import sys
import time

from nose.tools import assert_raises
from django.test import LiveServerTestCase
from django.test.testcases import QuietWSGIRequestHandler

try:
    from django.test.testcases import StoppableWSGIServer
except ImportError:
    from django.test.testcases import WSGIServer as StoppableWSGIServer

from django.utils import six
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, \
    StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver import Chrome, DesiredCapabilities, Firefox, PhantomJS
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.support.color import Color
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from sbo_selenium.conf import settings

logger = logging.getLogger('django.request')

# Storage for Sauce Labs session IDs so they can be logged in bulk
sauce_sessions = []

ADD_ACCESSIBILITY_SCRIPT = """
var script = document.createElement('script');
script.src = '/static/js/axs_testing.js';
document.body.appendChild(script);
"""

SELECT_TEXT_SOURCE = """
(function(selector, start, end) {
    var children,
        count,
        i,
        j = 0,
        length,
        node,
        range,
        selection,
        textNode,
        text;
    selection = document.getSelection();
    selection.removeAllRanges();
    range = document.createRange();
    node = $(selector);
    children = node.contents();
    count = children.length;
    if ('createTouch' in document) {
        node.trigger('touchstart');
    }
    else {
        $(node).mousedown();
    }
    for (i = 0; i < count; i++) {
        textNode = children[i];
        if (textNode.nodeType !== 3) {
            continue;
        }
        text = textNode.nodeValue;
        length = text.length;
        if (length === 0) {
            continue;
        }
        if (start >= j + length || (end !== -1 && end <= j)) {}
        else if (j >= start && j + length <= end) {
            range.selectNodeContents(textNode);
            break;
        }
        else if (start >= j && start < j + length) {
            range.setStart(textNode, start - j);
        }
        else if (end > j && end <= j + length) {
            range.setEnd(textNode, end - j);
            break;
        }
        j += text.length;
    }
    if (end === -1) {
        range.setEnd(textNode, length);
    }
    selection.addRange(range);
    if ('createTouch' in document) {
        node.trigger('touchend');
    }
    else {
        $(node).mouseup();
    }
})('%s', %d, %d);
"""


class LoggingStream(io.TextIOBase):
    """
    A stream that writes to the "django.request" logger (sending a new message
    when each newline is encountered).
    """
    def __init__(self, *args, **kwargs):
        self.buffer = six.StringIO()
        super(LoggingStream, self).__init__(*args, **kwargs)

    def write(self, s):
        parts = re.split("([^\n]+)", s)
        for part in parts:
            if part == "\n":
                logger.error(self.buffer.getvalue())
                self.buffer = six.StringIO()
            elif part:
                self.buffer.write(part)


def replacement_get_stderr(self):
    """ Replacement for QuietWSGIRequestHandler.get_stderr() to log errors to
    file rather than cluttering the test output """
    return LoggingStream()


def replacement_log_message(self, format, *args):
    """ Replacement for QuitWSGIRequestHandler.log_message() to log messages
    rather than ignore them """
    logger.info("[%s] %s", self.log_date_time_string(), format % args)


def replacement_handle_error(self, request, client_address):
    """ Errors from the WSGI server itself tend to be harmless ones like
    "[Errno 32] Broken pipe" (which happens when a browser cancels a request
    before it finishes because it realizes it already has the asset).  By
    default these get dumped to stderr where they get confused with the test
    results, but aren't actually treated as test errors.  We'll just log them
    instead.
    """
    msg = "Exception happened during processing of request from %s"
    logger.error(msg, client_address, exc_info=sys.exc_info())

QuietWSGIRequestHandler.get_stderr = replacement_get_stderr
QuietWSGIRequestHandler.log_message = replacement_log_message
StoppableWSGIServer.handle_error = replacement_handle_error


def lambda_click(element):
    """Click function for use in Wait lambdas to verify that the click succeeded"""
    if not element.is_displayed():
        return False
    element.click()
    return True


class Wait(WebDriverWait):
    """ Subclass of WebDriverWait with predetermined timeout and poll
    frequency.  Also deals with a wider variety of exceptions. """

    def __init__(self, driver):
        """ Constructor """
        super(Wait, self).__init__(driver, settings.SELENIUM_TIMEOUT,
                                   settings.SELENIUM_POLL_FREQUENCY)

    def until(self, method, message=''):
        """Calls the method provided with the driver as an argument until the \
        return value is not False."""
        end_time = time.time() + self._timeout
        while True:
            try:
                value = method(self._driver)
                if value:
                    return value
            except NoSuchElementException:
                pass
            except StaleElementReferenceException:
                pass
            except WebDriverException:
                pass
            time.sleep(self._poll)
            if time.time() > end_time:
                break
        raise TimeoutException(message)

    def until_not(self, method, message=''):
        """Calls the method provided with the driver as an argument until the
        return value is False."""
        end_time = time.time() + self._timeout
        while True:
            try:
                value = method(self._driver)
                if not value:
                    return value
            except NoSuchElementException:
                return True
            except StaleElementReferenceException:
                pass
            except WebDriverException:
                pass
            time.sleep(self._poll)
            if time.time() > end_time:
                break
        raise TimeoutException(message)


class SeleniumTestCaseBase(LiveServerTestCase):
    """
    Base class for Selenium tests.  Allows tests to be written independently
    of which browser they're going to be run in.
    """

    user_agent = ''
    webdriver_capabilities = {}
    mobile_emulation = None

    def get_firefox_profile(self):
        return webdriver.FirefoxProfile()

    def get_chrome_driver(self, chrome_options=None):
        capabilities = chrome_options.to_capabilities()
        return Chrome(desired_capabilities=capabilities)

    @classmethod
    def setup_screenshot_dir(cls):
        # Create the screenshots directory if it doesn't exist yet
        screenshot_dir = settings.SELENIUM_SCREENSHOT_DIR
        if screenshot_dir and not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)

    @classmethod
    def setUpClass(cls):
        cls.setup_screenshot_dir()
        super(SeleniumTestCaseBase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(SeleniumTestCaseBase, cls).tearDownClass()

    def set_up_browser(self):
        browser = os.getenv('SELENIUM_BROWSER',
                                 settings.SELENIUM_DEFAULT_BROWSER)
        host = os.getenv('SELENIUM_GRID_HUB',
                                 settings.SELENIUM_GRID_HUB)

        if browser == 'chrome':
            chrome_options = webdriver.ChromeOptions()
            if self.mobile_emulation:
                mobile_emulation = {"deviceName": self.mobile_emulation}
                chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)

        if host:
            capabilities = {}

            if browser == 'chrome':
                capabilities = chrome_options.to_capabilities()

            socket.setdefaulttimeout(30)

            def get_sel():
                try:
                    return RemoteWebDriver(command_executor=host, desired_capabilities=capabilities)
                except socket.timeout:
                    return get_sel()

            sel = get_sel()

        elif browser == 'firefox':
            sel = Firefox(self.get_firefox_profile())
        elif browser == 'htmlunit':
            sel = RemoteWebDriver(desired_capabilities=DesiredCapabilities.HTMLUNITWITHJS)
        elif browser == 'opera':
            sel = RemoteWebDriver(desired_capabilities=DesiredCapabilities.OPERA)
        elif browser == 'iexplore':
            sel = RemoteWebDriver(desired_capabilities=DesiredCapabilities.INTERNETEXPLORER)
        elif browser == 'phantomjs':
            sel = PhantomJS(service_args=['--debug=true', '--webdriver-loglevel=DEBUG'])
        elif browser == 'safari':
            # requires a Safari extension to be built from source and installed
            sel = RemoteWebDriver(desired_capabilities=DesiredCapabilities.SAFARI)
        else:
            sel = self.get_chrome_driver(chrome_options)

        sel.set_page_load_timeout(settings.SELENIUM_PAGE_LOAD_TIMEOUT)
        time.sleep(1)
        return sel


    def setUp(self):
        """ Start a new browser instance for each test """
        self._screenshot_number = 1
        self.sel = self.set_up_browser()


    def tearDown(self):
        # Check to see if an exception was raised during the test
        info = sys.exc_info()
        passed = info[0] is None
        if not passed:
            # Want to see what went wrong
            self.screenshot()
        super(SeleniumTestCaseBase, self).tearDown()
        self.sel.quit()


class SeleniumOperationsMixin(object):
    """
    Selenium Operations Mixin that contains all our selenium helpers.

    """

    def assert_hidden(self, selector):
        element = self.wait_for_element(selector)
        msg = "'%s' should not be visible" % selector
        assert not element.is_displayed(), msg

    def assert_not_present(self, selector):
        assert_raises(NoSuchElementException,
                      self.sel.find_element_by_css_selector, selector)

    def assert_not_visible(self, selector):
        """ Ok if it's either missing or hidden """
        try:
            element = self.sel.find_element_by_css_selector(selector)
        except NoSuchElementException:
            return
        msg = "'%s' should not be visible" % selector
        assert not element.is_displayed(), msg

    def assert_text_not_in_element(self, selector, text):
        """ Verify that the specified element does not contain certain text """
        msg = "'%s' should not contain the text '%s'" % (selector, text)
        content = self.sel.find_element_by_css_selector(selector).text
        assert text not in content, msg

    def assert_visible(self, selector):
        element = self.wait_for_element(selector)
        msg = "'%s' should be visible" % selector
        assert element.is_displayed(), msg

    def audit_accessibility(self):
        """ Check for accessibility violations using the JavaScript library
        from Chrome's Developer Tools. """
        # First add the library to the page
        script = ''
        for line in ADD_ACCESSIBILITY_SCRIPT.splitlines():
            script += line.strip()
        self.sel.execute_script(script)
        # Wait for the script to finish loading
        self.wait_for_condition('return axs.AuditRule.specs.videoWithoutCaptions !== "undefined";')
        # Now run the audit and inspect the results
        self.sel.execute_script('axs_audit_results = axs.Audit.run();')
        failed = self.sel.execute_script('return axs_audit_results.some(function (element, index, array) { return element.result === "FAIL" });')
        if failed:
            report = self.sel.execute_script('return axs.Audit.createReport(axs_audit_results);')
            raise self.failureException(report)

    def click(self, selector):
        """ Click the element matching the selector (and retry if it isn't
        visible or clickable yet) """
        element = self.wait_for_element(selector)
        element_was_clicked = lambda driver: lambda_click(element)
        msg = "The element matching '%s' should be clickable" % selector
        Wait(self.sel).until(element_was_clicked, msg)
        return element

    def click_link_with_text(self, text):
        link_is_present = lambda driver: driver.find_element_by_link_text(text)
        msg = "A link with text '%s' should be present" % text
        link = Wait(self.sel).until(link_is_present, msg)
        link.click()
        return link

    def click_link_with_xpath(self, xpath):
        link_is_present = lambda driver: driver.find_element_by_xpath(xpath)
        msg = "A link with xpath '%s' should be present" % xpath
        link = Wait(self.sel).until(link_is_present, msg)
        link.click()
        return link

    def enter_text(self, selector, value):
        field = self.wait_for_element(selector)
        field.send_keys(value)
        self.screenshot()
        return field

    def enter_text_via_xpath(self, xpath, value):
        field = self.wait_for_xpath(xpath)
        field.send_keys(value)
        self.screenshot()
        return field

    def get(self, relative_url):
        self.sel.get('%s%s' % (self.live_server_url, relative_url))
        self.screenshot()

    def screenshot(self):
        if hasattr(self, 'sauce_user_name'):
            # Sauce Labs is taking screenshots for us
            return
        if not hasattr(self, 'browser') or self.browser == 'htmlunit':
            # Can't take screenshots
            return
        screenshot_dir = settings.SELENIUM_SCREENSHOT_DIR
        if not screenshot_dir:
            return
        name = "%s_%d.png" % (self._testMethodName, self._screenshot_number)
        path = os.path.join(screenshot_dir, name)
        self.sel.get_screenshot_as_file(path)
        self._screenshot_number += 1

    def select_by_text(self, selector, text):
        select = Select(self.wait_for_element(selector))
        select.select_by_visible_text(text)
        self.screenshot()
        return select

    def select_by_value(self, selector, value):
        select = Select(self.wait_for_element(selector))
        select.select_by_value(value)
        self.screenshot()
        return select

    def select_text(self, selector, start=0, end=-1):
        """ Selects the specified text range of the element matching the
        provided selector by simulating a mouse down, programmatically
        selecting the text, and then simulating a mouse up.  Doesn't yet work
        on IE < 9 or iOS. Doesn't support nested markup either. """
        if not hasattr(self, 'select_text_template'):
            template = ''
            for line in SELECT_TEXT_SOURCE.splitlines():
                template += line.strip()
            self.select_text_template = template
        script = self.select_text_template % (selector, start, end)
        self.sel.execute_script(script)
        self.screenshot()

    def wait_for_background_color(self, selector, color_string):
        color = Color.from_string(color_string)
        correct_color = lambda driver: Color.from_string(driver.find_element_by_css_selector(selector).value_of_css_property("background-color")) == color
        msg = "The color of '%s' should be %s" % (selector, color_string)
        Wait(self.sel).until(correct_color, msg)
        self.screenshot()

    def wait_for_condition(self, return_statement, msg=None):
        """Wait until the provided JavaScript expression returns true.
        Note: for this to work, the expression must include the "return"
        keyword, not just the expression to be evaluated."""
        condition_is_true = lambda driver: driver.execute_script(return_statement)
        if not msg:
            msg = '"{}" never became true'.format(return_statement)
        Wait(self.sel).until(condition_is_true, msg)

    def wait_for_element(self, selector):
        element_is_present = lambda driver: driver.find_element_by_css_selector(selector)
        msg = "An element matching '%s' should be on the page" % selector
        element = Wait(self.sel).until(element_is_present, msg)
        self.screenshot()
        return element

    def wait_for_text(self, text):
        text_is_present = lambda driver: text in driver.page_source
        msg = "The text '%s' should be present on the page" % text
        Wait(self.sel).until(text_is_present, msg)
        self.screenshot()

    def wait_for_xpath(self, xpath):
        element_is_present = lambda driver: driver.find_element_by_xpath(xpath)
        msg = "An element matching '%s' should be on the page" % xpath
        element = Wait(self.sel).until(element_is_present, msg)
        self.screenshot()
        return element

    def wait_until_element_contains(self, selector, text):
        """ Wait until the specified element contains certain text """
        text_contained = lambda driver: text in driver.find_element_by_css_selector(selector).text
        msg = "'%s' should contain the text '%s'" % (selector, text)
        Wait(self.sel).until(text_contained, msg)
        self.screenshot()

    def wait_until_hidden(self, selector):
        """ Wait until the element matching the selector is hidden """
        element = self.wait_for_element(selector)
        element_is_hidden = lambda driver: not element.is_displayed()
        msg = "The element matching '%s' should not be visible" % selector
        Wait(self.sel).until(element_is_hidden, msg)
        self.screenshot()
        return element

    def wait_until_not_present(self, selector):
        """ Wait until the element matching the selector is gone from page """
        element_is_present = lambda driver: driver.find_element_by_css_selector(selector)
        msg = "There should not be an element matching '%s'" % selector
        Wait(self.sel).until_not(element_is_present, msg)
        self.screenshot()

    def wait_until_not_visible(self, selector):
        """ Wait until the element matching the selector is either hidden or
        removed from the page """
        element_is_visible = lambda driver: driver.find_element_by_css_selector(selector).is_displayed()
        msg = "The element matching '%s' should not be visible" % selector
        Wait(self.sel).until_not(element_is_visible, msg)
        self.screenshot()

    def wait_until_option_added(self, selector, option_text):
        """ Wait until the specified select option appears; the entire
        select widget may be replaced in the process """
        end_time = time.time() + settings.SELENIUM_TIMEOUT
        while True:
            try:
                select = Select(self.sel.find_element_by_css_selector(selector))
                for option in select.options:
                    if option.text == option_text:
                        return option
            except (NoSuchElementException, StaleElementReferenceException):
                pass
            time.sleep(settings.SELENIUM_POLL_FREQUENCY)
            if time.time() > end_time:
                break
        raise TimeoutException("Select option should have been added")

    def wait_until_option_disabled(self, selector, option_text):
        """ Wait until the specified select option is disabled; the entire
        select widget may be replaced in the process """
        end_time = time.time() + settings.SELENIUM_TIMEOUT
        while True:
            try:
                select = Select(self.sel.find_element_by_css_selector(selector))
                for option in select.options:
                    if option.text == option_text and not option.is_enabled():
                        return option
            except (NoSuchElementException, StaleElementReferenceException):
                pass
            time.sleep(settings.SELENIUM_POLL_FREQUENCY)
            if time.time() > end_time:
                break
        raise TimeoutException("Select option should have been disabled")

    def wait_until_property_equals(self, selector, name, value):
        """ Wait until the specified CSS property of the element matching the
        provided selector matches the expected value """
        value_is_correct = lambda driver: driver.find_element_by_css_selector(selector).value_of_css_property(name) == value
        msg = "The %s CSS property of '%s' should be %s" % (name, selector,
                                                            value)
        Wait(self.sel).until(value_is_correct, msg)
        self.screenshot()

    def wait_until_offscreen(self, selector):
        """ Wait until the element matching the provided selector has been
        moved offscreen (deliberately, not just scrolled out of view) """
        end_time = time.time() + settings.SELENIUM_TIMEOUT
        while True:
            try:
                element = self.sel.find_element_by_css_selector(selector)
                location = element.location
                size = element.size
                if location["y"] + size["height"] <= 0:
                    self.screenshot()
                    return True
                if location["x"] + size["width"] <= 0:
                    self.screenshot()
                    return True
            except (NoSuchElementException, StaleElementReferenceException):
                pass
            time.sleep(settings.SELENIUM_POLL_FREQUENCY)
            if time.time() > end_time:
                break
        raise TimeoutException("'%s' should be offscreen" % selector)

    def wait_until_onscreen(self, selector):
        """ Wait until the element matching the provided selector has been
        moved into the viewable page """
        end_time = time.time() + settings.SELENIUM_TIMEOUT
        while True:
            try:
                element = self.sel.find_element_by_css_selector(selector)
                location = element.location
                if location["x"] >= 0 and location["y"] >= 0:
                    self.screenshot()
                    return True
            except (NoSuchElementException, StaleElementReferenceException):
                pass
            time.sleep(settings.SELENIUM_POLL_FREQUENCY)
            if time.time() > end_time:
                break
        raise TimeoutException("'%s' should be offscreen" % selector)

    def wait_until_property_less_than(self, selector, name, value):
        """ Wait until the specified CSS property of the element matching the
        provided selector is less than a certain value.  Ignores any
        non-integer suffixes like 'px'. """
        value_is_correct = lambda driver: int(re.match(r'([\d-]+)', driver.find_element_by_css_selector(selector).value_of_css_property(name)).group(1)) < value
        msg = "The %s CSS property of '%s' should be less than %s" % (name, selector, value)
        Wait(self.sel).until(value_is_correct, msg)
        self.screenshot()

    def wait_until_visible(self, selector):
        """ Wait until the element matching the selector is visible """
        element = self.wait_for_element(selector)
        element_is_visible = lambda driver: element.is_displayed()
        msg = "The element matching '%s' should be visible" % selector
        Wait(self.sel).until(element_is_visible, msg)
        return element


class SeleniumTestCase(SeleniumOperationsMixin, SeleniumTestCaseBase):
    """
    Base class for Selenium tests.  Allows tests to be written independently
    of which browser they're going to be run in.
    """
    pass
