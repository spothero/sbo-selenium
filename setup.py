#!/usr/bin/env python

import os
from pip.index import PackageFinder
from pip.req import parse_requirements
from setuptools import setup, find_packages

root_dir = os.path.abspath(os.path.dirname(__file__))
requirements_path = os.path.join(root_dir, 'requirements', 'base.txt')

finder = PackageFinder([], [])
requirements = parse_requirements(requirements_path, finder)
install_requires = [str(r.req) for r in requirements]


version = '0.4.3'  # Remember to update docs/CHANGELOG.rst when this changes

setup(
    name="sbo-selenium",
    version=version,
    packages=find_packages(),
    zip_safe=False,
    description="Selenium testing framework for Django applications",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development',
        'Topic :: Software Development :: Testing',
    ],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Jeremy Bowman',
    author_email='jbowman@safaribooksonline.com',
    url='https://github.com/safarijv/sbo-selenium',
    package_data={
        'sbo_selenium': [
            'static/js/*.js',
        ],
    },
    install_requires=install_requires,
)
