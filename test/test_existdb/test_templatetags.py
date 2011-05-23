#!/usr/bin/env python

# file test_existdb/test_templatetags.py
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

from lxml import etree
import unittest

from eulexistdb.db import EXISTDB_NAMESPACE
from eulexistdb.templatetags.existdb import exist_matches
from eulxml.xmlmap import XmlObject

from testcore import main

class ExistMatchTestCase(unittest.TestCase):
# test exist_match template tag explicitly
    SINGLE_MATCH = """<abstract>Pitts v. <exist:match xmlns:exist="%s">Freeman</exist:match>
school desegregation case files</abstract>""" % EXISTDB_NAMESPACE
    MULTI_MATCH = """<title>Pitts v. <exist:match xmlns:exist="%(ex)s">Freeman</exist:match>
<exist:match xmlns:exist="%(ex)s">school</exist:match> <exist:match xmlns:exist="%(ex)s">desegregation</exist:match>
case files</title>""" % {'ex': EXISTDB_NAMESPACE}

    def setUp(self):
        self.content = XmlObject(etree.fromstring(self.SINGLE_MATCH))   # placeholder

    def test_single_match(self):
        self.content.node = etree.fromstring(self.SINGLE_MATCH)
        format = exist_matches(self.content)
        self.assert_('Pitts v. <span class="exist-match">Freeman</span>'
            in format, 'exist:match tag converted to span for highlighting')

    def test_multiple_matches(self):
        self.content.node = etree.fromstring(self.MULTI_MATCH)
        format = exist_matches(self.content)
        self.assert_('Pitts v. <span class="exist-match">Freeman</span>'
            in format, 'first exist:match tag converted')
        self.assert_('<span class="exist-match">school</span> <span class="exist-match">desegregation</span>'
            in format, 'second and third exist:match tags converted')



if __name__ == '__main__':
    main()
