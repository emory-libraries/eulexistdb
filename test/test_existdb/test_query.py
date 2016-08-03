# file test_existdb/test_query.py
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

from datetime import datetime
import unittest

from eulxml import xmlmap
from eulexistdb.db import ExistDB
from eulexistdb.exceptions import DoesNotExist
from eulexistdb.exceptions import ReturnedMultiple
from eulexistdb.query import QuerySet, Xquery, XmlQuery
from test_existdb.test_db import EXISTDB_SERVER_URL
from localsettings import EXISTDB_SERVER_URL, EXISTDB_SERVER_USER, \
    EXISTDB_SERVER_PASSWORD, EXISTDB_TEST_COLLECTION


class QuerySubModel(xmlmap.XmlObject):
    subname = xmlmap.StringField("subname")
    ssc = xmlmap.NodeField('subsubclass', xmlmap.XmlObject)


class QueryTestModel(xmlmap.XmlObject):
    ROOT_NAMESPACES = {'ex': 'http://example.com/'}
    id = xmlmap.StringField('@id')
    name = xmlmap.StringField('name')
    description = xmlmap.StringField('description')
    wnn = xmlmap.IntegerField('wacky_node_name')
    sub = xmlmap.NodeField("sub", QuerySubModel)
    or_field = xmlmap.StringField('name|description|@id')
    substring = xmlmap.StringField('substring(name, 1, 1)')
    nsfield = xmlmap.StringField('ex:field')
    years = xmlmap.StringListField('year')

COLLECTION = EXISTDB_TEST_COLLECTION

FIXTURE_ONE = '''
    <root id="one" xmlns:ex='http://example.com/'>
        <name>one</name>
        <description>this one has one one
        </description>

        <wacky_node_name>42</wacky_node_name>
        <sub>
           <subname>la</subname>
        </sub>
        <ex:field>namespaced</ex:field>
        <year>2001</year>
        <year>2000</year>
    </root>
'''
FIXTURE_TWO = '''
    <root id="abc">
        <name>two</name>
        <description>this one only has two</description>
        <year>1990</year>
        <year>1999</year>
        <year>2013</year>
    </root>
'''
FIXTURE_THREE = '''
    <root id="xyz">
        <name>three</name>
        <description>third!</description>
        <year>2010</year>
    </root>
'''
FIXTURE_FOUR = '''
    <root id="def">
        <name>four</name>
        <description>This one contains "quote" and &amp;!</description>
    </root>
'''
NUM_FIXTURES = 4


def load_fixtures(db):
    db.createCollection(COLLECTION, True)

    db.load(FIXTURE_ONE, COLLECTION + '/f1.xml')
    db.load(FIXTURE_TWO, COLLECTION + '/f2.xml')
    db.load(FIXTURE_THREE, COLLECTION + '/f3.xml')
    db.load(FIXTURE_FOUR, COLLECTION + '/f4.xml')


