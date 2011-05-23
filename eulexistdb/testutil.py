# file eulexistdb/testutil.py
# 
#   Copyright 2010,2011 Emory University Libraries
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
"""
:mod:`eulexistdb.testutil` provides utilities for writing and running
tests against code that makes use of :mod:`eulexistdb`.  This module
includes a customization of :class:`django.test.TestCase` with
eXist-db fixture handling, and custom test suite runners with Fedora
environment setup / teardown for all tests.

To use, configure as test runner in your Django settings::

   TEST_RUNNER = 'eulexistdb.testutil.ExistDBTestSuiteRunner'

When :mod:`xmlrunner` is available, xmlrunner variants are also
available.  To use this test runner, configure your test runner as
follows::

    TEST_RUNNER = 'eulexistdb.testutil.ExistDBXmlTestSuiteRunner'

The xml variant honors the same django settings that the xmlrunner
django testrunner does (TEST_OUTPUT_DIR, TEST_OUTPUT_VERBOSE, and
TEST_OUTPUT_DESCRIPTIONS).

Any :class:`~eulexistdb.db.ExistDB` instances created after the test
suite starts will automatically connect to the test collection. 

----

"""


from glob import glob
import logging
from os import path
import re
import unittest2 as unittest

from django.test import TestCase as DjangoTestCase
from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings

from eulexistdb.db import ExistDB, ExistDBException

logger = logging.getLogger(__name__)


class TestCase(DjangoTestCase):
    """Customization of :class:`django.test.TestCase`

    If TestCase instance has an attribute named ``exist_fixtures``, the
    specified fixtures will be loaded to eXist before the tests run.
    
    The ``exist_fixtures`` attribute should be a dictionary with information
    about fixtures to load to eXist. Currently supported options:

    * *index* - path to an eXist index configuration file; will be loaded before
      any other fixture files, and removed in fixture teardown
    * *directory* - path to a fixture directory; all .xml files in the directory
      will be loaded to eXist
    * *files* - list of files to be loaded (filenames should include path)

    """

    def assertPattern(self, regex, text, msg_prefix=''):
        """Assert that a string matches a regular expression (regex compiled as multiline).
           Allows for more flexible matching than the django assertContains.
         """
        if msg_prefix != '':
            msg_prefix += '.  '
        self.assert_(re.search(re.compile(regex, re.DOTALL), text),
        msg_prefix + "Should match '%s'" % regex)

    def _fixture_setup(self):
        if hasattr(self, 'exist_fixtures'):
            db = ExistDB()
            # load index
            if 'index' in self.exist_fixtures:
                db.loadCollectionIndex(settings.EXISTDB_ROOT_COLLECTION,
                        open(self.exist_fixtures['index']))
            if 'directory' in self.exist_fixtures:
                for file in glob(path.join(self.exist_fixtures['directory'], '*.xml')):
                    self._load_file_to_exist(file)
            if 'files' in self.exist_fixtures:
                for file in self.exist_fixtures['files']:
                    self._load_file_to_exist(file)

        return super(TestCase, self)._fixture_setup()

    def _fixture_teardown(self):
        if hasattr(self, 'exist_fixtures'):
            db = ExistDB()
            if 'index' in self.exist_fixtures:
                db.removeCollectionIndex(settings.EXISTDB_ROOT_COLLECTION)
            if 'directory' in self.exist_fixtures:
                for file in glob(path.join(self.exist_fixtures['directory'], '*.xml')):
                    self._remove_file_from_exist(file)
            if 'files' in self.exist_fixtures:
                for file in self.exist_fixtures['files']:
                    self._remove_file_from_exist(file)

        return super(TestCase, self)._fixture_teardown()

    def _load_file_to_exist(self, file):
        db = ExistDB()
        fname = path.split(file)[-1]
        exist_path= path.join(settings.EXISTDB_ROOT_COLLECTION, fname)
        db.load(open(file), exist_path, True)

    def _remove_file_from_exist(self, file):
        db = ExistDB()
        fname = path.split(file)[-1]
        exist_path= path.join(settings.EXISTDB_ROOT_COLLECTION, fname)
        # tests could remove fixtures, so an exception here is not a problem
        try:
            db.removeDocument(exist_path)
        except ExistDBException:
            # any way to determine if error ever needs to be reported?
            pass



