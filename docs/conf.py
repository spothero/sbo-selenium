#!/usr/bin/env python
# encoding: utf-8
"""
Sphinx configuration for documentation
"""

from sbo_sphinx.conf import *

project = 'sbo-selenium'
apidoc_exclude = [
    os.path.join('docs', 'conf.py'),
    'manage.py',
    os.path.join('sbo_selenium', 'tests'),
    'setup.py',
    'test_settings.py',
    'test_urls.py',
    've',
]
