sbo-selenium
============

sbo-selenium is a framework primarily intended to help write Selenium tests for
Django applications, although it may be useful in testing other kinds of web
applications as well.

Installation
------------

Add 'sbo-selenium' to the requirements for the application being tested, and add
'sbo_selenium' to the INSTALLED_APPS setting.  Install the new dependency as
usual for the containing project; for SBO packages this is typically::

    pip install -r requirements/tests.txt

To run tests using a particular browser, it needs to already be installed.  To
drive Chrome via Selenium, you'll need to install both Chrome itself and then
chromedriver:
 
1. Download the correct ChromeDriver from http://chromedriver.storage.googleapis.com/index.html
2. Put the binary, ``chromedriver``, somewhere on your path
   (ex: ``/usr/local/bin/chromedriver``)

On Mac OS X, if you have Homebrew installed you can instead run
``brew install chromedriver``.

To test Mobile Safari in the iPhone simulator, you'll first need to do the
following:

* Install Xcode
* From the Downloads tab of the Xcode Preferences dialog, install
  "Command Line Tools" and one of the iOS Simulator components (probably the
  latest one)
* Download and run `Appium <http://appium.io/>`_
* Check the "Use Mobile Safari" checkbox
* If you want to test in the iPad form factor, check the "Force Device"
  checkbox and make sure "iPad" is selected next to it
* Click the "Launch" button

To test Opera or Safari, you'll need to download the Selenium standalone server
`jar file <http://selenium-release.storage.googleapis.com/2.40/selenium-server-standalone-2.40.0.jar>`_
and configure the path to it in the ``SELENIUM_JAR_PATH`` setting
described below.

Note that all of these browsers and more can be tested using Sauce OnDemand;
see below for details.

Settings
--------

sbo-selenium uses a few Django settings to configure some aspects of test
runs:

* ``DJANGO_LIVE_TEST_SERVER_ADDRESS`` - The address at which to run the test
  server (this will be used as the environment variable of the same name
  described in the Django testing documentation).  Default value is
  ``'localhost:9090'``.
* ``SELENIUM_DEFAULT_BROWSER`` - The web browser to use for tests when none is
  specified.  Default value is ``'chrome'``.
* ``SELENIUM_DEFAULT_TESTS`` - The Selenium test(s) to be run by default when
  none are specified.  Should be an array of nose-compatible test
  specifications (see `Running Tests`_ below for examples).  Default value is
  an empty list.
* ``SELENIUM_PAGE_LOAD_TIMEOUT`` - The number of seconds to wait for a response
  to a GET request before considering it to have failed.  Default value is 10
  seconds.  (This is particularly important when using Sauce Connect, as it
  sometimes fails to connect properly, such that every single page load stalls
  indefinitely.)
* ``SELENIUM_JAR_PATH`` - Absolute path of the Selenium standalone server jar
  file.
* ``SELENIUM_POLL_FREQUENCY`` - The number of seconds to wait after a failed
  operation before trying again.  Default value is 0.5 seconds.
* ``SELENIUM_SAUCE_API_KEY`` - The API key for the Sauce Labs account to use
  for running tests.
* ``SELENIUM_SAUCE_CONNECT_PATH`` - Absolute path of the
  `Sauce Connect <https://saucelabs.com/docs/connect>`_ binary, used when
  testing a site that isn't visible to the internet at large via Sauce Labs.
  If not set but other parameters indicate Sauce usage, it's assumed that the
  site being tested is publicly accessible.
* ``SELENIUM_SAUCE_USERNAME`` - The username for the Sauce Labs account to use
  for running tests.
* ``SELENIUM_SAUCE_VERSION`` - The version of Selenium to ask Sauce Labs to
  use in the provided virtual machine.  If omitted, the current default version
  provided by Sauce Labs is used.  Documentation on the available versions and
  current default can be found `here <https://saucelabs.com/docs/additional-config#selenium-version>`_.
* ``SELENIUM_SCREENSHOT_DIR`` - Absolute path of the directory in which to save
  screenshots taken over the course of running tests (these can be useful for
  debugging test failures).  The directory will be created if it doesn't
  already exist.  If the tests are being run via Sauce Labs, screenshots are
  not created in this directory because that service generates screenshots for
  us.
* ``SELENIUM_TIMEOUT`` - The number of seconds to wait after an operation first
  failed until giving up and declaring it an error.  Default value is 10
  seconds.