class ExistDBTestResult(unittest.TextTestResult):
    '''Extend :class:`unittest2.TextTestResult` to take advantage of
    :meth:`~unittest2.TestResult.startTestRun` and
    :meth:`~unittest2.TestResult.stopTestRun` to do environmental test
    setup and teardown before and after all tests run.
    '''
    _stored_default_collection = None

    def startTestRun(self):
        '''Switch Django settings for EXIST access to test
        configuration, and load any repository fixtures (such as
        content models or initial objects).'''
        super(ExistDBTestResult, self).startTestRun()
        self._use_test_collection()

    def stopTestRun(self):
        '''Switch Django settings for EXIST access out of test
        configuration and back into normal settings, and do any 
        necessary clean up.'''
        self._restore_root_collection()
        super(ExistDBTestResult, self).stopTestRun()

    def _use_test_collection(self):    
        self._stored_default_collection = getattr(settings, "EXISTDB_ROOT_COLLECTION", None)

        if getattr(settings, "EXISTDB_TEST_COLLECTION", None):
            settings.EXISTDB_ROOT_COLLECTION = settings.EXISTDB_TEST_COLLECTION
        else:
            settings.EXISTDB_ROOT_COLLECTION = getattr(settings, "EXISTDB_ROOT_COLLECTION", "/default") + "_test"

        print "Creating eXist Test Collection: %s" % settings.EXISTDB_ROOT_COLLECTION
        # now that existdb root collection has been set to test collection, init db connection
        db = ExistDB()
        # create test collection (don't complain if collection already exists)
        db.createCollection(settings.EXISTDB_ROOT_COLLECTION, True)

    def _restore_root_collection(self):
        # if use_test_collection didn't run, don't change anything
        if self._stored_default_collection is not None:
            print "Removing eXist Test Collection: %s" % settings.EXISTDB_ROOT_COLLECTION
            # before restoring existdb non-test root collection, init db connection
            db = ExistDB()
            try:            
                # remove test collection
                db.removeCollection(settings.EXISTDB_ROOT_COLLECTION)
            except ExistDBException, e:
                print "Error removing collection ", settings.EXISTDB_ROOT_COLLECTION, ': ', e

            print "Restoring eXist Root Collection: %s" % self._stored_default_collection
            settings.EXISTDB_ROOT_COLLECTION = self._stored_default_collection

class ExistDBTestSuiteRunner(DjangoTestSuiteRunner):
    '''Extend :class:`~django.test.simple.DjangoTestSuiteRunner` to use
    :class:`ExistDBTestResult` as the result class.'''
    
    def run_suite(self, suite, **kwargs):
        # call the exact same way that django does, with the addition of our resultclass
        return unittest.TextTestRunner(resultclass=ExistDBTestResult,
                                       verbosity=self.verbosity, failfast=self.failfast).run(suite)

try:
    # when xmlrunner is available, define xmltest variants

    import xmlrunner
    
    class ExistDBXmlTestResult(xmlrunner._XMLTestResult, ExistDBTestResult):
        # xml test result logic with our custom startTestRun/stopTestRun
        def __init__(self, **kwargs):
            # sort out kwargs for the respective init methods;
            # need to call both so everything is set up properly
            testrunner_args = dict((key, val) for key, val in kwargs.iteritems()
                                   if key in ['stream', 'descriptions', 'verbosity'])
            ExistDBTestResult.__init__(self, **testrunner_args)

            xmlargs = dict((key, val) for key, val in kwargs.iteritems() if
                           key in ['stream', 'descriptions', 'verbosity', 'elapsed_times'])
            xmlrunner._XMLTestResult.__init__(self, **xmlargs)
            
    class ExistDBXmlTestRunner(xmlrunner.XMLTestRunner):
        # XMLTestRunner doesn't currently take a resultclass init option;
        # extend make_result to override test result class that will be used
        def _make_result(self):
            """Create the TestResult object which will be used to store
            information about the executed tests.
            """
            return ExistDBXmlTestResult(stream=self.stream, descriptions=self.descriptions, \
                                       verbosity=self.verbosity, elapsed_times=self.elapsed_times)
    
    class ExistDBXmlTestSuiteRunner(DjangoTestSuiteRunner):
        '''Extend :class:`~django.test.simple.DjangoTestSuiteRunner` to use
        :class:`FedoraTestResult` as the result class.'''
        # combination of DjangoTestSuiteRunner with xmlrunner django test runner variant
        
        def run_suite(self, suite, **kwargs):
            # pick up settings as expected by django xml test runner
            settings.DEBUG = False
            verbose = getattr(settings, 'TEST_OUTPUT_VERBOSE', False)
            descriptions = getattr(settings, 'TEST_OUTPUT_DESCRIPTIONS', False)
            output = getattr(settings, 'TEST_OUTPUT_DIR', '.')

            # call roughly the way that xmlrunner does, with our customized test runner
            return ExistDBXmlTestRunner(verbose=verbose, descriptions=descriptions,
                                       output=output).run(suite)

except ImportError:
    pass
