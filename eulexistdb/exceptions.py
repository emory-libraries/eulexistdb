# file existdb/exceptions.py
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

import socket
import xmlrpclib
from urllib import unquote_plus

class ExistDBException(Exception):
    """A handy wrapper for all errors returned by the eXist server."""

    rpc_prefix = 'RpcConnection: '

    def message(self):        
        "Rough conversion of xmlrpc fault string into something human-readable."
        orig_except = self.args[0]
        if isinstance(orig_except, socket.timeout):
            # socket timeout error text is always "timed out"
            message = 'Request Timed Out'
        elif isinstance(orig_except, socket.error):
            # socket error is a tuple of errno, error string
            message = 'I/O Error: %s' % orig_except[1]
        elif isinstance(orig_except, xmlrpclib.ProtocolError):
            message = 'XMLRPC Error at %(url)s: %(code)s %(msg)s' % {
                    'url': orig_except.url,
                    'code': orig_except.errcode,
                    'msg': unquote_plus(orig_except.errmsg)
            }
        # xmlrpclib.ResponseError ?
        elif self.rpc_prefix in str(self):
            # RpcConnection error generally reports eXist-specific errors
            preamble, message = str(self).strip("""'<>\"""").split(self.rpc_prefix)
            # xmldb and xpath calls may have additional error strings:
            message = message.replace('org.exist.xquery.XPathException: ', '')
            message = message.replace('XMLDB exception caught: ', '')
            message = message.replace('[at line 1, column 1]', '')
        else:
            # if all else fails, display the exception as a string
            message = str(orig_except)
        return message


class DoesNotExist(ExistDBException):
    "The query returned no results when exactly one was expected."
    silent_variable_failure = True

class ReturnedMultiple(ExistDBException):
    "The query returned multiple results when only one was expected."
    pass

class ExistDBTimeout(ExistDBException):
    "The query to eXist exceeded the configured timeout."
    pass


# other possible sub- exception types:
# document not found (getDoc,remove)
# collection not found 

