#!/usr/bin/env python
from setuptools import setup, find_packages
import sys

from eulexistdb import __version__

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Framework :: Django',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Topic :: Text Processing :: Markup :: XML',
]

LONG_DESCRIPTION = None
try:
    # read the description if it's there
    with open('README.rst') as desc_f:
        LONG_DESCRIPTION = desc_f.read()
except:
    pass

# test reqs does *not* include django to allow testing without django
# and against multiple versions of django
test_requirements = [
    'sphinx',
    'nose',
    'coverage',
    'tox',
    'mock'
]

# unittest2 should only be included for py2.6
if sys.version_info < (2, 7):
    # optional testrunner in testutil
    test_requirements.append('unittest2')

dev_requirements = test_requirements + ['Django', 'django-debug-toolbar']


setup(
    name='eulexistdb',
    version=__version__,
    author='Emory University Libraries',
    author_email='libsysdev-l@listserv.cc.emory.edu',
    url='https://github.com/emory-libraries/eulexistdb',
    license='Apache License, Version 2.0',
    packages=find_packages(),
    install_requires=[
        'requests',
        'eulxml>=1.1.2',
    ],
    extras_require={
        'django': ['Django'],
        'dev': dev_requirements,
        'test': test_requirements
    },
    description='Idiomatic access to the eXist-db XML Database using XPath and XQuery',
    long_description=LONG_DESCRIPTION,
    classifiers=CLASSIFIERS,
    keywords='eXist-db XQuery',
    include_package_data=True,
    package_data={'eulexistdb': ['eulexistdb/templates/eulexistdb/*.html']},
)
