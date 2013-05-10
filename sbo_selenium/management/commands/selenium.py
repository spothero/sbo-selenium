from optparse import make_option
import os
from shutil import rmtree
from subprocess import Popen, PIPE

from django.core.management import call_command
from django.core.management.base import BaseCommand

from sbo_selenium.conf import settings
from sbo_selenium.utils import OutputMonitor


class Command(BaseCommand):
    """
    Django management command for running Selenium tests.
    """
    args = '<package or test>'
    help = 'Run Selenium tests for this application'
    requires_model_validation = True
    custom_options = (
        make_option('-b',
            '--browser',
            dest='browser',
            default='chrome',
            help='Browser to run the tests in (default is chrome)'
        ),
        make_option('-n',
            type='int',
            dest='count',
            default=1,
            help='Number of times to run each test'
        ),
    )
    # Accept parameters for passthrough
    passthrough_options = (
        make_option('--noinput',
            action='store_false',
            dest='interactive',
            default=True,
            help='Tells Django to NOT prompt the user for input of any kind.'
        ),
        make_option(
            '--with-xunit',
            action='store_true',
            dest='xunit_enabled'
        ),
        make_option(
            '--xunit-file',
            dest='xunit_file',
            default='',
            help=("Path to xml file to store the xunit report in. "
                  "Default is nosetests.xml in the working directory "
                  "[NOSE_XUNIT_FILE]")
        ),
    )
    option_list = BaseCommand.option_list + custom_options + passthrough_options

    def handle(self, *args, **options):
        """
        Run the specified Selenium test(s) the indicated number of times in
        the specified browser.
        """
        browser = options['browser']
        count = options['count']
        if len(args) > 0:
            tests = list(args)
        else:
            tests = settings.SELENIUM_DEFAULT_TESTS

        # Kill any orphaned chromedriver processes
        process = Popen(['killall', 'chromedriver'],
                        stderr=open(os.devnull, 'w'))
        process.wait()

        # Delete any old log and screenshots
        log_file = settings.SELENIUM_LOG_FILE
        if log_file and os.path.isfile(log_file):
            os.remove(log_file)
        screenshot_dir = settings.SELENIUM_SCREENSHOT_DIR
        if screenshot_dir and os.path.isdir(screenshot_dir):
            rmtree(screenshot_dir)

        # Start the Selenium standalone server if it's needed
        selenium_process = None
        if browser in ['opera', 'safari']:
            selenium_jar = settings.SELENIUM_JAR_PATH
            if len(selenium_jar) < 5:
                self.stdout.write('You need to configure SELENIUM_JAR_PATH')
                return
            _jar_dir, jar_name = os.path.split(selenium_jar)
            # Is it already running?
            process = Popen(['ps -e | grep "%s"' % jar_name[:-4]],
                            shell=True, stdout=PIPE)
            (grep_output, _grep_error) = process.communicate()
            lines = grep_output.split('\n')
            running = False
            for line in lines:
                if jar_name in line:
                    self.stdout.write('Selenium standalone server is already running')
                    running = True
            if not running:
                self.stdout.write('Starting the Selenium standalone server')
                output = OutputMonitor()
                selenium_process = Popen(['java', '-jar', selenium_jar],
                                         stdout=output.stream.input,
                                         stderr=open(os.devnull, 'w'))
                ready_log_line = 'Started org.openqa.jetty.jetty.Server'
                if not output.wait_for(ready_log_line, 10):
                    self.stdout.write('Timeout starting the Selenium server:')
                    self.stdout.write('\n'.join(output.lines))
                    return
        elif browser in ['ipad', 'iphone']:
            # Is Appium running?
            process = Popen(['ps -e | grep "Appium"'], shell=True, stdout=PIPE)
            (grep_output, _grep_error) = process.communicate()
            lines = grep_output.split('\n')
            running = False
            for line in lines:
                if 'Appium.app' in line:
                    self.stdout.write('Appium is already running')
                    running = True
            if not running:
                self.stdout.write('Please launch and configure Appium first')
                return

        # Ugly hack: make it so django-nose won't have nosetests choke on our
        # parameters
        BaseCommand.option_list += self.custom_options

        # Configure and run the tests
        env = os.environ
        address = settings.DJANGO_LIVE_TEST_SERVER_ADDRESS
        env['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = address
        test_args = ['test'] + tests
        env['SELENIUM_BROWSER'] = browser
        for i in range(count):
            msg = 'Test run %d using %s' % (i + 1, browser)
            self.stdout.write(msg)
            call_command(*test_args)

        # Kill the Selenium standalone server, if running
        if selenium_process:
            selenium_process.kill()
