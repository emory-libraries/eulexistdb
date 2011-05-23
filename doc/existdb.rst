:mod:`eulcore.existdb` -- Store and retrieve data in an eXist database
======================================================================

.. automodule:: eulexistdb

.. FIXME: automodules here rely on undoc-members to include undocumented
     members in the output documentation. We should move away from this,
     preferring instead to add docstrings and/or reST docs right here) for
     members that need documentation.

See :mod:`eulcore.django.existdb` for existdb and django integration.

Direct database access
----------------------

.. automodule:: eulexistdb.db

   .. autoclass:: ExistDB(server_url[, resultType[, encoding[, verbose]]])
      :members:

      .. automethod:: getDocument(name)

      .. automethod:: createCollection(collection_name[, overwrite])

      .. automethod:: removeCollection(collection_name)

      .. automethod:: hasCollection(collection_name)

      .. automethod:: load(xml, path[, overwrite])

      .. automethod:: query(xquery[, start[, how_many]])

      .. automethod:: executeQuery(xquery)

      .. automethod:: querySummary(result_id)

      .. automethod:: getHits(result_id)

      .. automethod:: retrieve(result_id, position)

      .. automethod:: releaseQueryResult(result_id)

   .. autoclass:: QueryResult
      :members:

   .. autoexception:: ExistDBException


Object-based searching
----------------------

.. automodule:: eulexistdb.query

   .. autoclass:: QuerySet
      :members:


Django tie-ins for :mod:`eulexistdb`
------------------------------------


.. automodule:: eulexistdb.manager
   :members:

.. automodule:: eulexistdb.models

   .. autoclass:: XmlModel

      Two use cases are particularly common. First, a developer may wish to
      use an ``XmlModel`` just like an :class:`~eulxml.xmlmap.XmlObject`,
      but with the added semantics of being eXist-backed::
      
        class StoredWidget(XmlModel):
            name = StringField("name")
            quantity = IntegerField("quantity")
            top_customers = StringListField("(order[@status='active']/customer)[position()<5]/name")
            objects = Manager("//widget")

      Second, if an :class:`~eulxml.xml.XmlObject` is defined elsewhere, an
      application developer might simply expose
      :class:`~eulexistdb.db.ExistDB` backed objects::

        class StoredThingie(XmlModel, Thingie):
            objects = Manager("/thingie")

      Of course, some applications ask for mixing these two cases, extending
      an existing :class:`~eulxml.xml.XmlObject` while adding
      application-specific fields::

        class CustomThingie(XmlModel, Thingie):
            best_foobar = StringField("qux/fnord[@application='myapp']/name")
            custom_detail = IntegerField("detail/@level")
            objects = Manager("/thingie")

      In addition to the fields inherited from
      :class:`~eulxml.xmlmap.XmlObject`, ``XmlModel`` objects have one
      extra field:

      .. attribute:: _managers

         A dictionary mapping manager names to
         :class:`~eulcexistdb.manager.Manager` objects. This
         dictionary includes all of the managers defined on the model
         itself, though it does not currently include managers inherited
         from the model's parents.

Custom Template Tags
^^^^^^^^^^^^^^^^^^^^

.. automodule:: eulexistdb.templatetags.existdb
    :members:

:mod:`~eulexistdb` Management commands
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following management command will be available when you include
:mod:`eulexistdb` in your django ``INSTALLED_APPS`` and rely on the
existdb settings described above.

For more details on these commands, use ``manage.py <command> help``

 * **existdb** - update, remove, and show information about the index
   configuration for a collection index; reindex the configured
   collection based on that index configuration

:mod:`~eulexistdb.testutil` Unit Test utilities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: eulexistdb.testutil
    :members:
