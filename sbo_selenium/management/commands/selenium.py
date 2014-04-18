from optparse import make_option
import os
from shutil import rmtree
from subprocess import Popen, PIPE

from django.core.management import call_command
from django.core.management.base import BaseCommand

from django_nose.management.commands.test import Command as TestCommand

from sbo_selenium.conf import settings
from sbo_selenium.testcase import sauce_sessions
from sbo_selenium.utils import OutputMonitor


class Command(BaseCommand):
    """
    Django management command for running Selenium tests.
    """
    args = '<package or test>'
    help = 'Run Selenium tests for this application'
    requires_model_validation = True
    custom_options = (
        make_option(
            '-b',
            '--browser',
            dest='browser_name',
            default='chrome',
            help='Name of the browser to run the tests in (default is chrome)'
        ),
        make_option(
            '-n',
            type='int',
            dest='count',
            default=1,
            help='Number of times to run each test'
        ),
        make_option(
            '-p',
            '--platform',
            dest='platform',
            help='OS and version thereof for the Sauce OnDemand VM to use'
        ),
        make_option(
            '--browser-version',
            dest='browser_version',
            help='Browser version for the Sauce OnDemand VM to use'
        ),
        make_option(
            '--tunnel-identifier',
            dest='tunnel_id',
            help='Sauce Connect tunnel identifier'
        )
    )
    option_list = TestCommand.option_list + custom_options

    @staticmethod
    def clean():
        """Clear out any old screenshots"""
        screenshot_dir = settings.SELENIUM_SCREENSHOT_DIR
        if screenshot_dir and os.path.isdir(screenshot_dir):
            rmtree(screenshot_dir, ignore_errors=True)

    def handle(self, *args, **options):
        """
        Run the specified Selenium test(s) the indicated number of times in
        the specified browser.
        """
        browser_name = options['browser_name']
        count = options['count']
        if len(args) > 0:
            tests = list(args)
        else:
            tests = settings.SELENIUM_DEFAULT_TESTS

        # Kill any orphaned chromedriver processes
        process = Popen(['killall', 'chromedriver'],
                        stderr=open(os.devnull, 'w'))
        process.wait()

        # Clear any old log and screenshots
        self.clean()

        sc_process = None
        selenium_process = None
        if 'platform' in options and settings.SELENIUM_SAUCE_CONNECT_PATH:
            running, sc_process = self.verify_sauce_connect_is_running(options)
            if not running:
                return
        elif browser_name in ['opera', 'safari']:
            running, selenium_process = self.verify_selenium_server_is_running()
            if not running:
                return
        elif browser_name in ['ipad', 'iphone']:
            if not self.verify_appium_is_running():
                return

        # Ugly hack: make it so django-nose won't have nosetests choke on our
        # parameters
        BaseCommand.option_list += self.custom_options

        # Configure and run the tests
        self.update_environment(options)
        self.run_tests(tests, browser_name, count)

        # Kill Sauce Connect, if running
        if sc_process:
            sc_process.kill()

        # Kill the Selenium standalone server, if running
        if selenium_process:
            selenium_process.kill()

    def run_tests(self, tests, browser_name, count):
        """Configure and run the tests"""
        test_args = ['test'] + tests
        for i in range(count):
            msg = 'Test run %d using %s' % (i + 1, browser_name)
            self.stdout.write(msg)
            call_command(*test_args)
            for session in sauce_sessions:
                self.stdout.write(session)
            self.stdout.flush()
            del sauce_sessions[:]

    @staticmethod
    def update_environment(options):
        """
        Populate the environment variables that need to be added for test
        execution to work correctly.  Most (but not all) of these are to match
        what the Jenkins Sauce OnDemand plugin would use for the test
        configuration that was specified on the command line.
        """
        env = os.environ
        # https://docs.djangoproject.com/en/1.6/topics/testing/tools/#liveservertestcase
        env['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = settings.DJANGO_LIVE_TEST_SERVER_ADDRESS
        tunnel_id = options['tunnel_id']
        if tunnel_id:
            env['SAUCE_TUNNEL_ID'] = tunnel_id
        if 'SAUCE_API_KEY' in env:
            # Jenkins plugin has already configured the environment for us
            return
        env['SELENIUM_BROWSER'] = options['browser_name']
        platform = options['platform']
        browser_version = options['browser_version']
        if not platform or not browser_version:
            # None of the following Sauce OnDemand stuff applies
            return
        if settings.SELENIUM_SAUCE_CONNECT_PATH:
            host = 'localhost'
            port = '4445'
        else:
            host = 'ondemand.saucelabs.com'
            port = '80'
        env.update({
            'SAUCE_API_KEY': settings.SELENIUM_SAUCE_API_KEY,
            'SAUCE_USER_NAME': settings.SELENIUM_SAUCE_USERNAME,
            'SELENIUM_BROWSER': options['browser_name'],
            'SELENIUM_HOST': host,
            'SELENIUM_PLATFORM': platform,
            'SELENIUM_PORT': port,
            'SELENIUM_VERSION': browser_version,
        })

    def verify_sauce_connect_is_running(self, options):
        """
        Start Sauce Connect, if it isn't already running.  Returns a tuple of
        two elements:

        * A boolean which is True if Sauce Connect is now running
        * The Popen object representing the process so it can be terminated
          later; if it was already running, this value is "None"
        """
        sc_path = settings.SELENIUM_SAUCE_CONNECT_PATH
        if len(sc_path) < 2:
            self.stdout.write('You need to configure SELENIUM_SAUCE_CONNECT_PATH')
            return False, None
        username = settings.SELENIUM_SAUCE_USERNAME
        if not username:
            self.stdout.write('You need to configure SELENIUM_SAUCE_USERNAME')
            return False, None
        key = settings.SELENIUM_SAUCE_API_KEY
        if not key:
            self.stdout.write('You need to configure SELENIUM_SAUCE_API_KEY')
            return False, None
        # Is it already running?
        process = Popen(['ps -e | grep "%s"' % key],
                        shell=True, stdout=PIPE)
        (grep_output, _grep_error) = process.communicate()
        grep_command = 'grep {}'.format(key)
        lines = grep_output.split('\n')
        for line in lines:
            if 'sc' in line and username in line and grep_command not in line:
                self.stdout.write('Sauce Connect is already running')
                return True, None
        self.stdout.write('Starting Sauce Connect')
        output = OutputMonitor()
        command = [sc_path, '-u', username, '-k', key]
        tunnel_id = options['tunnel_id']
        if tunnel_id:
            command.extend(['-i', tunnel_id])
        sc_process = Popen(command,
                           stdout=output.stream.input,
                           stderr=open(os.devnull, 'w'))
        ready_log_line = 'Connection established.'
        if not output.wait_for(ready_log_line, 60):
            self.stdout.write('Timeout starting Sauce Connect:\n')
            self.stdout.write('\n'.join(output.lines))
            return False, None
        return True, sc_process

    def verify_selenium_server_is_running(self):
        """
        Start the Selenium standalone server, if it isn't already running.
        Returns a tuple of two elements:

        * A boolean which is True if the server is now running
        * The Popen object representing the process so it can be terminated
          later; if the server was already running, this value is "None"
        """
        selenium_jar = settings.SELENIUM_JAR_PATH
        if len(selenium_jar) < 5:
            self.stdout.write('You need to configure SELENIUM_JAR_PATH')
            return False, None
        _jar_dir, jar_name = os.path.split(selenium_jar)
        # Is it already running?
        process = Popen(['ps -e | grep "%s"' % jar_name[:-4]],
                        shell=True, stdout=PIPE)
        (grep_output, _grep_error) = process.communicate()
        lines = grep_output.split('\n')
        for line in lines:
            if jar_name in line:
                self.stdout.write('Selenium standalone server is already running')
                return True, None
        self.stdout.write('Starting the Selenium standalone server')
        output = OutputMonitor()
        selenium_process = Popen(['java', '-jar', selenium_jar],
                                 stdout=output.stream.input,
                                 stderr=open(os.devnull, 'w'))
        ready_log_line = 'Started org.openqa.jetty.jetty.Server'
        if not output.wait_for(ready_log_line, 10):
            self.stdout.write('Timeout starting the Selenium server:\n')
            self.stdout.write('\n'.join(output.lines))
            return False, None
        return True, selenium_process

    def verify_appium_is_running(self):
        """Verify that Appium is running so it can be used for local iOS tests."""
        process = Popen(['ps -e | grep "Appium"'], shell=True, stdout=PIPE)
        (grep_output, _grep_error) = process.communicate()
        lines = grep_output.split('\n')
        for line in lines:
            if 'Appium.app' in line:
                self.stdout.write('Appium is already running')
                return True
        self.stdout.write('Please launch and configure Appium first')
        return False