class ExistQueryTest(unittest.TestCase):

    def setUp(self):
        self.db = ExistDB(server_url=EXISTDB_SERVER_URL,
            username=EXISTDB_SERVER_USER, password=EXISTDB_SERVER_PASSWORD)
        load_fixtures(self.db)
        self.qs = QuerySet(using=self.db, xpath='/root', collection=COLLECTION, model=QueryTestModel)

    def tearDown(self):
        self.db.removeCollection(COLLECTION)
        # release any queryset sessions before test user account
        # is removed in module teardown
        del self.qs

    def test_count(self):
        load_fixtures(self.db)
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "queryset count returns number of fixtures")

    def test_getitem(self):
        qs = self.qs.order_by('id')     # adding sort order to test reliably
        self.assertEqual("abc", qs[0].id)
        self.assertEqual("def", qs[1].id)
        self.assertEqual("one", qs[2].id)
        self.assertEqual("xyz", qs[3].id)

        # test getting single item beyond initial set
        qs = self.qs.order_by('id')
        # load initial result cache
        self.assertEqual("abc", qs[0].id)
        # retrieve individual items beyond the current cache
        self.assertEqual("one", qs[2].id)
        self.assertEqual("xyz", qs[3].id)

    def test_getitem_typeerror(self):
        self.assertRaises(TypeError, self.qs.__getitem__, "foo")

    def test_getitem_indexerror(self):
        self.assertRaises(IndexError, self.qs.__getitem__, -1)
        self.assertRaises(IndexError, self.qs.__getitem__, 23)

    def test_getslice(self):
        slice = self.qs.order_by('id')[0:2]
        self.assert_(isinstance(slice, QuerySet))
        self.assert_(isinstance(slice[0], QueryTestModel))
        self.assertEqual(2, slice.count())
        self.assertEqual(2, len(slice))

        self.assertEqual('abc', slice[0].id)
        self.assertEqual('def', slice[1].id)
        self.assertRaises(IndexError, slice.__getitem__, 2)

        slice = self.qs.order_by('id')[1:3]
        self.assertEqual('def', slice[0].id)
        self.assertEqual('one', slice[1].id)

        slice = self.qs.order_by('id')[3:5]
        self.assertEqual(1, slice.count())
        self.assertEqual('xyz', slice[0].id)
        self.assertRaises(IndexError, slice.__getitem__, 1)

        # test slicing with unspecified bounds
        slice = self.qs.order_by('id')[:2]
        self.assertEqual(2, slice.count())
        self.assertEqual('def', slice[1].id)

        slice = self.qs.order_by('id')[1:]
        self.assertEqual(3, slice.count())
        self.assertEqual('one', slice[1].id)
        self.assertEqual('xyz', slice[2].id)

    def test_filter(self):
        fqs = self.qs.filter(contains="two")
        self.assertEqual(1, fqs.count(), "count returns 1 when filtered - contains 'two'")
        self.assertEqual("two", fqs[0].name, "name matches filter")
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

    def test_filter_field(self):
        fqs = self.qs.filter(name="one")
        self.assertEqual(1, fqs.count(), "count returns 1 when filtered on name = 'one' (got %s)"
                         % self.qs.count())
        self.assertEqual("one", fqs[0].name, "name matches filter")
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

    def test_filter_xmlquery(self):
        fqs = self.qs.filter(name=XmlQuery(term="one"))
        self.assertEqual(1, fqs.count(),
            "count returns 1 when filtered on name = <query><term>one</term></query> (got %s)"
             % self.qs.count())
        self.assertEqual("one", fqs[0].name, "name matches filter")


    def test_filter_field_xpath(self):
        fqs = self.qs.filter(id="abc")
        self.assertEqual(1, fqs.count(), "count returns 1 when filtered on @id = 'abc' (got %s)"
                         % self.qs.count())
        self.assertEqual("two", fqs[0].name, "name returned is correct for id filter")
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

    def test_filter_field_contains(self):
        fqs = self.qs.filter(name__contains="o")
        self.assertEqual(3, fqs.count(),
                         "should get 3 matches for filter on name contains 'o' (got %s)" % fqs.count())
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

    def test_filter_field_contains_special(self):
        fqs = self.qs.filter(description__contains=' "quote" ')
        self.assertEqual(1, fqs.count(),
                         "should get 1 match for filter on desc contains ' \"quote\" ' (got %s)" % fqs.count())
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

        fqs = self.qs.filter(description__contains=' &!')
        self.assertEqual(1, fqs.count(),
                         "should get 1 match for filter on desc contains ' &!' (got %s)" % fqs.count())
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

    def test_filter_field_startswith(self):
        fqs = self.qs.filter(name__startswith="o")
        self.assertEqual(1, fqs.count(),
                         "should get 1 match for filter on name starts with 'o' (got %s)" % fqs.count())
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

    def test_filter_subobject_field(self):
        fqs = self.qs.filter(sub__subname="la")
        self.assertEqual(1, fqs.count(),
                         "should get 1 match for filter on sub_subname = 'la' (got %s)" % fqs.count())

    def test_filter_in(self):
        fqs = self.qs.filter(id__in=['abc', 'xyz', 'qrs'])
        self.assertEqual(
            2, fqs.count(),
            "should get 2 matches for filter on id in list (got %s)" % fqs.count())
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

        fqs = self.qs.filter(document_name__in=['f1.xml', 'f2.xml'])
        self.assertEqual(
            2, fqs.count(),
            "should get 2 matches for filter on document name in list (got %s)" % fqs.count())
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

        # filtering on a special field - should still be able to return/access it via only
        fqs = self.qs.filter(document_name__in=['f1.xml', 'f2.xml']) \
                     .only('id', 'document_name').order_by('document_name')
        self.assertEqual(
            2, fqs.count(),
            "should get 2 matches for filter on document name in list (got %s)" % fqs.count())
        self.assertEqual('f1.xml', fqs[0].document_name)

        fqs = self.qs.filter(document_name__in=['f1.xml',  'f2.xml']) \
                     .also('id', 'document_name').order_by('document_name')
        self.assertEqual(
            2, fqs.count(),
            "should get 2 matches for filter on document name in list (got %s)" % fqs.count())
        self.assertEqual('f1.xml', fqs[0].document_name)

    def test_filter_exists(self):
        fqs = self.qs.filter(id__exists=True)
        self.assertEqual(4, fqs.count(),
                         "filter on id exists=true returns all documents")
        fqs = self.qs.filter(id__exists=False)
        self.assertEqual(0, fqs.count(),
                         "filter on id exists=false returns no documents")
        fqs = self.qs.filter(wnn__exists=False)
        self.assertEqual(3, fqs.count(),
                         "filter on wacky node name exists=false returns 3 documents")

    def test_or_filter(self):
        fqs = self.qs.or_filter(id='abc', name='four').only('id')
        self.assertEqual(
            2, fqs.count(),
            "should get 2 matches for OR filter on id='abc' or name='four' (got %s)" % fqs.count())
        ids = [obj.id for obj in fqs.all()]
        self.assert_('abc' in ids, 'id "abc" in list of ids when OR filter includes id="abc"')
        self.assert_('def' in ids, 'id "def" in list of ids when OR filter includes name="four')

    def test_exclude(self):
        fqs = self.qs.exclude(id='abc', name='one').only('id')
        self.assertEqual(
            2, fqs.count(),
            "should get 2 matches for exclude filter on id='abc' or name='one' (got %s)" % fqs.count())
        ids = [obj.id for obj in fqs.all()]
        self.assert_('abc' not in ids, 'id "abc" should not be in list of ids when exclude id="abc"')

    def test_filter_gtelte(self):
        # < <= > >=

        # subclass to add a numeric field to test with
        class CountQueryTestModel(QueryTestModel):
            name_count = xmlmap.IntegerField('count(name)')

        qs = QuerySet(using=self.db, xpath='/root', collection=COLLECTION,
                      model=CountQueryTestModel)

        # each fixture has one and only one name
        self.assertEqual(0, qs.filter(name_count__gt=1).count())
        self.assertEqual(4, qs.filter(name_count__gte=1).count())
        self.assertEqual(4, qs.filter(name_count__lte=1).count())
        self.assertEqual(0, qs.filter(name_count__lt=1).count())

    def test_filter_document_path(self):
        # get full test path to first document
        item = self.qs.filter(name='one').only('document_name', 'collection_name').get()
        path = '%s/%s' % (item.collection_name, item.document_name)

        #
        fqs = self.qs.filter(document_path=path, name='one')
        self.assertEqual(1, fqs.count())
        fqs = self.qs.filter(document_path=path, name='two')
        self.assertEqual(0, fqs.count())

    def test_get(self):
        result = self.qs.get(contains="two")
        self.assert_(isinstance(result, QueryTestModel), "get() with contains returns single result")
        self.assertEqual(result.name, "two", "result returned by get() has correct data")
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

    def test_get_toomany(self):
        self.assertRaises(ReturnedMultiple, self.qs.get, contains="one")

    def test_get_nomatch(self):
        self.assertRaises(DoesNotExist, self.qs.get, contains="fifty-four")

    def test_get_byname(self):
        result = self.qs.get(name="one")
        self.assert_(isinstance(result, QueryTestModel), "get() with contains returns single result")
        self.assertEqual(result.name, "one", "result returned by get() has correct data")
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

    def test_filter_get(self):
        result = self.qs.filter(contains="one").filter(name="two").get()
        self.assert_(isinstance(result, QueryTestModel))
        self.assertEqual("two", result.name, "filtered get() returns correct data")
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

    def test_reset(self):
        self.qs.filter(contains="two")
        self.qs.reset()
        self.assertEqual(NUM_FIXTURES, self.qs.count(), "main queryset remains unchanged by filter")

    def test_order_by(self):
        # element
        fqs = self.qs.order_by('name')
        self.assertEqual('four', fqs[0].name)
        self.assertEqual('one', fqs[1].name)
        self.assertEqual('three', fqs[2].name)
        self.assertEqual('two', fqs[3].name)
        self.assert_('order by ' not in self.qs.query.getQuery(), "main queryset unchanged by order_by()")
        # attribute
        fqs = self.qs.order_by('id')
        self.assertEqual('abc', fqs[0].id)
        self.assertEqual('def', fqs[1].id)
        self.assertEqual('one', fqs[2].id)
        self.assertEqual('xyz', fqs[3].id)
        # reverse sorting
        fqs = self.qs.order_by('-name')
        self.assertEqual('four', fqs[3].name)
        self.assertEqual('two', fqs[0].name)
        fqs = self.qs.order_by('-id')
        self.assertEqual('abc', fqs[3].id)
        self.assertEqual('xyz', fqs[0].id)
        # case-insensitive sorting - upper-case description should not sort first
        fqs = self.qs.order_by('~description')
        self.assert_(fqs[0].description.startswith('third'))
        self.assert_(fqs[1].description.startswith('This one contains'))
        # reverse case-insensitive sorting - flags in either order
        fqs = self.qs.order_by('~-description')
        self.assert_(fqs[3].description.startswith('third'))
        fqs = self.qs.order_by('-~description')
        self.assert_(fqs[3].description.startswith('third'))

    def test_order_by_raw(self):
        fqs = self.qs.order_by_raw('min(%(xq_var)s/year)')
        self.assert_('1990' in fqs[0].years)
        self.assert_('2001' in fqs[1].years)
        self.assert_('2010' in fqs[2].years)
        self.assertEqual([], fqs[3].years)

        fqs = self.qs.order_by_raw('min(%(xq_var)s/year)', ascending=False)
        self.assertEqual([], fqs[0].years)
        self.assert_('2010' in fqs[1].years)
        self.assert_('2001' in fqs[2].years)
        self.assert_('1990' in fqs[3].years)

    def test_only(self):
        self.qs.only('name')
        self.assert_('element name {' not in self.qs.query.getQuery(), "main queryset unchanged by only()")

        fqs = self.qs.filter(id='one').only('name', 'id', 'sub', 'or_field')
        self.assert_(isinstance(fqs[0], QueryTestModel))  # actually a Partial type derived from this
        # attributes that should be present
        self.assertNotEqual(fqs[0].id, None)
        self.assertNotEqual(fqs[0].sub, None)
        self.assertNotEqual(fqs[0].sub.subname, None)
        self.assertNotEqual(fqs[0].or_field, None)
        # attribute not returned
        self.assertEqual(fqs[0].description, None)
        self.assertEqual('one', fqs[0].id)
        self.assertEqual('one', fqs[0].name)
        self.assertEqual('la', fqs[0].sub.subname)
        self.assertEqual('one', fqs[0].or_field)    # = name (first of ORed fields present)

        fqs = self.qs.filter(id='one').only('wnn')
        self.assertTrue(hasattr(fqs[0], "wnn"))
        self.assertEqual(42, fqs[0].wnn)

        # nested field return
        fqs = self.qs.filter(id='one').only('name', 'id', 'sub__subname')
        self.assertEqual('la', fqs[0].sub.subname)

        # xpath function return
        fqs = self.qs.filter(id='one').only('substring')
        self.assertEqual('o', fqs[0].substring)

        # sub-subclass
        fqs = self.qs.filter(id='one').only('sub__ssc')
        self.assert_(isinstance(fqs[0], QueryTestModel))

    def test_only_hash(self):
        fqs = self.qs.only('hash')
        # no filters, should return all 3 test objects
        for result in fqs:
            # each return object should have a 40-character SHA-1 hash checksum
            self.assertEqual(40, len(result.hash),
                             'xquery result should have 40-character checksum, got %s' % result.hash)

    def test_document_name(self):
        fqs = self.qs.filter(id='one').only('document_name')
        # document_name attribute should be present
        self.assertNotEqual(fqs[0].document_name, None)
        self.assertEqual(fqs[0].document_name, "f1.xml")

        fqs = self.qs.filter(id='one').also('document_name')
        self.assertNotEqual(fqs[0].document_name, None)
        self.assertEqual(fqs[0].document_name, "f1.xml")

    def test_collection_name(self):
        fqs = self.qs.filter(id='one').only('collection_name')
        self.assertEqual(fqs[0].collection_name, '/db' + COLLECTION)

        fqs = self.qs.filter(id='one').also('collection_name')
        self.assertEqual(fqs[0].collection_name, '/db' + COLLECTION)

    def test_only_lastmodified(self):
        fqs = self.qs.only('last_modified')
        # no filters, should return all 3 test objects
        for result in fqs:
            self.assert_(isinstance(result.last_modified, datetime))

    def test_iter(self):
        for q in self.qs:
            self.assert_(isinstance(q, QueryTestModel))

    def test_slice_iter(self):
        i = 0
        for q in self.qs[1:2]:
            i += 1
        self.assertEqual(1, i)

    def test_also(self):
        class SubqueryTestModel(xmlmap.XmlObject):
            name = xmlmap.StringField('.')
            parent_id = xmlmap.StringField('parent::root/@id')

        qs = QuerySet(using=self.db, collection=COLLECTION, model=SubqueryTestModel, xpath='//name')
        name = qs.also('parent_id').get(name__exact='two')
        self.assertEqual('abc', name.parent_id,
                         "parent id set correctly when returning at name level with also parent_id specified; should be 'abc', got '"
                         + name.parent_id + "'")

    def test_also_subfield(self):
        class SubqueryTestModel(xmlmap.XmlObject):
            subname = xmlmap.StringField('subname')
            parent = xmlmap.NodeField('parent::root', QueryTestModel)

        qs = QuerySet(using=self.db, collection=COLLECTION, model=SubqueryTestModel, xpath='//sub')
        name = qs.also('parent__id', 'parent__wnn').get(subname__exact='la')
        self.assertEqual('la', name.subname)
        self.assertEqual('one', name.parent.id)
        self.assertEqual(42, name.parent.wnn)

    def test_also_raw(self):
        class SubqueryTestModel(QueryTestModel):
            myid = xmlmap.StringField('@id')

        qs = QuerySet(using=self.db, collection=COLLECTION, model=SubqueryTestModel, xpath='/root')
        qs = qs.filter(id='abc').also_raw(myid='string(%(xq_var)s//name/ancestor::root/@id)')
        self.assertEqual('abc', qs[0].myid)
        # filtered version of the queryset with raw
        obj = qs.filter(name='two').get()
        self.assertEqual('abc', obj.myid)

        # multiple parameters
        obj = qs.filter(id='abc').also_raw(id='string(%(xq_var)s/@id)',
            name='normalize-space(%(xq_var)s//name)').get(id='abc')
        self.assertEqual('abc', obj.id)
        self.assertEqual('two', obj.name)

    def test_only_raw(self):
        qs = self.qs.only_raw(id='xs:string(%(xq_var)s//name/ancestor::root/@id)').filter(name='two')
        self.assertEqual('abc', qs[0].id)
        # filtered version
        obj = qs.get()
        self.assertEqual('abc', obj.id)

        # when combined with regular only, other fields come back correctly
        qs = self.qs.only('name', 'description', 'substring')
        obj = qs.only_raw(id='xs:string(%(xq_var)s//name/ancestor::root/@id)').get(id='abc')
        self.assertEqual('two', obj.name)
        self.assertEqual('t', obj.substring)
        self.assertEqual('this one only has two', obj.description)
        self.assertEqual('abc', obj.id)

        # subfield
        obj = qs.only_raw(sub__subname='normalize-space(%(xq_var)s//subname)').get(id='one')
        self.assertEqual('la', obj.sub.subname)

        # multiple parameters
        obj = self.qs.filter(id='abc').only_raw(id='string(%(xq_var)s/@id)',
            name='normalize-space(%(xq_var)s//name)').get(id='abc')
        self.assertEqual('abc', obj.id)
        self.assertEqual('two', obj.name)

        # list field - multiple return values
        class MyQueryTest(QueryTestModel):
            name = xmlmap.StringListField('name')
        qs = QuerySet(using=self.db, xpath='/root', collection=COLLECTION, model=MyQueryTest)
        # return one object but find all the names in the test collection
        obj = qs.filter(id='abc').only_raw(name='collection("/db%s")//name' % COLLECTION).get(id='abc')
        # 4 names in test fixtures - should come back as a list of those 4 names
        self.assertEqual(4, len(obj.name))

    def test_getDocument(self):
        obj = self.qs.getDocument("f1.xml")
        self.assert_(isinstance(obj, QueryTestModel),
                     "object returned by getDocument is instance of QueryTestModel")
        self.assertEqual("one", obj.name)

    def test_distinct(self):
        qs = QuerySet(using=self.db, collection=COLLECTION, xpath='//name')
        vals = qs.distinct()
        self.assert_('one' in vals)
        self.assert_('two' in vals)
        self.assert_('three' in vals)
        self.assert_('four' in vals)
        self.assert_('abc' not in vals)

    def test_namespaces(self):
        # filter on a field with a namespace
        fqs = self.qs.filter(nsfield='namespaced').all()
        self.assertEqual('namespaced', fqs[0].nsfield)


