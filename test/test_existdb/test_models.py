# file test_existdb/test_models.py
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

import os
import unittest
try:
    from unittest import skipIf
except ImportError:
    from unittest2 import skipIf

try:
    import django
    from django.conf import settings
except ImportError:
    django = None
    import localsettings as settings

from eulxml import xmlmap
from eulexistdb.db import ExistDB

try:
    # manager and model currently require django
    from eulexistdb.models import XmlModel
    from eulexistdb.manager import Manager
except ImportError:
    # create dummy classes so code models declared below are valid
    class XmlModel:
        pass

    class Manager:
        def __init__(self, *args, **kwargs):
            pass

from localsettings import EXISTDB_SERVER_URL, EXISTDB_SERVER_USER, \
    EXISTDB_SERVER_PASSWORD, EXISTDB_TEST_COLLECTION

# test model/manager logic


class PartingBase(xmlmap.XmlObject):
    '''A plain XmlObject comparable to how one might be defined in
    production code.'''
    exclamation = xmlmap.StringField('exclamation')
    target = xmlmap.StringField('target')


class Parting(XmlModel, PartingBase):
    '''An XmlModel can derive from an XmlObject to incorporate its
    fields.'''
    objects = Manager('/parting')


class Exclamation(XmlModel):
    text = xmlmap.StringField('text()')
    next = xmlmap.StringField('following-sibling::*[1]')

    objects = Manager('/parting/exclamation')


@skipIf(django is None, 'Requires Django')
class ModelTest(unittest.TestCase):
    COLLECTION = EXISTDB_TEST_COLLECTION

    def setUp(self):
        self.db = ExistDB(server_url=EXISTDB_SERVER_URL,
            username=EXISTDB_SERVER_USER, password=EXISTDB_SERVER_PASSWORD)
        self.db.createCollection(self.COLLECTION, True)

        test_dir = os.path.dirname(os.path.abspath(__file__))
        fixture = os.path.join(test_dir, 'exist_fixtures', 'goodbye-english.xml')
        loaded = self.db.load(open(fixture), self.COLLECTION + '/goodbye-english.xml')
        fixture = os.path.join(test_dir, 'exist_fixtures', 'goodbye-french.xml')
        loaded = self.db.load(open(fixture), self.COLLECTION + '/goodbye-french.xml')

        # temporarily set test collection as root exist collection
        self._root_collection = settings.EXISTDB_ROOT_COLLECTION
        settings.EXISTDB_ROOT_COLLECTION = self.COLLECTION

    def tearDown(self):
        self.db.removeCollection(self.COLLECTION)

        settings.EXISTDB_ROOT_COLLECTION = self._root_collection

    def test_manager(self):
        partings = Parting.objects.all()
        self.assertEquals(2, partings.count())

    def test_sibling_query(self):
        # test sibling node access via 'also'
        exc = Exclamation.objects.filter(text='Au revoir').also('next').get()
        self.assertEqual('monde', exc.next)

