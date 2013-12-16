#!/usr/bin/env python

from setuptools import setup, find_packages


version = '0.3.9'

setup(
    name="sbo-selenium",
    version=version,
    packages=find_packages(),
    zip_safe=False,
    description="",
    long_description="""\
""",
    classifiers=[],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='',
    author_email='',
    url='',
    license='',
    package_data={
        'sbo_selenium': [
            'static/js/*.js',
        ],
    },
    install_requires=[
        'Django>=1.6.1,<1.7',
        'django-nose>=1.2',
        'selenium>=2.39.0',
    ],
    entry_points="""
    # -*- Entry points: -*-
    """,
)