class ExistQueryTest__FullText(unittest.TestCase):
    # when full-text indexing is enabled, eXist must index files when they are loaded to the db
    # this makes tests *significantly* slower
    # any tests that require full-text queries should be here

    # sample lucene configuration for testing full-text queries
    FIXTURE_INDEX = '''
    <collection xmlns="http://exist-db.org/collection-config/1.0">
        <index>
            <lucene>
                <analyzer class="org.apache.lucene.analysis.standard.StandardAnalyzer"/>
                <text qname="description"/>
                <text qname="root"/>
            </lucene>
        </index>
    </collection>
    '''

    def setUp(self):
        self.db = ExistDB(server_url=EXISTDB_SERVER_URL,
            username=EXISTDB_SERVER_USER, password=EXISTDB_SERVER_PASSWORD)
        # create index for collection - should be applied to newly loaded files
        self.db.loadCollectionIndex(COLLECTION, self.FIXTURE_INDEX)

        load_fixtures(self.db)

        self.qs = QuerySet(using=self.db, xpath='/root',
                           collection=COLLECTION, model=QueryTestModel)

    def tearDown(self):
        self.db.removeCollection(COLLECTION)
        self.db.removeCollectionIndex(COLLECTION)

    def test_filter_fulltext_terms(self):
        fqs = self.qs.filter(description__fulltext_terms='only two')
        self.assertEqual(1, fqs.count(),
                         "should get 1 match for fulltext_terms search on = 'only two' (got %s)" % fqs.count())

    def test_filter_fulltext_options(self):
        qs = QuerySet(using=self.db, xpath='/root',
                      collection=COLLECTION, model=QueryTestModel,
                      fulltext_options={'default-operator': 'and'})
        # search for terms present in fixtures - but not both present in one doc
        fqs = qs.filter(description__fulltext_terms='only third')
        # for now, just confirm that the option is passed through to query
        self.assert_('<default-operator>and</default-operator>' in fqs.query.getQuery())
        # TODO: test this properly!
        # query options not supported in current version of eXist
        # self.assertEqual(0, fqs.count())

    def test_order_by__fulltext_score(self):
        fqs = self.qs.filter(description__fulltext_terms='one').order_by('-fulltext_score')
        self.assertEqual('one', fqs[0].name)    # one appears 3 times, should be first

    def test_only__fulltext_score(self):
        fqs = self.qs.filter(description__fulltext_terms='one').only('fulltext_score', 'name')
        self.assert_(isinstance(fqs[0], QueryTestModel))  # actually a Partial type derived from this
        # fulltext score attribute should be present
        self.assertNotEqual(fqs[0].fulltext_score, None)
        self.assert_(float(fqs[0].fulltext_score) > 0.5)    # full-text score should be a float

    def test_fulltext_highlight(self):
        fqs = self.qs.filter(description__fulltext_terms='only two')
        # result from fulltext search - by default, xml should have exist:match tags
        self.assert_('<exist:match' in fqs[0].serialize())

        fqs = self.qs.filter(description__fulltext_terms='only two', highlight=False)
        # with highlighting disabled, should not have exist:match tags
        self.assert_('<exist:match' not in fqs[0].serialize())

        # order of args in the same filter should not matter
        fqs = self.qs.filter(highlight=False, description__fulltext_terms='only two')
        # with highlighting disabled, should not have exist:match tags
        self.assert_('<exist:match' not in fqs[0].serialize())

        # separate filters should also work
        fqs = self.qs.filter(description__fulltext_terms='only two').filter(highlight=False)
        # with highlighting disabled, should not have exist:match tags
        self.assert_('<exist:match' not in fqs[0].serialize())

    def test_highlight(self):
        fqs = self.qs.filter(highlight='supercalifragilistic')
        self.assertEqual(4, fqs.count(),
                         "highlight filter returns all documents even though search term is not present")

        fqs = self.qs.filter(highlight='one').order_by('id')
        self.assert_('<exist:match' in fqs[0].serialize())

    def test_match_count(self):
        fqs = self.qs.filter(id='one', highlight='one').only('match_count')
        self.assertEqual(fqs[0].match_count, 4, "4 matched words should be found")

    def test_using(self):
        fqs = self.qs.using('new-collection')
        # using should update the collection on the xquery object
        self.assertEqual('new-collection', fqs.query.collection)


class XqueryTest(unittest.TestCase):

    def test_defaults(self):
        xq = Xquery()
        self.assertEquals('/node()', xq.getQuery())

    def test_xpath(self):
        xq = Xquery(xpath='/path/to/el')
        self.assertEquals('/path/to/el', xq.getQuery())

    def test_coll(self):
        xq = Xquery(collection='myExistColl')
        self.assertEquals('collection("/db/myExistColl")/node()', xq.getQuery())

        xq = Xquery(xpath='/root/el', collection='/coll/sub')
        self.assertEquals('collection("/db/coll/sub")/root/el', xq.getQuery())

    def test_set_collection(self):
        # initialize with no collection
        xq = Xquery(xpath='/el')
        xq.set_collection('coll')
        self.assertEquals('collection("/db/coll")/el', xq.getQuery())

        # initialize with one collection, then switch
        xq = Xquery(collection='coll1')
        xq.set_collection('coll2')
        self.assertEquals('collection("/db/coll2")/node()', xq.getQuery())

        # leading slash is ok too
        xq.set_collection('/coll3')
        self.assertEquals('collection("/db/coll3")/node()', xq.getQuery())

        # set to None
        xq.set_collection(None)
        self.assertEquals('/node()', xq.getQuery())

    def test_document(self):
        xq = Xquery(xpath='/el', document="/db/coll/file.xml")
        self.assertEquals('doc("/db/coll/file.xml")/el', xq.getQuery())
        # document takes precedence over collection
        xq.set_collection('coll')  # should be ignored
        self.assertEquals('doc("/db/coll/file.xml")/el', xq.getQuery())

    def test_sort(self):
        xq = Xquery(collection="mycoll")
        xq.xq_var = '$n'
        xq.sort('@id')
        self.assert_('order by $n/@id ascending' in xq.getQuery())
        self.assert_('collection("/db/mycoll")' in xq.getQuery())

        # prep_xpath function should clean up more complicated xpaths
        xq.sort('name|@id')
        self.assert_('order by $n/name|$n/@id' in xq.getQuery())

        # sort descending
        xq.sort('@id', ascending=False)
        self.assert_('order by $n/@id descending' in xq.getQuery())

        # sort case-insensitive
        xq.sort('@id', case_insensitive=True)
        self.assert_('order by fn:lower-case($n/@id) ascending' in xq.getQuery())

        # case-insensitive and descending
        xq.sort('@id', case_insensitive=True, ascending=False)
        self.assert_('order by fn:lower-case($n/@id) descending' in xq.getQuery())

    def test_filters(self):
        xq = Xquery(xpath='/el')
        xq.add_filter('.', 'contains', 'dog')
        self.assertEquals('/el[contains(., "dog")]', xq.getQuery())
        # filters are additive
        xq.add_filter('.', 'startswith', 'S')
        self.assertEquals('/el[contains(., "dog")][starts-with(., "S")]', xq.getQuery())

    def test_filters_fulltext(self):
        xq = Xquery(xpath='/el')
        xq.add_filter('.', 'fulltext_terms', 'dog')
        self.assertEquals('/el[ft:query(., "dog")]', xq.getQuery())

    def test_fulltext_options(self):
        # pass in options for a full-text query
        xq = Xquery(xpath='/el', fulltext_options={'default-operator': 'and'})
        xq.add_filter('.', 'fulltext_terms', 'dog')
        self.assert_('<default-operator>and</default-operator>' in xq.getQuery())
        self.assert_('/el[ft:query(., "dog", $ft_options)]', xq.getQuery())

    def test_filters_highlight(self):
        xq = Xquery(xpath='/el')
        xq.add_filter('.', 'highlight', 'dog star')
        self.assertEquals('util:expand((/el[ft:query(., "dog star")]|/el))',
            xq.getQuery())

    def test_filter_escaping(self):
        xq = Xquery(xpath='/el')
        xq.add_filter('.', 'contains', '"&')
        self.assertEquals('/el[contains(., """&amp;")]', xq.getQuery())

    def test_filter_in(self):
        xq = Xquery(xpath='/el')
        xq.add_filter('@id', 'in', ['a', 'b', 'c'])
        self.assertEquals('/el[@id="a" or @id="b" or @id="c"]', xq.getQuery())

        # filter on a 'special' field - requires let & where statements
        xq = Xquery(xpath='/el')
        xq.add_filter('document_name', 'in', ['a.xml', 'b.xml'])
        self.assert_('let $document_name' in xq.getQuery())
        self.assert_('where $document_name="a.xml" or $document_name="b.xml"'
                     in xq.getQuery())

    def test_filter_exists(self):
        xq = Xquery(xpath='/el')
        xq.add_filter('@id', 'exists', True)
        self.assertEquals('/el[@id]', xq.getQuery())

        xq = Xquery(xpath='/el')
        xq.add_filter('@id', 'exists', False)
        self.assertEquals('/el[not(@id)]', xq.getQuery())

    def test_filter_gtlt(self):
        xq = Xquery(xpath='/el')
        xq.add_filter('@id', 'gt', 5)
        self.assert_('el[@id > 5]' in xq.getQuery())

        xq = Xquery(xpath='/el')
        xq.add_filter('@id', 'gte', 5)
        self.assert_('/el[@id >= 5]' in xq.getQuery())

        xq.add_filter('@id', 'lt', '10')
        self.assert_('el[@id >= 5]' in xq.getQuery())
        self.assert_('[@id < "10"]' in xq.getQuery())

        xq.add_filter('@id', 'lte', 3)
        self.assert_('[@id <= 3]' in xq.getQuery())

    def test_or_filters(self):
        xq = Xquery(xpath='/el')
        xq.add_filter('.', 'contains', 'dog', mode='OR')
        xq.add_filter('.', 'startswith', 'S', mode='OR')
        self.assertEquals('/el[contains(., "dog") or starts-with(., "S")]',
                          xq.getQuery())

    def test_not_filters(self):
        xq = Xquery(xpath='/el')
        xq.add_filter('.', 'contains', 'dog', mode='NOT')
        self.assertEquals('/el[not(contains(., "dog"))]', xq.getQuery())

        xq = Xquery(xpath='/el')
        xq.add_filter('.', 'contains', 'dog', mode='NOT')
        xq.add_filter('.', 'startswith', 'S', mode='NOT')
        self.assertEquals('/el[not(contains(., "dog")) and not(starts-with(., "S"))]',
                          xq.getQuery())

    def test_return_only(self):
        xq = Xquery(xpath='/el')
        xq.xq_var = '$n'
        xq.return_only({'myid': '@id', 'some_name': 'name',
            'first_letter': 'substring(@n,1,1)'})
        xq_return = xq._constructReturn()
        self.assert_('return <el>' in xq_return)
        self.assert_('<field>{$n/@id}</field>' in xq_return)
        self.assert_('<field>{$n/name}</field>' in xq_return)
        self.assert_('<field>{substring($n/@n,1,1)}</field>' in xq_return)
        self.assert_('</el>' in xq_return)

        xq = Xquery(xpath='/some/el/notroot')
        xq.return_only({'id': '@id'})
        self.assert_('return <notroot>' in xq._constructReturn())

        # case where node test can't be the return element
        xq = Xquery(xpath='/foo/bar/node()')
        xq.return_only({'myid': '@id'})
        xq_return = xq._constructReturn()
        self.assert_('return <node>' in xq_return)

        xq = Xquery(xpath='/foo/bar/*')
        xq.return_only({'myid': '@id'})
        xq_return = xq._constructReturn()
        self.assert_('return <node>' in xq_return)

    def test_return_only__fulltext_score(self):
        xq = Xquery(xpath='/el')
        xq.xq_var = '$n'
        xq.return_only({'fulltext_score': ''})
        self.assert_('let $fulltext_score := ft:score($n)' in xq.getQuery())
        self.assert_('<fulltext_score>{$fulltext_score}</fulltext_score>' in xq._constructReturn())

    def test_return_also(self):
        xq = Xquery(xpath='/el')
        xq.xq_var = '$n'
        xq.return_also({'myid': '@id', 'some_name': 'name'})
        self.assert_('{$n}' in xq._constructReturn())
        self.assert_('<field>{$n/@id}</field>' in xq._constructReturn())

    def test_return_also__fulltext_score(self):
        xq = Xquery(xpath='/el')
        xq.xq_var = '$n'
        xq.return_also({'fulltext_score': ''})
        self.assert_('let $fulltext_score := ft:score($n)' in xq.getQuery())
        self.assert_('<fulltext_score>{$fulltext_score}</fulltext_score>' in xq._constructReturn())

    def test_return_also__highlight(self):
        xq = Xquery(xpath='/el')
        xq.xq_var = '$n'
        xq.return_also({'fulltext_score': ''})
        xq.add_filter('.', 'highlight', 'dog star')
        self.assert_('(/el[ft:query(., "dog star")]|/el)' in xq.getQuery())

    def test_return_also_raw(self):
        xq = Xquery(xpath='/el')
        xq.xq_var = '$n'
        xq._raw_prefix = 'r_'
        xq.return_also({'myid': 'count(util:expand(%(xq_var)s/@id))'}, raw=True)
        self.assert_('<r_myid>{count(util:expand($n/@id))}</r_myid>' in xq._constructReturn())

        xq = Xquery(xpath='/el')
        xq.xq_var = '$n'
        xq._raw_prefix = 'r_'
        xq.return_also({'myid': '@id'}, raw=True)
        self.assert_('<r_myid>{@id}</r_myid>' in xq._constructReturn())

    def test_set_limits(self):
        # subsequence with xpath
        xq = Xquery(xpath='/el')
        xq.xq_var = '$n'
        xq.set_limits(low=0, high=4)
        self.assertEqual('subsequence(/el, 1, 4)', xq.getQuery())
        # subsequence with FLWR query
        xq.return_only({'name': 'name'})
        self.assert_('subsequence(for $n in' in xq.getQuery())

        # additive limits
        xq = Xquery(xpath='/el')
        xq.set_limits(low=2, high=10)
        xq.set_limits(low=1, high=5)
        self.assertEqual('subsequence(/el, 4, 4)', xq.getQuery())

        # no high specified
        xq = Xquery(xpath='/el')
        xq.set_limits(low=10)
        self.assertEqual('subsequence(/el, 11, )', xq.getQuery())

        # no low
        xq = Xquery(xpath='/el')
        xq.set_limits(high=15)
        self.assertEqual('subsequence(/el, 1, 15)', xq.getQuery())

    def test_clear_limits(self):
        xq = Xquery(xpath='/el')
        xq.set_limits(low=2, high=5)
        xq.clear_limits()
        self.assertEqual('/el', xq.getQuery())

    def test_distinct(self):
        # distinct-values
        xq = Xquery(xpath='/el')
        xq.distinct()
        self.assertEqual('distinct-values(/el)', xq.getQuery())

    def test_prep_xpath(self):
        xq = Xquery()
        xq.xq_var = '$n'
        # handle attributes
        self.assertEqual('<field>{$n/@id}</field>', xq.prep_xpath('@id', return_field=True))
        self.assertEqual('<field>{$n/../@id}</field>', xq.prep_xpath('../@id', return_field=True))
        self.assertEqual('<field>{$n/parent::root/@id}</field>', xq.prep_xpath('parent::root/@id', return_field=True))
        # handle regular nodes
        self.assertEqual('<field>{$n/title}</field>', xq.prep_xpath('title', return_field=True))
        # function call - regular node
        self.assertEqual('substring($n/title,1,1)', xq.prep_xpath('substring(title,1,1)'))
        # function call - abbreviated step
        self.assertEqual('substring($n/.,1,1)', xq.prep_xpath('substring(.,1,1)'))

        # xpath with OR - absolute paths
        self.assertEqual('<field>{$n/name|$n/title}</field>', xq.prep_xpath('/name|/title', return_field=True))
        # xpath with OR - relative paths
        self.assertEqual('<field>{$n/name|$n/title}</field>', xq.prep_xpath('name|title', return_field=True))
        # xpath with OR - mixed absolute and relative paths
        self.assertEqual('<field>{$n/name|$n/title}</field>', xq.prep_xpath('/name|title', return_field=True))
        # multiple ORs
        self.assertEqual('<field>{$n/name|$n/title|$n/@year}</field>',
                         xq.prep_xpath('/name|/title|@year', return_field=True))

        # .//node inside a function call
        self.assertEqual('<field>{normalize-space($n/.//name)}</field>',
                xq.prep_xpath('normalize-space($n/.//name)', return_field=True))

        # node|node inside a function call
        self.assertEqual('fn:lower-case($n/name|$n/title)',
                xq.prep_xpath('fn:lower-case(name|title)'))

        # node|node inside a nested function call
        self.assertEqual('fn:lower-case(normalize-space($n/name|$n/title))',
                xq.prep_xpath('fn:lower-case(normalize-space(name|title))'))


    def test_namespaces(self):
        xq = Xquery(xpath='/foo:el', namespaces={'foo': 'urn:foo#'})
        ns_declaration = '''declare namespace foo='urn:foo#';'''
        # xpath-only xquery should have namespace declaration
        self.assert_(ns_declaration in xq.getQuery())
        # full FLOWR xquery should also have declaration
        xq.return_only({'id': '@id'})
        self.assert_(ns_declaration in xq.getQuery())
