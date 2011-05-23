# file localsettings.py
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

EXISTDB_SERVER_PROTOCOL = "http://"
EXISTDB_SERVER_HOST     = "localhost:8080/exist"
# NOTE: test account used for tests that require non-guest access; user should be in eXist DBA group
EXISTDB_DBA_USER     = "username"
EXISTDB_DBA_PASSWORD = "pwd"
# main access - no user/password, guest account
EXISTDB_SERVER_URL = EXISTDB_SERVER_PROTOCOL + EXISTDB_SERVER_HOST
# access with the specified user account
EXISTDB_SERVER_URL_DBA      = EXISTDB_SERVER_PROTOCOL + EXISTDB_DBA_USER + ":" + \
    EXISTDB_DBA_PASSWORD + "@" + EXISTDB_SERVER_HOST
EXISTDB_ROOT_COLLECTION = '/eulcore'
# NOTE: currently, for full-text query tests to work, test collection should be named /test/something
#       a system collection named /db/system/config/db/test should exist and be writable by guest
EXISTDB_TEST_COLLECTION = '/test' + EXISTDB_ROOT_COLLECTION
