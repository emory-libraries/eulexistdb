# file eulexistdb/db.py
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

"""Connect to an eXist XML database and query it.

This module provides :class:`ExistDB` and related classes for connecting to
an eXist-db_ database and executing XQuery_ queries against it.

.. _XQuery: http://www.w3.org/TR/xquery/
.. _eXist-db: http://exist.sourceforge.net/

When used with Django, :class:`~eulexistdb.db.ExistDB` can pull
configuration settings directly from Django settings.  If you create
an instance of :class:`~eulexistdb.db.ExistDB` without specifying a
server url, it will attempt to configure an eXist database based on
Django settings, using the configuration names documented below.



Projects that use this module should include the following settings in their
``settings.py``::

  # Exist DB Settings
  EXISTDB_SERVER_USER = 'user'
  EXISTDB_SERVER_PASSWORD = 'password'
  EXISTDB_SERVER_URL = "http://megaserver.example.com:8042/exist"
  EXISTDB_ROOT_COLLECTION = "/sample_collection"

.. note:

  User and password settings are optional.

To configure a timeout for most eXist connections, specify the desired
time in seconds as ``EXISTDB_TIMEOUT``; if none is specified, the
global default socket timeout will be used.

.. note::

  Any configured ``EXISTDB_TIMEOUT`` will be ignored by the
  **existdb** management command, since reindexing a large collection
  could take significantly longer than a normal timeout would allow
  for.

If you are using an eXist index configuration file, you can add another setting
to specify your configuration file::

  EXISTDB_INDEX_CONFIGFILE = "/path/to/my/exist_index.xconf"

This will allow you to use the ``existdb`` management command to
manage your index configuration file in eXist.

If you wish to specify options for fulltext queries, you can set a dictionary
of options like this::

    EXISTDB_FULLTEXT_OPTIONS = {'default-operator': 'and'}

.. Note::

    Python :mod:`xmlrpclib` does not support extended types, some of which
    are used in eXist returns.  This does not currently affect the
    functionality exposed within :class:`ExistDB`, but may cause issues
    if you use the :attr:`ExistDB.server` XML-RPC connection directly
    for other available eXist XML-RPC methods.   If you do make use of
    those, you may want to enable XML-RPC patching to handle the return
    types::

        from eulexistdb import patch
        patch.request_patching(patch.XMLRpcLibPatch)

---

If you are writing unit tests against code that uses
:mod:`eulexistdb`, you may want to take advantage of
:class:`eulexistdb.testutil.TestCase` for loading fixture data to a
test eXist-db collection, and
:class:`eulexistdb.testutil.ExistDBTestSuiteRunner`, which has logic
to set up and switch configurations between a development and test
collections in eXist.

----

"""

from functools import wraps
import logging
import requests
import socket
import time
from urllib import splittype
import urlparse
import warnings
import xmlrpclib

try:
    from django.dispatch import Signal
except ImportError:
    Signal = None

from . import patch
from eulxml import xmlmap
from eulexistdb.exceptions import ExistDBException, ExistDBTimeout

__all__ = ['ExistDB', 'QueryResult', 'ExistDBException', 'EXISTDB_NAMESPACE']

logger = logging.getLogger(__name__)

EXISTDB_NAMESPACE = 'http://exist.sourceforge.net/NS/exist'


