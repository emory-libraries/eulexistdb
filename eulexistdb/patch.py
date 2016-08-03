"""
Manage and apply patches necessary to work around issues in
third-party libraries.
"""
import xmlrpclib
import collections
from decimal import Decimal

requested_patches = set()

class Patch(object):
    """Base for the patches we manage in this module."""

    @classmethod
    def warranted(cls):
        """
        Whether the patch is warranted or not. A patch is warranted if
        there is really a problem to work around. The default
        implementation always resolves to ``True`` but subclasses
        should perform tests to determine whether the patch is going
        to actually fix something.
        """
        return True

    @classmethod
    def requested(cls):
        """
        Whether this patch was requested.
        """
        return cls in requested_patches


# Utility function for XMLRpcLibPatch.
def _end_bigdecimal(self, data):
    self.append(Decimal(data))
    self._value = 0

class XMLRpcLibPatch(Patch):
    """
    Patch to work around an issue in xmlrpclib whereby it is unable to
    handle the Apache extended types. These types can be returned by
    eXist. Therefore, we must be able to handle them.

    This patch is inspired by the work done by Serhiy Storchaka on
     patching xmlrpclib. See this bug report:

    https://bugs.python.org/issue26885
    """

    _warranted = None

    @classmethod
    def warranted(cls):
        # We cache it so that we don't actually retest.
        if cls._warranted is not None:
            return cls._warranted

        good = True
        parser, unmarshaller = xmlrpclib.getparser()
        try:
            # This will fail if the unmarshaller is unable to handle ex:nil.
            # We do not test for every value that we patch for. We assume if
            # ex:nil won't work, no other extended value will.
            parser.feed("<params><param><value><ex:nil/></value></param></params>")
        except xmlrpclib.ResponseError:
            good = False

        # Trying to close if there was an error earlier won't work.
        if good:
            parser.close()
            unmarshaller.close()

        cls._warranted = not good
        return cls._warranted

    @classmethod
    def apply(cls, parser, unmarshaller):
        """
        Apply the patch to a ``parser`` and ``unmarshaller`` obtained from
        xmlrpclib, but only if requested and warranted.
        """
        if cls.requested() and cls.warranted():
            return cls.patch_parser(parser, unmarshaller)

        return parser, unmarshaller

    @classmethod
    def patch_parser(cls, parser, unmarshaller):
        """
        Patch the "parser". It is actually the unmarshaller that gets
        patched but the other related functions are named
        ``get_parser``, etc.

        This code is not patching xmlrpclib objects directly. This is an
        intentional decision. Patching xmlrpclib would mean that any
        code using it would use the patch. Rather than assume the
        patch is desirable in every situation, we conservativaly
        perform the fix only on objects passed to it.
        """
        # Create a private copy.
        unmarshaller.dispatch = dispatch = dict(unmarshaller.dispatch)

        end_int = dispatch["int"]
        dispatch.update({
            "ex:i1": end_int,
            "ex:i2": end_int,
            "ex:biginteger": end_int,
            "ex:float": dispatch["double"],
            "ex:bigdecimal": _end_bigdecimal,
            "ex:nil": dispatch["nil"],
            "ex:i8": dispatch["i8"]
        })

        return parser, unmarshaller

def request_patching(patches):
    """
    Request that patches be applied. This effectively adds to the set
    of patches that are requested.

    :param patches: A single class, or a sequence of classes. All
    classes must be derived from `:class:Patch`.
    """
    if not isinstance(patches, collections.Iterable):
        # A single value was passed, make it iterable.
        patches = [patches]

    subclasses = set(Patch.__subclasses__())

    for patch in patches:
        if patch in requested_patches:
            # Already in the map...
            continue

        if patch not in subclasses:
            raise ValueError(str(patch) + " is not a valid class")

        requested_patches.add(patch)
