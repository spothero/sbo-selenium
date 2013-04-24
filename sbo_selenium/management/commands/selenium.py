from optparse import make_option
import os
from shutil import rmtree
from subprocess import Popen

from django.core.management import call_command
from django.core.management.base import BaseCommand

from sbo_selenium.conf import settings


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
    option_list = BaseCommand.option_list + custom_options

    def handle(self, *args, **options):
        """
        Run the specified Selenium test(s) the indicated number of times in
        the specified browser.
        """
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

        # Ugly hack: make it so django-nose won't have nosetests choke on our
        # parameters
        BaseCommand.option_list += self.custom_options

        # Configure and run the tests
        env = os.environ
        address = settings.DJANGO_LIVE_TEST_SERVER_ADDRESS
        env['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = address
        test_args = ['test'] + tests
        browser = options['browser']
        count = options['count']
        env['SELENIUM_BROWSER'] = browser
        for i in range(count):
            msg = 'Test run %d using %s' % (i + 1, browser)
            self.stdout.write(msg)
            call_command(*test_args)
