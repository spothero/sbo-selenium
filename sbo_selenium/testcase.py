from __future__ import absolute_import

import base64
import httplib
import json
import os
import re
import socket
import sys
import time

from nose.tools import assert_raises
from django.test import LiveServerTestCase
from django.test.testcases import QuietWSGIRequestHandler, StoppableWSGIServer
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, \
    StaleElementReferenceException, TimeoutException
from selenium.webdriver import Chrome, DesiredCapabilities, Firefox, PhantomJS
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.support.color import Color
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait

from sbo_selenium.conf import settings

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


def replacement_get_stderr(self):
    """ Replacement for QuietWSGIRequestHandler.get_stderr() to log errors to
    file rather than cluttering the test output """
    log_file = settings.SELENIUM_LOG_FILE
    if log_file:
        return open(log_file, "a")
    else:
        return os.devnull


def replacement_log_message(self, format, *args):
    """ Replacement for QuitWSGIRequestHandler.log_message() to log to file
    rather than ignore the messages """
    # Don't bother logging requests for admin images or the favicon.
    if (self.path.startswith(self.admin_media_prefix)
            or self.path == '/favicon.ico'):
        return
    log_file = settings.SELENIUM_LOG_FILE
    if not log_file:
        return

    msg = "[%s] %s\n" % (self.log_date_time_string(), format % args)

    # Utilize terminal colors, if available
    if args[1][0] == '2':
        # Put 2XX first, since it should be the common case
        msg = self.style.HTTP_SUCCESS(msg)
    elif args[1][0] == '1':
        msg = self.style.HTTP_INFO(msg)
    elif args[1] == '304':
        msg = self.style.HTTP_NOT_MODIFIED(msg)
    elif args[1][0] == '3':
        msg = self.style.HTTP_REDIRECT(msg)
    elif args[1] == '404':
        msg = self.style.HTTP_NOT_FOUND(msg)
    elif args[1][0] == '4':
        msg = self.style.HTTP_BAD_REQUEST(msg)
    else:
        # Any 5XX, or any other response
        msg = self.style.HTTP_SERVER_ERROR(msg)

    with open(log_file, "a") as out:
        out.write(msg)


def replacement_handle_error(self, request, client_address):
    """ Replacement for StoppableWSGIServer.handle_error() to ignore errors
    rather than cluttering the test output """
    pass


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
        while(True):
            try:
                value = method(self._driver)
                if value:
                    return value
            except NoSuchElementException:
                pass
            except StaleElementReferenceException:
                pass
            time.sleep(self._poll)
            if(time.time() > end_time):
                break
        raise TimeoutException(message)

    def until_not(self, method, message=''):
        """Calls the method provided with the driver as an argument until the
        return value is False."""
        end_time = time.time() + self._timeout
        while(True):
            try:
                value = method(self._driver)
                if not value:
                    return value
            except NoSuchElementException:
                return True
            except StaleElementReferenceException:
                pass
            time.sleep(self._poll)
            if(time.time() > end_time):
                break
        raise TimeoutException(message)


