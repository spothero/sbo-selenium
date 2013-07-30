from django.core.urlresolvers import reverse

from sbo_selenium import SeleniumTestCase


class TestAccessibility(SeleniumTestCase):
    """
    Test cases for accessibility audits using code from Chrome's Accessibility
    Developer Tools extension.
    """

    def test_good_accessibility(self):
        """ A page without accessibility problems should pass the audit"""
        self.get(reverse('good_accessibility'))
        self.audit_accessibility()

    def test_poor_accessibility(self):
        """ A page with accessibility problems should fail the audit """
        self.get(reverse('poor_accessibility'))
        try:
            self.audit_accessibility()
        except self.failureException:
            pass
        else:
            raise self.failureException('Accessibility problems not detected')