Note that some test runners (such as nose) may not always show errors logged
during test setup and teardown.  To consistently get this output, you may want
to configure a logging handler that outputs to file (in addition to any that
may be outputting to console).

Creating Tests
--------------

We're creating Selenium tests as Python classes.  Typically you'll want to
create a common subclass of sbo_selenium.SeleniumTestCase which each of your
application's actual test classes will in turn inherit from.  This main class
will contain methods for common operations like logging in and logging out,
verifying that common page content is present, loading typical test data, and
so forth.  This can be defined in the application's tests.selenium.__init__
module.  Avoid method names with "test" in them, as the test runner is likely
to mistake them for actual standalone tests.

Each related set of tests should then be created as methods in a subclass of
this common test case class which lives in its own file within tests.selenium
(or a subdirectory thereof).  These test methods should start with ``test_`` so
the test runner can find them, and it's generally good practice to have utility
methods which aren't tests themselves start with an underscore.  Typically each
test class will cover functionality on a single page or a set of closely
related pages.

Running Tests
-------------

Tests can be run via the "selenium" management command::

    ./manage.py selenium --settings=myapp.selenium_settings

Or to specify which test(s) to run rather than using the defaults specified in
the settings file::

    ./manage.py selenium myapp.tests.selenium.test_module:TestClass.test_method myotherapp/tests/selenium --settings=myapp.selenium_settings

Having a separate settings file for the Selenium tests isn't a requirement, but
in practice you'll probably want to use different settings for the tests than
you do for development (for example, to make sure that ``DEBUG=False``).  If you
don't want to type out the settings parameter each time, a simple shell script
should do the trick::

    #!/bin/sh
    ./manage.py selenium $@ --settings=myapp.selenium_settings

All the usual methods that nose uses to identify tests should work::

    directory/of/tests
    python.module
    python.module:TestClass
    python.module:TestClass.test_method
    
(Note that a specifying a package, like myapp.tests.selenium when the actual
tests are defined in modules within that package, does NOT work.)

By default, tests are run in the browser specified by ``SELENIUM_DEFAULT_BROWSER``.
You can use the ``-b`` or ``--browser`` parameter to change this::

    ./manage.py selenium -b firefox
    ./manage.py selenium --browser=safari

Valid browser names are "chrome", "firefox", "htmlunit", "ios", "opera",
"phantomjs", and "safari" ("ipad", "iphone", and "ipod" are treated as
synonyms for "ios", the form factor is chosen in Appium).  Alternatively,
tests can be run at Sauce Labs; see below for details.

You can also specify the number of times to run the tests (for example, if you
have a test that is failing intermittently for some reason and want to run it
a few times to increase the odds of encountering the error)::

    ./manage.py selenium -n 5

Sauce Labs
----------

Instead of running tests in a local browser, they can be run on one in a
virtual machine hosted at  `Sauce Labs <https://saucelabs.com/home>`_.  Support
for this in sbo-selenium is designed to play nicely with the Jenkins
`Sauce OnDemand plugin <https://saucelabs.com/jenkins>`_.  For running tests in
Jenkins, just install that plugin and configure it for the job you want to
run.  On a local machine, you'll need to set the ``SELENIUM_SAUCE_*`` Django
settings described above and use a couple of command-line parameters in
addition to the ``-b`` browser name setting mentioned previously:

* ``-p`` or ``--platform`` - The name and version of the operating system to
  use.
* ``--browser-version`` - The version number of the browser to use.

The valid values for these can be found on the
`Sauce Labs website <https://saucelabs.com/platforms>`_.

There's also a ``--tunnel-identifier`` parameter which can be used to utilize
a named Sauce Connect tunnel; this is particularly useful if you intend to run
multiple Connect instances against the same account simultaneously (like on
multiple Jenkins slave nodes).  For more about what these tunnels are and when
to use them, see the `Sauce Labs documentation <https://saucelabs.com/docs/connect#part-9>`_
on the topic.

Generating Documentation
------------------------

Documentation for this package is generated using `Sphinx <http://sphinx-doc.org/>`_
and some extensions for it from `sbo-sphinx <https://github.com/safarijv/sbo-sphinx>`_.
To generate the docs locally with any changes you may have made::

    pip install -r requirements/tests.txt
    tox -e docs
