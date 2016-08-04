# file test_existdb/test_db.py
# -*- coding: UTF-8 -*-
#
#   Copyright 2011 Emory University Libraries
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

from contextlib import contextmanager
import unittest
import xmlrpclib
from urlparse import urlsplit, urlunsplit
from mock import patch

try:
    from unittest import skipIf
except ImportError:
    from unittest2 import skipIf

try:
    import django
    from django.conf import settings
    from django.test.utils import override_settings
except ImportError:
    django = None
    import localsettings as settings

    # supply replacement for override settings
    # NOTE: only used here as context manager, not as a decorator
    @contextmanager
    def override_settings(*args, **kwargs):
        global settings
        # patch settings
        old_vals = {}
        for key, val in kwargs.iteritems():
            old_vals[key] = getattr(settings, key, None)
            setattr(settings, key, val)

        yield

        # restore values
        for key, val in old_vals.iteritems():
            setattr(settings, key, val)


from eulexistdb import db
from eulexistdb import patch as db_patch
from eulexistdb.exceptions import ExistDBTimeout

from localsettings import EXISTDB_SERVER_URL, EXISTDB_SERVER_USER, \
    EXISTDB_SERVER_PASSWORD, EXISTDB_TEST_COLLECTION, \
    EXISTDB_SERVER_ADMIN_USER, EXISTDB_SERVER_ADMIN_PASSWORD


