#!/usr/bin/env python

# file test_existdb/test_exceptions.py
# 
#   Copyright 2012 Emory University Libraries
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

import socket
import unittest
import xmlrpclib

from eulexistdb.exceptions import ExistDBException
from testcore import main

class ExistDbExceptionTest(unittest.TestCase):

    def test_message(self):
        # generic exception 

        msg_text = 'this is a basic exception message'
        err = ExistDBException(Exception(msg_text))
        self.assertEqual(msg_text, err.message())

        # socket timeout
        err = ExistDBException(socket.timeout())
        self.assertEqual('Request Timed Out', err.message())

        # xmlrpc error
        # - args are url, error code, error message, headers
        rpc_err = xmlrpclib.ProtocolError('http://so.me/url', 101,
                                          'rpc error message', {})
        err = ExistDBException(rpc_err)
        # message should contain various bits of info from exception
        msg = err.message()
        self.assert_('XMLRPC Error' in msg)
        self.assert_(rpc_err.url in msg)
        self.assert_(str(rpc_err.errcode) in msg)
        self.assert_(rpc_err.errmsg in msg)

        # no test for exist-speficic errors (need an exaample error)



if __name__ == '__main__':
    main()