class SeleniumTestCase(LiveServerTestCase):
    """
    Base class for Selenium tests.  Allows tests to be written independently
    of which browser they're going to be run in.
    """

    @classmethod
    def appium_command_executor(cls):
        """ Get the command executor URL for iOS simulator testing """
        if hasattr(cls, '_appium_executor'):
            return cls._appium_executor
        # Get the address iWebDriver will connect to
        address = None
        try:
            address = socket.gethostbyname(socket.gethostname())
        except:
            # Use default address defined below
            pass
        # If we don't have an address we should use localhost
        if not address:
            address = '127.0.0.1'
        port = 4723
        cls._appium_executor = "".join(["http://", address, ":", str(port),
                                     '/wd/hub'])
        return cls._appium_executor

    @classmethod
    def setUpClass(cls):
        # Hacks to suppress harmless broken pipe errors from output
        QuietWSGIRequestHandler.get_stderr = replacement_get_stderr
        QuietWSGIRequestHandler.log_message = replacement_log_message
        StoppableWSGIServer.handle_error = replacement_handle_error
        # Create the screenshots directory if it doesn't exist yet
        screenshot_dir = settings.SELENIUM_SCREENSHOT_DIR
        if screenshot_dir and not os.path.exists(screenshot_dir):
            os.mkdir(screenshot_dir)
        super(SeleniumTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(SeleniumTestCase, cls).tearDownClass()

    def setUp(self):
        """ Start a new browser instance for each test """
        self._screenshot_number = 1
        self.browser = os.getenv('SELENIUM_BROWSER',
                                 settings.SELENIUM_DEFAULT_BROWSER())
        if os.getenv('SELENIUM_HOST'):
            self.sel = self.sauce_labs_driver()
        elif self.browser == 'firefox':
            self.sel = Firefox()
        elif self.browser == 'htmlunit':
            self.sel = RemoteWebDriver(desired_capabilities=DesiredCapabilities.HTMLUNITWITHJS)
        elif self.browser in ['ios', 'ipad', 'ipod', 'iphone']:
            capabilities = {
                'app': 'safari',
                'browserName': '',
                'device': 'iPhone Simulator',
                'os': 'iOS 6.1'
            }
            self.sel = RemoteWebDriver(command_executor=self.appium_command_executor(),
                                       desired_capabilities=capabilities)
        elif self.browser == 'opera':
            self.sel = RemoteWebDriver(desired_capabilities=DesiredCapabilities.OPERA)
        elif self.browser == 'phantomjs':
            self.sel = PhantomJS()
        elif self.browser == 'safari':
            # requires a Safari extension to be built from source and installed
            self.sel = RemoteWebDriver(desired_capabilities=DesiredCapabilities.SAFARI)
        else:
            self.sel = Chrome()
        # Give the browser a little time; Firefox throws random errors if you
        # hit it too soon
        time.sleep(1)

    def tearDown(self):
        # Check to see if an exception was raised during the test
        info = sys.exc_info()
        passed = info[0] is None
        if not passed:
            # Want to see what went wrong
            self.screenshot()
        self.report_status(passed)
        self.sel.quit()
        super(SeleniumTestCase, self).tearDown()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~ Selenium operations ~~~~~~~~~~~~~~~~~~~~~~~~~~

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

    def click(self, selector):
        """ Wait until the element matching the selector is visible """
        element = self.wait_for_element(selector)
        element_is_visible = lambda driver: element.is_displayed()
        msg = "The element matching '%s' should be visible" % selector
        Wait(self.sel).until(element_is_visible, msg)
        element.click()
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
        if self.browser == 'htmlunit':
            # Doesn't support screenshots
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

    def wait_for_element(self, selector):
        element_is_present = lambda driver: driver.find_element_by_css_selector(selector)
        msg = "An elment matching '%s' should be on the page" % selector
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
        while(True):
            try:
                select = Select(self.sel.find_element_by_css_selector(selector))
                for option in select.options:
                    if option.text == option_text:
                        return option
            except (NoSuchElementException, StaleElementReferenceException) as e:
                pass
            time.sleep(settings.SELENIUM_POLL_FREQUENCY)
            if(time.time() > end_time):
                break
        raise TimeoutException("Select option should have been added")

    def wait_until_option_disabled(self, selector, option_text):
        """ Wait until the specified select option is disabled; the entire
        select widget may be replaced in the process """
        end_time = time.time() + settings.SELENIUM_TIMEOUT
        while(True):
            try:
                select = Select(self.sel.find_element_by_css_selector(selector))
                for option in select.options:
                    if option.text == option_text and not option.is_enabled():
                        return option
            except (NoSuchElementException, StaleElementReferenceException) as e:
                pass
            time.sleep(settings.SELENIUM_POLL_FREQUENCY)
            if(time.time() > end_time):
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
        while(True):
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
            except (NoSuchElementException, StaleElementReferenceException) as e:
                pass
            time.sleep(settings.SELENIUM_POLL_FREQUENCY)
            if(time.time() > end_time):
                break
        raise TimeoutException("'%s' should be offscreen" % selector)

    def wait_until_onscreen(self, selector):
        """ Wait until the element matching the provided selector has been
        moved into the viewable page """
        end_time = time.time() + settings.SELENIUM_TIMEOUT
        while(True):
            try:
                element = self.sel.find_element_by_css_selector(selector)
                location = element.location
                if location["x"] >= 0 and location["y"] >= 0:
                    self.screenshot()
                    return True
            except (NoSuchElementException, StaleElementReferenceException) as e:
                pass
            time.sleep(settings.SELENIUM_POLL_FREQUENCY)
            if(time.time() > end_time):
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

    # ~~~~~~~~~~~~~~~~~~~~~~~~~ Sauce Labs support ~~~~~~~~~~~~~~~~~~~~~~~~~~

    def sauce_labs_driver(self):
        """ Configure the Selenium driver to use Sauce Labs """
        host = os.getenv("SELENIUM_HOST", "ondemand.saucelabs.com")
        port = os.getenv("SELENIUM_PORT", "80")
        executor = "".join(["http://", host, ":", port, '/wd/hub'])
        platform = os.getenv("SELENIUM_PLATFORM", "Windows 2008")
        version = os.getenv("SELENIUM_VERSION", "")
        self.sauce_user_name = os.getenv("SAUCE_USER_NAME")
        api_key = os.getenv("SAUCE_API_KEY")
        self.sauce_auth = base64.encodestring('%s:%s' % (self.sauce_user_name,
                                                         api_key))[:-1]
        caps = {
            "platform": platform,
            "browserName": self.browser,
            "version": version,
            "javascriptEnabled": True,
            "name": self._testMethodName,
            "username": self.sauce_user_name,
            "accessKey": api_key
        }
        return webdriver.Remote(command_executor=executor,
                                desired_capabilities=caps)

    def report_status(self, passed):
        if not hasattr(self, 'sauce_user_name'):
            # Not using Sauce Labs for this test
            return
        # Report failure if any individual test failed or had an error
        body_content = json.dumps({"passed": passed})
        connection = httplib.HTTPConnection("saucelabs.com")
        url = '/rest/v1/%s/jobs/%s' % (self.sauce_user_name,
                                       self.sel.session_id)
        connection.request('PUT', url, body_content,
                           headers={"Authorization": "Basic %s" % self.sauce_auth})
        result = connection.getresponse()
        return result.status == 200
