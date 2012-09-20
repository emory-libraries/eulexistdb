# file eulexistdb/__init__.py
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

"""Interact with `eXist-db`_ XML databases.

This package provides classes to ease interaction with eXist XML databases.
It contains the following modules:

 * :mod:`eulexistdb.db` -- Connect to the database and query
 * :mod:`eulexistdb.query` -- Query :class:`~eulxml.xmlmap.XmlObject`
   models from eXist with semantics like a Django_ QuerySet

.. _eXist-db: http://exist.sourceforge.net/
.. _Django: http://www.djangoproject.com/

"""

__version_info__ = (0, 15, 3, None)

# Dot-connect all but the last. Last is dash-connected if not None.
__version__ = '.'.join([ str(i) for i in __version_info__[:-1] ])
if __version_info__[-1] is not None:
    __version__ += ('-%s' % (__version_info__[-1],))

