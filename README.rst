EULexistdb
==========

EULexistdb is a `Python <http://www.python.org/>`_ module that
provides utilities and classes for interacting with the `eXist-db XML
Database <http://exist.sourceforge.net/>`_ (version 1.4) in a
pythonic, object-oriented way, with optional `Django
<https://www.djangoproject.com/>`_ integration.

**eulexistdb.db** provides access to an eXist-db instance through
eXist's `XML-RPC API
<http://exist.sourceforge.net/devguide_xmlrpc.html>`_.

**eulexistdb.query** provides a **QuerySet** class modeled after
`Django QuerySet
<http://docs.djangoproject.com/en/1.3/ref/models/querysets/>`_ in
functionality.  This module provides **model** and **manager** classes
that can be used to connect an `eulxml
<https://github.com/emory-libraries/eulxml>`_ **XmlObject** with the
**QuerySet** class, in order to generate XQueries and return the
results as XmlObject instances.  However, configuring the XmlObject
XPaths to make efficent XQueries against eXist and take advantage of
the full-text index does require expertise and familiarity with eXist.

When used with `Django <https://www.djangoproject.com/>`_,
**eulexistdb** can pull the database connection configuration from
Django settings, provides a custom management command for working with
the collection index configuration index in the configured eXist
database, and also provides a custom template tag that can be used to
highlight full-text search matches.


Dependencies
------------

**eulexistdb** currently depends on
`eulxml <https://github.com/emory-libraries/eulxml>`_.

**eulexistdb** can be used without
`Django <https://www.djangoproject.com/>`_, but additional
functionality is available when used with Django.


Contact Information
-------------------

**eulexistdb** was created by the Digital Programs and Systems Software
Team of `Emory University Libraries <http://web.library.emory.edu/>`_.

libsysdev-l@listserv.cc.emory.edu


License
-------
**eulexistdb** is distributed under the Apache 2.0 License.


Development History
-------------------

For instructions on how to see and interact with the full development
history of **eulexistdb**, see
`eulcore-history <https://github.com/emory-libraries/eulcore-history>`_.

Developer notes
---------------

To install dependencies for your local check out of the code, run ``pip install``
in the ``eulexistdb`` directory (the use of `virtualenv`_ is recommended)::

    pip install -e .

.. _virtualenv: http://www.virtualenv.org/en/latest/

If you want to run unit tests or build sphinx documentation, you will also
need to install development dependencies::

    pip install -e . "eulexistdb[dev]"

Running the unit tests requires an eXist-DB database instance.  Before running tests, you will
need to copy ``test/localsettings.py.dist`` to ``test/localsettings.py`` and edit the
configuration for your test instance of eXist.

To run all unit tests::


    nosetests test/ # for normal development
    nosetests test/ --with-coverage --cover-package=eulexistdb --cover-xml --with-xunit   # for continuous integration

To run unit tests for a specific module, use syntax like this::

    nosetests test/test_existdb/test_db.py


To generate sphinx documentation::

    cd doc
    make html


