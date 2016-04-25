# file test_existdb/__init__.py
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

# django settings must be configured before importing anything that
# relies on settings or uses override_settings
os.environ["DJANGO_SETTINGS_MODULE"] = "localsettings"

from test_existdb.test_db import *
from test_existdb.test_query import *
from test_existdb.test_models import *
from test_existdb.test_templatetags import *
from test_existdb.test_exceptions import *

from eulexistdb import db

from localsettings import EXISTDB_SERVER_URL, EXISTDB_SERVER_ADMIN_USER, \
    EXISTDB_SERVER_ADMIN_PASSWORD, EXISTDB_SERVER_USER, \
    EXISTDB_SERVER_PASSWORD, EXISTDB_TEST_COLLECTION, \
    EXISTDB_TEST_BASECOLLECTION, EXISTDB_TEST_GROUP


def setup_module():
    # create test account and collections, with appropriate permissions
    admindb = db.ExistDB(server_url=EXISTDB_SERVER_URL,
        username=EXISTDB_SERVER_ADMIN_USER,
        password=EXISTDB_SERVER_ADMIN_PASSWORD)

    # create non-admin test account
    admindb.create_group(EXISTDB_TEST_GROUP)
    admindb.create_account(EXISTDB_SERVER_USER, EXISTDB_SERVER_PASSWORD,
        EXISTDB_TEST_GROUP)

    admindb.createCollection('/db' + EXISTDB_TEST_BASECOLLECTION, True)
    # test index config
    test_cfg_collection = '/db/system/config/db/' + EXISTDB_TEST_BASECOLLECTION
    admindb.createCollection(test_cfg_collection, True)

    # make both collections owned by test group and group writable
    admindb.query('sm:chgrp(xs:anyURI("/db%s"), "%s")' % \
        (EXISTDB_TEST_BASECOLLECTION, EXISTDB_TEST_GROUP))
    admindb.query('sm:chgrp(xs:anyURI("%s"), "%s")' % \
        (test_cfg_collection, EXISTDB_TEST_GROUP))

    admindb.query('sm:chmod(xs:anyURI("/db%s"), "rwxrwxrwx")' % \
        (EXISTDB_TEST_BASECOLLECTION))
    admindb.query('sm:chmod(xs:anyURI("%s"), "rwxrwxrwx")' % \
        (test_cfg_collection))


def teardown_module():
    # remove test account & collections

    admindb = db.ExistDB(server_url=EXISTDB_SERVER_URL,
        username=EXISTDB_SERVER_ADMIN_USER,
        password=EXISTDB_SERVER_ADMIN_PASSWORD)

    test_cfg_collection = '/db/system/config/db/' + EXISTDB_TEST_BASECOLLECTION
    admindb.removeCollection(test_cfg_collection)
    admindb.removeCollection(EXISTDB_TEST_BASECOLLECTION)
    admindb.query('sm:remove-group("%s")' % EXISTDB_TEST_GROUP);
    admindb.query('sm:remove-group("%s")' % EXISTDB_SERVER_USER);
    admindb.query('sm:remove-account("%s")' % EXISTDB_SERVER_USER);
