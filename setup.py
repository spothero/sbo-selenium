#!/usr/bin/env python

from setuptools import setup, find_packages


version = '0.3'

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
    include_package_data=True,
    install_requires=[
        'Django>=1.5.1,<1.6',
        'django-nose',
        'selenium',
    ],
    entry_points="""
    # -*- Entry points: -*-
    """,
)