def _wrap_xmlrpc_fault(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (socket.timeout, requests.exceptions.ReadTimeout) as err:
            raise ExistDBTimeout(err)
        except (socket.error, xmlrpclib.Fault,
                xmlrpclib.ProtocolError, xmlrpclib.ResponseError,
                requests.exceptions.ConnectionError) as err:
            raise ExistDBException(err)
        # FIXME: could we catch IOerror (connection reset) and try again ?
        # occasionally getting this error (so far exclusively in unit tests)
        # error: [Errno 104] Connection reset by peer
    return wrapper

xquery_called = None
if Signal is not None:
    xquery_called = Signal(providing_args=[
        "time_taken", "name", "return_value", "args", "kwargs"])


class ExistDB(object):
    """Connect to an eXist database, and manipulate and query it.

    Construction doesn't initiate server communication, only store
    information about where the server is, to be used in later
    communications.

    :param server_url: The eXist server URL.  New syntax (as of 0.20)
        expects primary eXist url and *not* the ``/xmlrpc`` endpoint;
        for backwards compatibility, urls that include `/xmlrpc``
        are still handled, and will be parsed to set exist server path
        as well as username and password if specified.  Note that username
        and password parameters take precedence over username
        and password in the server url if both are specified.
    :param username: exist username, if any
    :param password: exist user password, if any
    :param resultType: The class to use for returning :meth:`query` results;
                       defaults to :class:`QueryResult`
    :param encoding:   The encoding used to communicate with the server;
                       defaults to "UTF-8"
    :param verbose:    When True, print XML-RPC debugging messages to stdout
    :param timeout: Specify a timeout for xmlrpc connection
      requests.  If not specified, the global default socket timeout
      value will be used.
    :param keep_alive: Optional parameter, to disable requests built-in
      session handling;  can also be configured in django settings
      with EXISTDB_SESSION_KEEP_ALIVE
    """

    # default timeout, to allow distinguishing between no timeout
    # specified and an explicit timeout of None (e.g., explicit timeout
    # None should override a configured EXISTDB_TIMEOUT)
    DEFAULT_TIMEOUT = object()

    exist_url = None
    username = None
    password = None

    def __init__(self, server_url=None, username=None, password=None,
                 resultType=None, encoding='UTF-8', verbose=False,
                 keep_alive=None, timeout=DEFAULT_TIMEOUT):

        self.resultType = resultType or QueryResult
        datetime_opt = {'use_datetime': True}

        # distinguish between timeout not set and no timeout, to allow
        # easily setting a timeout of None and have it override any
        # configured EXISTDB_TIMEOUT

        if server_url is not None and 'xmlrpc' in server_url:
            self._init_from_xmlrpc_url(server_url)
        else:
            # add username/password to url if set
            self.exist_url = server_url

        # if username/password are supplied, set them
        if username is not None:
            self.username = username
        if password is not None:
            self.password = password

        # if server url or timeout are not set, attempt to get from django settings
        if self.exist_url is None or timeout == ExistDB.DEFAULT_TIMEOUT:
            # Django integration is NOT required, so check for settings
            # but don't error if they are not available.
            try:
                # if django is not installed, we should get an import error
                import django
                # from django.core.exceptions import ImproperlyConfigured
                try:
                    # if django is installed but not used, we get an
                    # "improperly configured" error
                    from django.conf import settings
                    if self.exist_url is None:
                        self.exist_url = self._serverurl_from_djangoconf()

                    # if the default timeout is used, check for a timeout
                    # in django exist settings
                    if timeout == ExistDB.DEFAULT_TIMEOUT:
                        timeout = getattr(settings, 'EXISTDB_TIMEOUT',
                                          ExistDB.DEFAULT_TIMEOUT)

                    # if a keep-alive option is not specified, check
                    # for a django option to configure the session
                    if keep_alive is None:
                        keep_alive = getattr(settings,
                                             'EXISTDB_SESSION_KEEP_ALIVE', None)
                except django.core.exceptions.ImproperlyConfigured:
                    pass
            except ImportError:
                pass

        # if server url is still not set, we have a problem
        if self.exist_url is None:
            raise Exception('Cannot initialize an eXist-db connection without specifying ' +
                            'eXist server url directly or in Django settings as EXISTDB_SERVER_URL')

        # initialize a requests session; used for REST api calls
        # AND for xmlrpc transport
        self.session = requests.Session()
        if self.username is not None and self.password is not None:
            self.session.auth = (self.username, self.password)
        if keep_alive is not None:
            self.session.keep_alive = keep_alive
        self.session_opts = {}
        if timeout is not ExistDB.DEFAULT_TIMEOUT:
            self.session_opts['timeout'] = timeout

        transport = RequestsTransport(timeout=timeout, session=self.session,
                                      url=self.exist_url, **datetime_opt)

        self.server = xmlrpclib.ServerProxy(
                uri='%s/xmlrpc' % self.exist_url.rstrip('/'),
                transport=transport,
                encoding=encoding,
                verbose=verbose,
                allow_none=True,
                **datetime_opt
            )

    def _serverurl_from_djangoconf(self):
        # determine what exist url to use based on django settings, if available
        try:
            from django.conf import settings

            # don't worry about errors on this one - if it isn't set, this should fail
            self.exist_url = settings.EXISTDB_SERVER_URL

            # former syntax had credentials in the server url; warn about the change
            if '@' in self.exist_url:
                warnings.warn('EXISTDB_SERVER_URL should not include eXist user or ' +
                              'password information.  You should update your django ' +
                              'settings to use EXISTDB_SERVER_USER and EXISTDB_SERVER_PASSWORD.')

            # look for username & password
            self.username = getattr(settings, 'EXISTDB_SERVER_USER', None)
            self.password = getattr(settings, 'EXISTDB_SERVER_PASSWORD', None)

            return self.exist_url

        except ImportError:
            pass

    def _init_from_xmlrpc_url(self, url):
        # map old-style xmlrpc url with username/password to
        # new-style initialization
        parsed = urlparse.urlparse(url)
        # add username/password if set
        if parsed.username:
            self.username = parsed.username
        if parsed.password:
            self.password = parsed.password

        # construct base exist url, without xmlrpc extension
        path = parsed.path.replace('/xmlrpc', '')
        # parsed netloc includes username & password; reconstruct without
        if parsed.port is not None:
            netloc = '%s:%s' % (parsed.hostname, parsed.port)
        else:
            netloc = parsed.hostname
        self.exist_url = '%s://%s%s' % (parsed.scheme, netloc, path)

    def restapi_path(self, path):
        # generate rest path to a collection or document
        # FIXME: getting duplicated db path, handle this better
        if path.startswith('/db'):
            path = path[len('/db'):]
        # make sure there is a slash between db and requested path
        if not path.startswith('/'):
            path = '/%s' % path
        return '%s/rest/db%s' % (self.exist_url.rstrip('/'), path)

    def getDocument(self, name):
        """Retrieve a document from the database.

        :param name: database document path to retrieve
        :rtype: string contents of the document

        """
        # REST api; need an error wrapper?
        logger.debug('getDocument %s', self.restapi_path(name))
        response = self.session.get(self.restapi_path(name), stream=False,
                                    **self.session_opts)
        if response.status_code == requests.codes.ok:
            return response.content
        if response.status_code == requests.codes.not_found:
            # matching previous xmlrpc behavior;
            # TODO: use custom exception classes here
            raise ExistDBException('%s not found' % name)

    def getDoc(self, name):
        "Alias for :meth:`getDocument`."
        return self.getDocument(name)

    def createCollection(self, collection_name, overwrite=False):
        """Create a new collection in the database.

        :param collection_name: string name of collection
        :param overwrite: overwrite existing document?
        :rtype: boolean indicating success

        """
        if not overwrite and self.hasCollection(collection_name):
            raise ExistDBException(collection_name + " exists")

        logger.debug('createCollection %s', collection_name)
        return self.server.createCollection(collection_name)

    @_wrap_xmlrpc_fault
    def removeCollection(self, collection_name):
        """Remove the named collection from the database.

        :param collection_name: string name of collection
        :rtype: boolean indicating success

        """
        if (not self.hasCollection(collection_name)):
            raise ExistDBException(collection_name + " does not exist")

        logger.debug('removeCollection %s', collection_name)
        return self.server.removeCollection(collection_name)

    def hasCollection(self, collection_name):
        """Check if a collection exists.

        :param collection_name: string name of collection
        :rtype: boolean

        """
        try:
            logger.debug('describeCollection %s', collection_name)
            self.server.describeCollection(collection_name)
            return True
        except Exception as e:
            # now could be generic ProtocolError
            s = "collection " + collection_name + " not found"
            if hasattr(e, 'faultCode') and (e.faultCode == 0 and s in e.faultString):
                return False
            else:
                raise ExistDBException(e)

    def reindexCollection(self, collection_name):
        """Reindex a collection.
        Reindex will fail if the eXist user does not have the correct permissions
        within eXist (must be a member of the DBA group).

        :param collection_name: string name of collection
        :rtype: boolean success

        """
        if (not self.hasCollection(collection_name)):
            raise ExistDBException(collection_name + " does not exist")

        # xquery reindex function requires that collection name begin with /db/
        if collection_name[0:3] != '/db':
            collection_name = '/db/' + collection_name.strip('/')

        result = self.query("xmldb:reindex('%s')" % collection_name)
        return result.values[0] == 'true'

    @_wrap_xmlrpc_fault
    def hasDocument(self, document_path):
        """Check if a document is present in eXist.

        :param document_path: string full path to document in eXist
        :rtype: boolean

        """
        if self.describeDocument(document_path) == {}:
            return False
        else:
            return True

    @_wrap_xmlrpc_fault
    def describeDocument(self, document_path):
        """Return information about a document in eXist.
        Includes name, owner, group, created date, permissions, mime-type,
        type, content-length.
        Returns an empty dictionary if document is not found.

        :param document_path: string full path to document in eXist
        :rtype: dictionary

        """
        logger.debug('describeResource %s', document_path)
        return self.server.describeResource(document_path)

    @_wrap_xmlrpc_fault
    def getCollectionDescription(self, collection_name):
        """Retrieve information about a collection.

        :param collection_name: string name of collection
        :rtype: boolean

        """
        logger.debug('getCollectionDesc %s', collection_name)
        return self.server.getCollectionDesc(collection_name)

    def load(self, xml, path):
        """Insert or overwrite a document in the database.

        .. Note::

            This method will automatically overwrite existing content
            at the same path without notice.  This is a change from
            versions prior to 0.20.

        :param xml: string or file object with the document contents
        :param path: destination location in the database
        :rtype: boolean indicating success

        """
        if hasattr(xml, 'read'):
            xml = xml.read()

        logger.debug('load %s', path)
        # NOTE: overwrite is assumed by REST
        response = self.session.put(self.restapi_path(path), xml, stream=False,
                                    **self.session_opts)
        if response.status_code == requests.codes.bad_request:
            # response is HTML, not xml...
            # could use regex or beautifulsoup to pull out the error
            raise ExistDBException

        # expect 201 created for new documents, 200 for
        # successful update of an existing document
        # NOTE: testing shows a 201 response every time (perhaps because
        # eXist removes the resource before replacing?)
        # check for either success response
        return response.status_code in [requests.codes.created,
                                        requests.codes.ok]

    @_wrap_xmlrpc_fault
    def removeDocument(self, name):
        """Remove a document from the database.

        :param name: full eXist path to the database document to be removed
        :rtype: boolean indicating success

        """
        logger.debug('remove %s', name)
        return self.server.remove(name)

    @_wrap_xmlrpc_fault
    def moveDocument(self, from_collection, to_collection, document):
        """Move a document in eXist from one collection to another.

        :param from_collection: collection where the document currently exists
        :param to_collection: collection where the document should be moved
        :param document: name of the document in eXist
        :rtype: boolean
        """
        self.query("xmldb:move('%s', '%s', '%s')" % \
                            (from_collection, to_collection, document))
        # query result does not return any meaningful content,
        # but any failure (missing collection, document, etc) should result in
        # an exception, so return true if the query completed successfully
        return True

    @_wrap_xmlrpc_fault
    def query(self, xquery=None, start=1, how_many=10, cache=False, session=None,
        release=None, result_type=None):
        """Execute an XQuery query, returning the results directly.

        :param xquery: a string XQuery query
        :param start: first index to return (1-based)
        :param how_many: maximum number of items to return
        :param cache: boolean, to cache a query and return a session id (optional)
        :param session: session id, to retrieve a cached session (optional)
        :param release: session id to be released (optional)
        :rtype: the resultType specified at the creation of this ExistDB;
                defaults to :class:`QueryResult`.

        """

        # xml_s = self.server.query(xquery, how_many, start, kwargs)
        params = {
            '_howmany': how_many,
            '_start': start,
        }
        if xquery is not None:
            params['_query'] = xquery
        if cache:
            params['_cache'] = 'yes'
        if release is not None:
            params['_release'] = release
        if session is not None:
            params['_session'] = session
        if result_type is None:
            result_type = self.resultType

        opts = ' '.join('%s=%s' % (key.lstrip('_'), val)
                        for key, val in params.iteritems() if key != '_query')
        if xquery:
            debug_query = '\n%s' % xquery
        else:
            debug_query = ''
        logger.debug('query %s%s', opts, debug_query)
        start = time.time()
        response = self.session.get(self.restapi_path(''), params=params,
                                    stream=False, **self.session_opts)

        if xquery_called is not None:
            args = {'xquery': xquery, 'start': start, 'how_many': how_many,
                    'cache': cache, 'session': session, 'release': release,
                    'result_type': result_type}
            xquery_called.send(
                sender=self.__class__, time_taken=time.time() - start,
                name='query', return_value=response, args=[], kwargs=args)

        if response.status_code == requests.codes.ok:
            # successful release doesn't return any content
            if release is not None:
                return True  # successfully released

            # TODO: test unicode handling
            return xmlmap.load_xmlobject_from_string(response.content, result_type)

        # 400 bad request returns an xml error we can parse
        elif response.status_code == requests.codes.bad_request:
            err = xmlmap.load_xmlobject_from_string(response.content, ExistExceptionResponse)
            raise ExistDBException(err.message)

        # not sure if any information is available on other error codes
        else:
            raise ExistDBException(response.content)

        # xml_s = self.server.query(xquery, how_many, start, kwargs)

        # # xmlrpclib tries to guess whether the result is a string or
        # # unicode, returning whichever it deems most appropriate.
        # # Unfortunately, :meth:`~eulxml.xmlmap.load_xmlobject_from_string`
        # # requires a byte string. This means that if xmlrpclib gave us a
        # # unicode, we need to encode it:
        # if isinstance(xml_s, unicode):
        #     xml_s = xml_s.encode("UTF-8")

        # return xmlmap.load_xmlobject_from_string(xml_s, self.resultType)

    @_wrap_xmlrpc_fault
    def executeQuery(self, xquery):
        """Execute an XQuery query, returning a server-provided result
        handle.

        :param xquery: a string XQuery query
        :rtype: an integer handle identifying the query result for future calls

        """
        # NOTE: eXist's xmlrpc interface requires a dictionary parameter.
        #   This parameter is not documented in the eXist docs at
        #   http://demo.exist-db.org/exist/devguide_xmlrpc.xml
        #   so it's not clear what we can pass there.
        logger.debug('executeQuery\n%s', xquery)
        result_id = self.server.executeQuery(xquery, {})
        logger.debug('result id is %s', result_id)
        return result_id

    @_wrap_xmlrpc_fault
    def querySummary(self, result_id):
        """Retrieve results summary from a past query.

        :param result_id: an integer handle returned by :meth:`executeQuery`
        :rtype: a dict describing the results

        The returned dict has four fields:

         * *queryTime*: processing time in milliseconds

         * *hits*: number of hits in the result set

         * *documents*: a list of lists. Each identifies a document and
           takes the form [`doc_id`, `doc_name`, `hits`], where:

             * *doc_id*: an internal integer identifier for the document
             * *doc_name*: the name of the document as a string
             * *hits*: the number of hits within that document

         * *doctype*: a list of lists. Each contains a doctype public
                      identifier and the number of hits found for this
                      doctype.

        """
        # FIXME: This just exposes the existdb xmlrpc querySummary function.
        #   Frankly, this return is just plain ugly. We should come up with
        #   something more meaningful.
        summary = self.server.querySummary(result_id)
        logger.debug('querySummary result id %d : ' % result_id +
                     '%(hits)s hits, query took %(queryTime)s ms' % summary)
        return summary

    @_wrap_xmlrpc_fault
    def getHits(self, result_id):
        """Get the number of hits in a query result.

        :param result_id: an integer handle returned by :meth:`executeQuery`
        :rtype: integer representing the number of hits

        """

        hits = self.server.getHits(result_id)
        logger.debug('getHits result id %d : %s', result_id, hits)
        return hits

    @_wrap_xmlrpc_fault
    def retrieve(self, result_id, position, highlight=False, **options):
        """Retrieve a single result fragment.

        :param result_id: an integer handle returned by :meth:`executeQuery`
        :param position: the result index to return
        :param highlight: enable search term highlighting in result; optional,
            defaults to False
        :rtype: the query result item as a string

        """
        if highlight:
            # eXist highlight modes: attributes, elements, or both
            # using elements because it seems most reasonable default
            options['highlight-matches'] = 'elements'
            # pretty-printing with eXist matches can introduce unwanted whitespace
            if 'indent' not in options:
                options['indent'] = 'no'
        logger.debug('retrieve result id %d position=%d options=%s',
                     result_id, position, options)
        return self.server.retrieve(result_id, position, options)

    @_wrap_xmlrpc_fault
    def releaseQueryResult(self, result_id):
        """Release a result set handle in the server.

        :param result_id: an integer handle returned by :meth:`executeQuery`

        """
        logger.debug('releaseQueryResult result id %d', result_id)
        self.server.releaseQueryResult(result_id)

    @_wrap_xmlrpc_fault
    def setPermissions(self, resource, permissions):
        """Set permissions on a resource in eXist.

        :param resource: full path to a collection or document in eXist
        :param permissions: int or string permissions statement
        """
        # TODO: support setting owner, group ?
        logger.debug('setPermissions %s %s', resource, permissions)
        self.server.setPermissions(resource, permissions)

    @_wrap_xmlrpc_fault
    def getPermissions(self, resource):
        """Retrieve permissions for a resource in eXist.

        :param resource: full path to a collection or document in eXist
        :rtype: ExistPermissions
        """
        return ExistPermissions(self.server.getPermissions(resource))

    def loadCollectionIndex(self, collection_name, index):
        """Load an index configuration for the specified collection.
        Creates the eXist system config collection if it is not already there,
        and loads the specified index config file, as per eXist collection and
        index naming conventions.

        :param collection_name: name of the collection to be indexed
        :param index: string or file object with the document contents (as used by :meth:`load`)
        :rtype: boolean indicating success

        """
        index_collection = self._configCollectionName(collection_name)
        # FIXME: what error handling should be done at this level?

        # create config collection if it does not exist
        if not self.hasCollection(index_collection):
            self.createCollection(index_collection)

        # load index content as the collection index configuration file
        return self.load(index, self._collectionIndexPath(collection_name))

    def removeCollectionIndex(self, collection_name):
        """Remove index configuration for the specified collection.
        If index collection has no documents or subcollections after the index
        file is removed, the configuration collection will also be removed.

        :param collection: name of the collection with an index to be removed
        :rtype: boolean indicating success

        """
        # collection indexes information must be stored under system/config/db/collection_name
        index_collection = self._configCollectionName(collection_name)

        # remove collection.xconf in the configuration collection
        self.removeDocument(self._collectionIndexPath(collection_name))

        desc = self.getCollectionDescription(index_collection)
        # no documents and no sub-collections - safe to remove index collection
        if desc['collections'] == [] and desc['documents'] == []:
            self.removeCollection(index_collection)

        return True

    def hasCollectionIndex(self, collection_name):
        """Check if the specified collection has an index configuration in eXist.

        Note: according to eXist documentation, index config file does not *have*
        to be named *collection.xconf* for reasons of backward compatibility.
        This function assumes that the recommended naming conventions are followed.

        :param collection: name of the collection with an index to be removed
        :rtype: boolean indicating collection index is present

        """
        return self.hasCollection(self._configCollectionName(collection_name)) \
            and self.hasDocument(self._collectionIndexPath(collection_name))


    def _configCollectionName(self, collection_name):
        """Generate eXist db path to the configuration collection for a specified collection
        according to eXist collection naming conventions.
        """
        # collection indexes information must be stored under system/config/db/collection_name
        return "/db/system/config/db/" + collection_name.strip('/')

    def _collectionIndexPath(self, collection_name):
        """Generate full eXist db path to the index configuration file for a specified
        collection according to eXist collection naming conventions.
        """
        # collection indexes information must be stored under system/config/db/collection_name
        return self._configCollectionName(collection_name) + "/collection.xconf"

    # admin functionality; where should this live?

    def create_group(self, group):
        '''Create a group; returns true if the group was created,
        false if the group already exists.  Any other exist exception
        is re-raised.'''
        try:
            self.query('sm:create-group("%s")' % group);
            # returns a query result with no information on success
            return True
        except ExistDBException as err:
            if 'group with name %s already exists' % group in err.message():
                return False
            raise

    def create_account(self, username, password, groups):
        '''Create a user account; returns true if the user was created,
        false if the user already exists.  Any other exist exception
        is re-raised.'''
        try:
            self.query('sm:create-account("%s", "%s", "%s")' % \
                      (username, password, groups))
            return True
        except ExistDBException as err:
            if 'user account with username %s already exists' % username in err.message():
                return False
            # NOTE: might be possible to also get a group error here
            # perhaps just check for 'already exists' ?
            raise


class ExistPermissions(object):
    "Permissions for an eXist resource - owner, group, and active permissions."
    def __init__(self, data):
        self.owner = data['owner']
        self.group = data['group']
        self.permissions = data['permissions']

    def __str__(self):
        return "owner: %s; group: %s; permissions: %s" % (self.owner, self.group, self.permissions)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, str(self))


