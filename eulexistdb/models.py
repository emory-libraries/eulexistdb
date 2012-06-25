# file eulexistdb/models.py
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

from eulexistdb.manager import Manager
from eulxml.xmlmap.core import XmlObject, XmlObjectType

class _ManagerDescriptor(object):
    def __init__(self, manager):
       self.manager = manager

    def __get__(self, instance, type=None):
        if instance is not None:
            raise AttributeError, "Manager isn't accessible via %s instances" % (type.__name__,)
        return self.manager


class XmlModelType(XmlObjectType):

    """
    A metaclass for :class:`XmlModel`.

    This metaclass is derived from
    :class:`~eulxml.xmlmap.core.XmlObjectType` and further extends the
    additions that metaclass makes to its instance classes. In addition to
    collecting and translating fields, we:
      1. take any :class:`~eulexistdb.manager.Manager members
         and convert them to descriptors, and
      2. store all of these managers in a ``_managers`` dictionary on the
         class.
    """

    def __new__(cls, name, bases, defined_attrs):
        use_attrs = {}
        managers = {}

        for attr_name, attr_val in defined_attrs.items():
            # XXX: like in XmlObjectType, not a fan of isinstance here.
            # consider using something like django's contribute_to_class.

            # in any case, we handle managers and then pass everything else
            # up to the metaclass parent (XmlObjectType) to handle other
            # things like fields.
            if isinstance(attr_val, Manager):
                manager = attr_val
                managers[attr_name] = manager
                use_attrs[attr_name] = _ManagerDescriptor(manager)

            else:
                use_attrs[attr_name] = attr_val
        use_attrs['_managers'] = managers

        # XXX: do we need to ensure a default model like django relational
        # Models do? i don't think we need it right now, but we might in the
        # future.

        super_new = super(XmlModelType, cls).__new__
        new_class = super_new(cls, name, bases, use_attrs)

        # and then patch that new class into the managers:
        for manager in managers.values():
            manager.model = new_class

        return new_class


class XmlModel(XmlObject):

    """
    An :class:`~eulxml.xmlmap.XmlObject` in an
    :class:`eulexistdb.db.ExistDB`.

    ``XmlModel`` is derived from :class:`~eulxml.xmlmap.XmlObject` and
    thus has access to all the :ref:`field <xmlmap-field>` logic
    provided by that class. Additionally, since ``XmlModel`` objects
    are stored in an :class:`~eulexistdb.db.ExistDB`, they can define
    :class:`~eulexistdb.manager.Manager` members for easy access to
    stored models.
    """

    __metaclass__ = XmlModelType
