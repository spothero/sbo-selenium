sbo-selenium Changelog
======================

0.4.3 (2014-06-01)
------------------
* More robust SeleniumTestCase.click() implementation (retry until success or timeout)

0.4.2 (2014-05-20)
------------------
* Page load timeout support (default is 10 seconds, override via SELENIUM_PAGE_LOAD_TIMEOUT)
* Support for Internet Explorer Sauce OnDemand sessions

0.4.1 (2014-04-18)
------------------
* Added support for Sauce Connect tunnel identifiers
* Added the SELENIUM_SAUCE_VERSION setting to tell Sauce Labs which Selenium
  version to use
* More reliable output of Sauce OnDemand session IDs for integration with
  the Jenkins plugin
* Better redirection of error messages to configured logging (the
  SELENIUM_LOG_FILE setting is no longer needed and has been removed)

0.4.0 (2014-03-29)
------------------
* Initial public release