class QueryResult(xmlmap.XmlObject):
    """The results of an eXist XQuery query"""

    start = xmlmap.IntegerField("@start|@exist:start")
    """The index of the first result returned"""

    values = xmlmap.StringListField("exist:value")
    "Generic value (*exist:value*) returned from an exist xquery"

    session = xmlmap.IntegerField("@exist:session")
    "Session id, when a query is requested to be cached"

    _raw_count = xmlmap.IntegerField("@count|@exist:count")
    @property
    def count(self):
        """The number of results returned in this chunk"""
        return self._raw_count or 0

    _raw_hits = xmlmap.IntegerField("@hits|@exist:hits")
    @property
    def hits(self):
        """The total number of hits found by the search"""
        return self._raw_hits or 0

    @property
    def results(self):
        """The result documents themselves as nodes, starting at
        :attr:`start` and containing :attr:`count` members"""
        return self.node.xpath('*')


class ExistExceptionResponse(xmlmap.XmlObject):
    '''XML exception response returned on an error'''
    #: db path where the error occurred
    path = xmlmap.StringField('path')
    #: error message
    message = xmlmap.StringField('message')
    #: query that generated the error
    query = xmlmap.StringField('query')


# requests-based xmlrpc transport
# https://gist.github.com/chrisguitarguy/2354951
class RequestsTransport(xmlrpclib.Transport):
    """
    Transport for xmlrpclib that uses Requests instead of httplib.

    Additional parameters:

    :param timeout: optional timeout for xmlrpc requests
    :param session: optional requests session; use a custom session
        if your xmlrpc server requires authentication
    :param url: optional xmlrpc url; used to determine if https should
        be used when making xmlrpc requests
    """
    # update user agent to reflect use of requests
    user_agent = "xmlrpclib.py/%s via requests %s" % (xmlrpclib.__version__,
        requests.__version__)

    # boolean flag to indicate whether https should be used or not
    use_https = False

    def __init__(self, timeout=ExistDB.DEFAULT_TIMEOUT, session=None,
                 url=None, *args, **kwargs):
        # if default timeout is requested, use the global socket default
        if timeout is ExistDB.DEFAULT_TIMEOUT:
            timeout = socket.getdefaulttimeout()
        xmlrpclib.Transport.__init__(self, *args, **kwargs)
        self.timeout = timeout
        # NOTE: assumues that if basic auth is needed, it is set
        # on the session that is passed in
        if session:
            self.session = session
        else:
            self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Content-Type': 'application/xml'
        })

        # determine whether https is needed based on the url
        if url is not None:
            self.use_https = (splittype(url)[0] == 'https')

    def request(self, host, handler, request_body, verbose):
        """
        Make an xmlrpc request.
        """
        url = self._build_url(host, handler)
        try:
            resp = self.session.post(url, data=request_body,
                timeout=self.timeout)
        except Exception:
            raise  # something went wrong
        else:
            try:
                resp.raise_for_status()
            except requests.RequestException as err:
                raise xmlrpclib.ProtocolError(url, resp.status_code,
                                              str(err), resp.headers)
            else:
                return self.parse_response(resp)

    def getparser(self):
        # Patch the parser to prevent errors on Apache's extended
        # attributes. See the code in the patch module for details.
        parser, unmarshaller = xmlrpclib.Transport.getparser(self)
        return patch.XMLRpcLibPatch.apply(parser, unmarshaller)

    def parse_response(self, resp):
        """
        Parse the xmlrpc response.
        """
        parser, unmarshaller = self.getparser()
        parser.feed(resp.text)
        parser.close()
        return unmarshaller.close()

    def _build_url(self, host, handler):
        """
        Build a url for our request based on the host, handler and use_http
        property
        """
        scheme = 'https' if self.use_https else 'http'
        return '%s://%s%s' % (scheme, host, handler)