class ExistDBTest(unittest.TestCase):
    COLLECTION = EXISTDB_TEST_COLLECTION

    def setUp(self):
        self.db = db.ExistDB(server_url=EXISTDB_SERVER_URL,
            username=EXISTDB_SERVER_USER, password=EXISTDB_SERVER_PASSWORD)
        # separate existdb instance with dba credentials
        self.db_admin = db.ExistDB(server_url=EXISTDB_SERVER_URL,
            username=EXISTDB_SERVER_ADMIN_USER,
            password=EXISTDB_SERVER_ADMIN_PASSWORD)
        self.db.createCollection(self.COLLECTION, True)

        self.db.load('<hello>World</hello>', self.COLLECTION + '/hello.xml')

        xml = '<root><element name="one">One</element><element name="two">Two</element><element name="two">Three</element></root>'
        self.db.load(xml, self.COLLECTION + '/xqry_test.xml')

        xml = '<root><field name="one">One</field><field name="two">Two</field><field name="three">Three</field><field name="four">Four</field><unicode> ϔ ϕ ϖ Ϛ Ϝ Ϟ Ϡ Ϣ ڡ ڢ ڣ ڤ ༀ </unicode></root>'
        self.db.load(xml, self.COLLECTION + '/xqry_test2.xml')

        self.test_groups = []
        self.test_users = []

        xml = '<root xml:id="A"/>'
        self.db.load(xml, self.COLLECTION + '/xqry_test3.xml')
        self.db.load(xml, self.COLLECTION + '/xqry_test4.xml')

    def tearDown(self):
        self.db.removeCollection(self.COLLECTION)

        for group in self.test_groups:
            self.db_admin.query('sm:remove-group("%s")' % group)
        for user in self.test_users:
            self.db_admin.query('sm:remove-account("%s")' % user)

        # Start with a clean slate.
        db_patch.requested_patches = set()

    # TODO: test init with/without django.conf settings

    @skipIf(django is None, 'Requires Django')
    def test_failed_authentication_from_settings(self):
        """Check that initializing ExistDB with invalid django settings raises exception"""
        # passwords can be specified in localsettings.py
        # test bad credentials to ensure that authentication fails
        with override_settings(EXISTDB_SERVER_URLEXISTDB_SERVER_USER='bad_user',
                               EXISTDB_SERVER_PASSWORD='bad_pass'):

            test_db = db.ExistDB()
            self.assertRaises(db.ExistDBException,
                test_db.hasCollection, self.COLLECTION)

    @skipIf(django is None, 'Requires Django')
    def test_serverurl_from_djangoconf(self):
        # test constructing url based on multiple possible configurations
        if not hasattr(settings, 'EXISTDB_SERVER_USER'):
            settings.EXISTDB_SERVER_USER = 'username'
        if not hasattr(settings, 'EXISTDB_SERVER_PASSWORD'):
            settings.EXISTDB_SERVER_PASSWORD = 'pass'

        # these are irrelevant now, since not included in the url
        # user = settings.EXISTDB_SERVER_USER
        # pwd = settings.EXISTDB_SERVER_PASSWORD
        scheme, sep, host = settings.EXISTDB_SERVER_URL.partition('//')

        # username & password NOT included in xmlrpc url
        self.assertEqual(scheme + sep + host, self.db._serverurl_from_djangoconf())

        # username but no password - still NOT included in xmlrpc url
        settings.EXISTDB_SERVER_PASSWORD = None
        self.assertEqual(scheme + sep + host, self.db._serverurl_from_djangoconf())

        # no credentials
        settings.EXISTDB_SERVER_USER = None
        self.assertEqual(settings.EXISTDB_SERVER_URL, self.db._serverurl_from_djangoconf())

    def test_init_old_format(self):
        # support init with old-style xmlrpc url optionally including
        # username and password
        user = 'exister'
        password = 'tryme'
        url = 'example.com:8080/exist'
        test_db = db.ExistDB('http://%s:%s@%s/xmlrpc' % (user, password, url))

        self.assertEqual(user, test_db.username)
        self.assertEqual(password, test_db.password)
        self.assertEqual('http://%s' % url, test_db.exist_url)

        # specified username/password args shoudl override xmlrpc url
        override_user = 'existentialist'
        override_password = 'sartre'
        test_db = db.ExistDB('http://%s:%s@%s/xmlrpc' % (user, password, url),
                             username=override_user, password=override_password)
        self.assertEqual(override_user, test_db.username)
        self.assertEqual(override_password, test_db.password)
        self.assertEqual('http://%s' % url, test_db.exist_url)

        # no username/password
        test_db = db.ExistDB('http://%s/xmlrpc' % (url))
        self.assertEqual(None, test_db.username)
        self.assertEqual(None, test_db.password)
        self.assertEqual('http://%s' % url, test_db.exist_url)

        # no port, ssl
        url = 'example.com/exist'
        test_db = db.ExistDB('https://%s/xmlrpc' % (url))
        self.assertEqual('https://%s' % url, test_db.exist_url)




    def test_getDocument(self):
        """Test retrieving a full document from eXist"""
        xml = self.db.getDocument(self.COLLECTION + "/hello.xml")
        self.assertEquals(xml, "<hello>World</hello>")

        self.assertRaises(Exception, self.db.getDocument, self.COLLECTION + "/notarealdoc.xml")

    def test_getDoc(self):
        """Test retrieving a full document from eXist (legacy function name for getDocument)"""
        xml = self.db.getDoc(self.COLLECTION + "/hello.xml")
        self.assertEquals(xml, "<hello>World</hello>")


    def test_hasDocument(self):
        """Test that document existence can be determined in eXist"""
        #test document loaded in setup
        self.assertTrue(self.db.hasDocument(self.COLLECTION + "/hello.xml"),
            "hasDocument failed to return true for existing collection")
        #test non-existent file in test collection
        self.assertFalse(self.db.hasDocument(self.COLLECTION + "/nonexistent.xml"),
            "hasDocument failed to return false for non-existent file")
        #test non-existent file in bogus collection
        self.assertFalse(self.db.hasDocument("/bogus/nonexistent.xml"),
            "hasDocument failed to return false for non-existent file in non-existent collection")

    def test_describeDocument(self):
        desc = self.db.describeDocument(self.COLLECTION + '/hello.xml')
        self.assertEqual(self.COLLECTION + "/hello.xml", desc['name'])
        self.assertEqual("application/xml", desc['mime-type'])
        self.assertEqual("XMLResource", desc['type'])
        self.assert_('owner' in desc)
        self.assert_('group' in desc)
        self.assert_('content-length' in desc)
        self.assert_('created' in desc)
        self.assert_('modified' in desc)
        self.assert_('permissions' in desc)

        self.assertEqual({}, self.db.describeDocument("/nonexistent.xml"))

    def test_removeDocument(self):
        "Test removing a full document from eXist"
        result = self.db.removeDocument(self.COLLECTION + "/hello.xml")
        self.assertTrue(result)
        # attempting to retrieve the deleted file should cause an exception
        self.assertRaises(Exception, self.db.getDocument, self.COLLECTION + "/hello.xml")

    def test_moveDocument(self):
        "Test moving a document from one eXist collection to another"
        new_collection = '%s-tmp' % self.COLLECTION
        self.db.createCollection(new_collection, True)
        self.db.moveDocument(self.COLLECTION, new_collection, 'hello.xml')

        self.assertEqual({}, self.db.describeDocument('%s/hello.xml' % self.COLLECTION),
            "describeDocument returns nothing for document in original collection after move")
        new_name = '%s/hello.xml' % new_collection
        desc = self.db.describeDocument(new_name)
        self.assertEqual(desc['name'], new_name,
            "describeDocument returns details for document in new location after move")

        # move to a non-existent colletion
        self.assertRaises(Exception, self.db.moveDocument, self.COLLECTION,
            'my/bogus/collection', 'xqry_test.xml')

        # move from a non-existent collection
        self.assertRaises(Exception, self.db.moveDocument, 'my/bogus/collection',
            new_collection, 'hello.xml')

        # move a non-existent file
        self.assertRaises(Exception, self.db.moveDocument, self.COLLECTION,
            new_collection, 'not-here.xml')

        # remove temporary collection where document was moved
        self.db_admin.removeCollection(new_collection)

    def test_hasCollection(self):
        """Check collections can be found in eXist"""
        #test collection created in setup
        self.assertTrue(self.db.hasCollection(self.COLLECTION), "hasCollection failed to return true for existing collection")
        #test bad collection that does not exist
        self.assertFalse(self.db.hasCollection("/nonexistingCollecton"), "hasCollection failed to return false for non-existing collection")

    def test_getCollectionDescription(self):
        """Test retrieving information about a collection in eXist"""
        info = self.db.getCollectionDescription(self.COLLECTION)

        self.assertEqual("/db" + self.COLLECTION, info['name'],
            "collection name returned (expected '/db/%s', got '%s'" % (self.COLLECTION, info['name']))
        self.assertEqual(EXISTDB_SERVER_USER, info['owner'],
            "collection owner returned (expected '%s', got %s" % \
                (EXISTDB_SERVER_USER, info['owner']))
        # untested - group, created, permissions
        self.assertEqual(5, len(info['documents']), "collection has 5 documents (5 test documents loaded)")
        self.assertEqual([], info['collections'], "collection has no subcollections")

        # attempting to describe a collection that isn't in the db
        self.assertRaises(db.ExistDBException, self.db.getCollectionDescription,
            "bogus_collection")

    def test_createCollection(self):
        """Test creating new collections in eXist"""
        #create new collection
        self.assertTrue(self.db.createCollection(self.COLLECTION + "/new_collection"),
            "failed to create new collection")

        #attempt create collection again expects ExistDBException
        self.assertRaises(db.ExistDBException,
            self.db.createCollection, self.COLLECTION + "/new_collection")

        #create new collection again with over_write = True
        self.assertTrue(self.db.createCollection(self.COLLECTION + "/new_collection", True),
            "failed to create new collection with over_write")

    def test_removeCollection(self):
        """Test removing collections from eXist"""
        #attempt to remove non-existent collection expects ExistDBException
        self.assertRaises(db.ExistDBException,
            self.db.removeCollection, self.COLLECTION + "/newer_collection")

        #create collection to test removal
        self.db.createCollection(self.COLLECTION + "/new_collection")
        self.assertTrue(self.db.removeCollection(self.COLLECTION + "/new_collection"), "removeCollection failed to remove existing collection")

    def test_query(self):
        """Test xquery results with hits & count"""
        xqry = 'for $x in collection("/db%s")//root/element where $x/@name="two" return $x' % (self.COLLECTION, )
        qres = self.db.query(xqry)
        self.assertEquals(qres.hits, 2)
        self.assertEquals(qres.start, 1)
        self.assertEquals(qres.count, 2)

        self.assertEquals(qres.results[0].xpath('string()'), 'Two')
        self.assertEquals(qres.results[1].xpath('string()'), 'Three')

        # retrieve unicode content unchanged
        xqry = 'collection("/db%s")//root[unicode]' % (self.COLLECTION, )
        qres = self.db.query(xqry)
        unicode_str = u' ϔ ϕ ϖ Ϛ Ϝ Ϟ Ϡ Ϣ ڡ ڢ ڣ ڤ ༀ '
        self.assertEquals(qres.results[0].xpath('unicode/text()')[0],
            unicode_str)
        # query on unicode does not currently return results
        # xqry = u'collection("/db%s")//root[contains(unicode, "%s")]' % (self.COLLECTION, unicode_str)
        # qres = self.db.query(xqry)
        # self.assertEquals(qres.hits, 1)

    def test_query_duplicate_ids(self):
        """
        Test xquery with duplicate IDs in result. A query that returns
        multiple XML documents that have the same xml:id value
        appearing in them should not result in a query failure.
        """
        xqry = 'for $x in collection("/db%s")//root[@xml:id] return $x' % (
            self.COLLECTION, )
        qres = self.db.query(xqry)
        self.assertEquals(qres.hits, 2)

    def test_query_bad_xqry(self):
        """Check that an invalid xquery raises an exception"""
        #invalid xqry missing "
        xqry = 'for $x in collection("/db%s")//root/element where $x/@name=two" return $x' % (self.COLLECTION, )
        self.assertRaises(db.ExistDBException,
            self.db.query, xqry)

    def test_query_with_no_result(self):
        """Test xquery with no results"""
        xqry = 'for $x in collection("/db%s")/root/field where $x/@name="notfound" return $x' % (self.COLLECTION, )
        qres = self.db.query(xqry)

        self.assertTrue(qres.hits is not None)
        self.assertTrue(qres.count is not None)

        self.assertFalse(qres.hits, 0)
        self.assertEquals(qres.count, 0)
        self.assertEquals(qres.start, 1)
        # NOTE: this is a change from exist 1.4.x, was unset/None previously

        self.assertFalse(qres.results)

    def test_executeQuery(self):
        """Test executeQuery & dependent functions (querySummary, getHits, retrieve)"""
        xqry = 'for $x in collection("/db%s")/root/element where $x/@name="two" return $x' % (self.COLLECTION, )
        result_id = self.db.executeQuery(xqry)
        self.assert_(isinstance(result_id, int), "executeQuery returns integer result id")

        # run querySummary on result from executeQuery
        summary = self.db.querySummary(result_id)
        self.assertEqual(2, summary['hits'], "querySummary returns correct hit count of 2")
        self.assert_(isinstance(summary['queryTime'], int), "querySummary return includes int queryTime")
        # any reasonable way to check what is in the documents summary info?
        # documents should be an array of arrays - document name, id, and # hits

        # getHits on result
        hits = self.db.getHits(result_id)
        self.assert_(isinstance(hits, int), "getHits returns integer hit count")
        self.assertEqual(2, hits, "getHits returns correct count of 2")

        # retrieve first result
        result = self.db.retrieve(result_id, 0)
        self.assertEqual('<element name="two">Two</element>', result,
                "retrieve index 0 returns first element with @name='two'")
        # retrieve second result
        result = self.db.retrieve(result_id, 1)
        self.assertEqual('<element name="two">Three</element>', result,
                "retrieve index 0 returns first element with @name='two'")

    def test_executeQuery_noresults(self):
        """Test executeQuery & dependent functions (querySummary, getHits, retrieve) - xquery with no results"""
        xqry = 'collection("/db%s")/root/element[@name="bogus"]' % (self.COLLECTION, )
        result_id = self.db.executeQuery(xqry)
        # run querySummary on result from executeQuery
        summary = self.db.querySummary(result_id)
        self.assertEqual(0, summary['hits'], "querySummary returns hit count of 0")
        self.assertEqual([], summary['documents'], "querySummary document list is empty")

        # getHits
        hits = self.db.getHits(result_id)
        self.assertEqual(0, hits, "getHits returns correct count of 0 for query with no match")

        # retrieve non-existent result
        self.assertRaises(db.ExistDBException, self.db.retrieve, result_id, 0)

    def test_executeQuery_bad_xquery(self):
        """Check that an invalid xquery raises an exception"""
        #invalid xqry missing "
        xqry = 'collection("/db%s")//root/element[@name=two"]' % (self.COLLECTION, )
        self.assertRaises(db.ExistDBException, self.db.executeQuery, xqry)

    def test_releaseQuery(self):
        xqry = 'collection("/db%s")/root/element[@name="two"]' % (self.COLLECTION, )
        result_id = self.db.executeQuery(xqry)
        self.db.releaseQueryResult(result_id)
        # attempting to get data from a result that has been released should cause an error
        self.assertRaises(Exception, self.db.getHits, result_id)

    def test_load(self):
        dbpath = '%s/test-load.xml' % self.COLLECTION
        # create
        # NOTE: exist returns indented xml; creating string to match
        xml = '''<root>
    <element/>
</root>'''
        # load should return True on success
        self.assertTrue(self.db.load(xml, dbpath))
        self.assertEqual(xml, self.db.getDocument(dbpath))
        # update
        xml = '''<root>
    <element>value</element>
</root>'''
        self.assertTrue(self.db.load(xml, dbpath))
        self.assertEqual(xml, self.db.getDocument(dbpath))

    def test_load_invalid_xml(self):
        """Check that loading invaliid xml raises an exception"""
        xml = '<root><element></root>'
        self.assertRaises(db.ExistDBException,
            self.db.load, xml, self.COLLECTION + 'invalid.xml')

    def test_failed_authentication(self):
        """Check that connecting with invalid user credentials raises an exception"""
        parts = urlsplit(EXISTDB_SERVER_URL)
        netloc = 'bad_user:bad_password@' + parts.hostname
        if parts.port:
            netloc += ':' + str(parts.port)
        bad_uri = urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))

        test_db = db.ExistDB(server_url=bad_uri)
        self.assertRaises(db.ExistDBException,
                test_db.hasCollection, self.COLLECTION)

    def test_configCollectionName(self):
        self.assertEqual("/db/system/config/db/foo", self.db._configCollectionName("foo"))
        self.assertEqual("/db/system/config/db/foo", self.db._configCollectionName("/foo"))
        self.assertEqual("/db/system/config/db/foo", self.db._configCollectionName("/foo/"))
        self.assertEqual("/db/system/config/db/foo/bar", self.db._configCollectionName("/foo/bar"))

    def test_collectionIndexPath(self):
        self.assertEqual("/db/system/config/db/foo/collection.xconf", self.db._collectionIndexPath("foo"))

    def test_loadCollectionIndex(self):
        """Test loading a collection index config file to the system config collection."""
        self.db.loadCollectionIndex(self.COLLECTION, "<collection/>")
        self.assert_(self.db.hasCollection(self.db._configCollectionName(self.COLLECTION)))
        xml = self.db.getDocument(self.db._collectionIndexPath(self.COLLECTION))
        self.assertEquals(xml, "<collection/>")

        # NOTE: rest api assumes overwrite, so this behavior is different now
        # reload with overwrite disabled - should cause an exception
        # self.assertRaises(db.ExistDBException, self.db.loadCollectionIndex,
        #     self.COLLECTION, "<collection/>", False)

        # clean up
        self.db_admin.removeCollection(self.db._configCollectionName(self.COLLECTION))

    def test_removeCollectionIndex(self):
        """Test removing a collection index config file from the system config collection."""
        self.db.loadCollectionIndex(self.COLLECTION, "<collection/>")

        self.assertTrue(self.db.removeCollectionIndex(self.COLLECTION))
        # collection index configuration should not be loaded
        self.assertRaises(db.ExistDBException, self.db.getDocument,
            self.db._collectionIndexPath(self.COLLECTION))
        self.assertFalse(self.db.hasCollection(self.db._configCollectionName(self.COLLECTION)),
            "config collection should have been removed from eXist")

        self.db.loadCollectionIndex(self.COLLECTION, "<collection/>")
        self.db.createCollection(self.db._configCollectionName(self.COLLECTION) + "/subcollection")
        self.assertTrue(self.db.removeCollectionIndex(self.COLLECTION))
        # NOTE: getDocument on nonexistent file actually raises exception here because collection exists (?)
        self.assertRaises(Exception, self.db.getDocument, self.db._collectionIndexPath(self.COLLECTION))
        self.assertTrue(self.db.hasCollection(self.db._configCollectionName(self.COLLECTION)),
            "config collection should not be removed when it contains documents")

        # clean up
        self.db_admin.removeCollection(self.db._configCollectionName(self.COLLECTION))

    def test_hasCollectionIndex(self):
        # ensure no config collection is present
        if self.db.hasCollection(self.db._configCollectionName(self.COLLECTION)):
            self.db.removeCollection(self.db._configCollectionName(self.COLLECTION))
        self.assertFalse(self.db.hasCollectionIndex(self.COLLECTION),
            "hasCollectionIndex failed to return false for collection with no config collection")

        # load test config collection
        self.db.loadCollectionIndex(self.COLLECTION, "<collection/>")
        self.assertTrue(self.db.hasCollectionIndex(self.COLLECTION),
            "hasCollectionIndex failed to return True for collection with config file loaded")

        # remove config file but leave config collection
        self.db.removeDocument(self.db._collectionIndexPath(self.COLLECTION))
        self.assertFalse(self.db.hasCollectionIndex(self.COLLECTION),
            "hasCollectionIndex failed to return false for collection with config collection but no config file")

    def test_reindexCollection(self):
        # guest account - permission denied
        self.assertFalse(self.db.reindexCollection('/db' + self.COLLECTION),
            "reindex should fail - guest account does not have permission to reindex collection")
        # dba account
        self.assertTrue(self.db_admin.reindexCollection('/db' + self.COLLECTION),
            "reindex with exist dba user should succeed")
        # full or short version of collection name
        self.assertTrue(self.db_admin.reindexCollection(self.COLLECTION),
            "reindex with exist dba user and collection name without leading '/db/' should succeed")
        # non-existent collection
        self.assertRaises(db.ExistDBException, self.db.reindexCollection, "notacollection")

    def test_getPermissions(self):
        perms = self.db.getPermissions('/db' + self.COLLECTION + '/hello.xml')
        self.assert_(isinstance(perms, db.ExistPermissions))
        self.assertEqual(EXISTDB_SERVER_USER, perms.owner)
        self.assertEqual(EXISTDB_SERVER_USER, perms.group)
        # self.assertEqual(493, perms.permissions)    # FIXME: will this always be true?
        self.assertEqual(420, perms.permissions)    # default in exist 2.2

    def test_setPermissions(self):
        # documentation still says this syntax is supported:
        # self.db_admin.setPermissions('/db' + self.COLLECTION + '/hello.xml', 'other=-update')
        # but it errors with "Unrecognised mode syntax"
        self.db_admin.setPermissions('/db' + self.COLLECTION + '/hello.xml', 492)
        perms = self.db.getPermissions('/db' + self.COLLECTION + '/hello.xml')
        self.assertEqual(492, perms.permissions)

    def test_timeout(self):
        # set timeout low to confirm timeout exception is raised
        timeoutdb = db.ExistDB(server_url=EXISTDB_SERVER_URL,
                               timeout=1)
        self.assertRaises(ExistDBTimeout, timeoutdb.query, 'util:wait(10000)')

        # use mocks to test initialization/timeout parameters
        with patch('eulexistdb.db.socket') as mocksocket:
            timeout_server = 'http://nonexistent/exist:8080/timeout'
            # default timeout
            timeoutdb = db.ExistDB(server_url=timeout_server)
            mocksocket.getdefaulttimeout.assert_called_with()
            mocksocket.reset_mock()

            # timeout specified
            with patch('eulexistdb.db.requests') as mockrequests:
                timeout = 3
                timeoutdb = db.ExistDB(server_url=timeout_server,
                                       timeout=timeout)
                mocksocket.getdefaulttimeout.assert_not_called()

                # session options used for rest api should have timeout set
                self.assertEqual(timeout, timeoutdb.session_opts['timeout'])
                # xmlrpc transport should use requested timeout
                xmlrpc_session = mockrequests.Session.return_value
                # requires a valid xmlrpc response or unmarshalling fails
                xmlrpc_session.post.return_value.text = '''<methodResponse>
                <params><param/></params></methodResponse>'''
                timeoutdb.server.ping()
                args, kwargs = xmlrpc_session.post.call_args
                self.assertEqual(timeout, kwargs['timeout'])

    @skipIf(django is None, 'Requires Django')
    def test_django_timeout(self):
        # use mocks to test initialization/timeout parameters
        with patch('eulexistdb.db.socket') as mocksocket:
            timeout_server = 'http://nonexistent/exist:8080/timeout'

            with patch('eulexistdb.db.requests') as mockrequests:

                # test init via django settings
                django_timeout = 4
                with override_settings(EXISTDB_TIMEOUT=django_timeout):
                    # no timeout specified, should use settings
                    timeoutdb = db.ExistDB(server_url=timeout_server)
                    mocksocket.getdefaulttimeout.assert_not_called()

                    # xmlrpc transport should use requested timeout
                    xmlrpc_session = mockrequests.Session.return_value
                    # requires a valid xmlrpc response or unmarshalling fails
                    xmlrpc_session.post.return_value.text = '''<methodResponse>
                    <params><param/></params></methodResponse>'''

                    # session used for rest api should use django timeout
                    self.assertEqual(django_timeout,
                                     timeoutdb.session_opts['timeout'])
                    # xmlrpc transport should use django timeout
                    timeoutdb.server.ping()
                    args, kwargs = xmlrpc_session.post.call_args
                    self.assertEqual(django_timeout, kwargs['timeout'])

                    # explicit None should take precedence over django settings
                    no_timeout = None
                    timeoutdb = db.ExistDB(server_url=EXISTDB_SERVER_URL,
                                           timeout=no_timeout)
                    self.assertEqual(no_timeout,
                                     timeoutdb.session_opts['timeout'])
                    timeoutdb.server.ping()
                    args, kwargs = xmlrpc_session.post.call_args
                    self.assertEqual(no_timeout, kwargs['timeout'])

    def test_create_account(self):
        self.test_users.append('foo')
        self.test_groups.append('foo')
        # admin should be able to create a user
        self.assertTrue(self.db_admin.create_account('foo', 'pass', 'foo'))
        # trying to create same account again should return false
        self.assertFalse(self.db_admin.create_account('foo', 'pass', 'foo'))
        # non-admin should not be able to create an account
        self.assertRaises(db.ExistDBException, self.db.create_account,
                          'nodice', 'pass', 'nodice')

    def test_create_group(self):
        self.test_groups.append('foo')
        # admin should be able to create a group
        self.assertTrue(self.db_admin.create_group('foo'))
        # trying to create same group again should return false
        self.assertFalse(self.db_admin.create_group('foo'))
        # non-admin should not be able to create an account
        self.assertRaises(db.ExistDBException, self.db.create_group,
                          'not-a-group')

    def test_xmlrpclib_failure_without_patch(self):
        """
        Test that without the XMLRpcLibPatch, we get a failure when
        xmlrpclib tries to parse a response that contains Apache's
        extended types.
        """
        self.assertTrue(self.db_admin.create_group('foo'))
        # The group is actually removed but the response cannot be parsed.
        self.assertRaises(xmlrpclib.ResponseError,
                          self.db_admin.server.removeGroup, 'foo')

    def test_xmlrpclib_failure_without_patch(self):
        """
        Test that without the XMLRpcLibPatch, we get a failure when
        xmlrpclib tries to parse a response that contains Apache's
        extended types.
        """
        db_patch.request_patching(db_patch.XMLRpcLibPatch)
        self.assertTrue(self.db_admin.create_group('foo'))
        # The group is actually removed but the response cannot be parsed.
        self.db_admin.server.removeGroup('foo')
