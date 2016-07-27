Change & Version Information
============================

The following is a summary of changes and improvements to
:mod:`eulexistdb`.  New features in each version should be listed, with
any necessary information about installation or upgrade notes.

0.21 (preliminary)
------------------

* Removed unused kwargs from db.ExistDB init method
  `#1 <https://github.com/emory-libraries/eulexistdb/issues/1>`_
* db.ExistDB ``create_group`` and ``create_account`` methods now re-raise
  unexpected errors
  `#2 <https://github.com/emory-libraries/eulexistdb/issues/2>`_
* Improved timeout handling; fixes timeouts on REST API requests
  `#3 <https://github.com/emory-libraries/eulexistdb/issues/3>`_
* bugfix: make Django settings actually optional
* Require eulxml 1.1.2 to handle duplicate ``xml:id`` attributes included
  in a single exist result.  (Duplicate id test case contributed by
  `@lddubeau <https://github.com/lddubeau>`_ in
  `PR #5 <https://github.com/emory-libraries/eulexistdb/pull/5>`_ )
* Add opt-in patch for extended type handling in xmlrpc.
  Contributed by  `@lddubeau <https://github.com/lddubeau>`_ in
  `PR #6 <https://github.com/emory-libraries/eulexistdb/pull/6>`_,
  resolves `#4 <https://github.com/emory-libraries/eulexistdb/issues/4>`_
* Removed ``overwrite`` option from `eulexistdb.ExistDB.load`
  (no longer applicable under the REST API, and misleading)
  `#9 <https://github.com/emory-libraries/eulexistdb/issues/9>`_
* Improved django-debug-toolbar integration.
  `#7 <https://github.com/emory-libraries/eulexistdb/issues/7>`_,
  `#8 <https://github.com/emory-libraries/eulexistdb/issues/8>`_
* Updated `Existdb.DB` initialization parameters to restore support for
  xmlrpc-style urls with username and password used in previous versions
  of eulexistdb. `#10 <https://github.com/emory-libraries/eulexistdb/issues/10>`_
* Updated unit tests so they can be run with and without django, in order
  to test that eulexistdb works properly without django.
* Configured unit tests on travis-ci to test with and without django.

0.20
----

* **NOTE:** :class:`Existdb.DB` initialization parameters has changed;
  server url is no longer expected to include full xmlrpc path.
* Updated and tested for compatibility with eXist-db 2.2
* Improved :class:`eulexistdb.query.QuerySet` efficiency when retrieving
  results (now retrieves chunked results using eXist REST API,
  making fewer requests to the server)
* Simple xml-based query syntax now supported via
  :class:`eulexistdb.query.XmlQuery`
* Updated for compatibility with current versions of Django
* Now uses `requests <http://docs.python-requests.org/>` for REST API
  access and as XML-RPC transport for improved handling and connection
  pooling.
* New custom django-debug-toolbar panel to view existdb xqueries
  used to generate a django page.

0.19.2
------

* Unittest2 and Django test runner are now optional when using testutils.

0.19.1
------

* Basic support for preceding/following/preceding-sibling/following-sibling
  queries when returning additional fields from a query via XmlModel.
* Bugfix: support xml returns for xpaths ending with node() or *

0.19
----
* New method for sorting a :class:`eulexistdb.query.QuerySet`
  by a raw XPath, for those cases when the desired sort xpath cannot be
  specified as an :mod:`xmlmap` field:
  :meth:`eulexistdb.query.QuerySet.order_by_raw`
* The Django manage.py script for managing eXist-DB index configuration
  files now takes optional username and password credentials, for use
  with sites that run in guest mode or with limited access.
* bugfix: :class:`~eulexistdb.query.QuerySet` greater than and less than
  filters no longer assume numeric values should be treated as numbers,
  to allow comparison of string values of numbers.
* bugfix: :class:`~eulexistdb.query.Xquery` now correctly generates
  xqueries with more than one where statement.

0.18
----

* New filters and operators supported on :class:`eulexistdb.query.QuerySet`:
  * ``exists`` - filter on the presence of absence of a node
  * comparison operators ``gt``, ``gte``, ``lt``, ``lte``
* Support for excluding documents using all existing filters
  with new method :meth:`eulexistdb.query.QuerySet.exclude`.

0.17
----

* Support for restricting xqueries to a single document in
  :class:`eulexistdb.query.QuerySet` with ``document_path`` filter.

0.16
----

* Development requirements can now be installed as an optional requirement
  of the eulexistdb package (``pip install "eulexistdb[dev]"``).
* Unit tests have been updated to use :mod:`nose`
* Provides a nose plugin to set up and tear down an eXist database collection
  for tests, as an alternative to the custom test runners.

0.15.2
------

* Update to latest released version of :mod:`eulxml` (0.18.0) with
  backwards-incompatible DateField/DateTimeField change.

0.15.1 - Bugfix Release
-----------------------

* Support Python 2.7.
* Rearrange test code to support easier recombination.

0.15.0 - Initial Release
------------------------

* Split out existdb-specific components from :mod:`eulcore`; now
  depends on :mod:`eulxml`.
