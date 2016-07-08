import unittest
from mock import patch, Mock

from eulexistdb import patch as db_patch

class Foo(db_patch.Patch):
    pass

class PatchTest(unittest.TestCase):
    def tearDown(self):
        db_patch.requested_patches = set()

    def test_request_patching_single_class(self):
        """
        We can request a single patch.
        """
        db_patch.request_patching(db_patch.XMLRpcLibPatch)
        self.assertEqual(len(db_patch.requested_patches), 1)

    def test_request_patching_list(self):
        """
        We can request a list of patches.
        """
        db_patch.request_patching([db_patch.XMLRpcLibPatch,
                                Foo])
        self.assertEqual(len(db_patch.requested_patches), 2)

    def test_request_patching_duplicate(self):
        """
        Requesting the same patch more than once registers only once.
        """
        db_patch.request_patching([db_patch.XMLRpcLibPatch,
                                db_patch.XMLRpcLibPatch])
        self.assertEqual(len(db_patch.requested_patches), 1)

    def test_request_patching_unknown_patch(self):
        """
        Requesting an unknown patch raises ValueError
        """
        self.assertRaises(ValueError,
                          db_patch.request_patching, object())

    def test_patch_is_not_requested(self):
        """
        A patch is not requested before it is actually requested.
        """
        self.assertFalse(db_patch.XMLRpcLibPatch.requested())

    def test_patch_is_requested(self):
        """
        A patch is requested once the call has been made.
        """
        db_patch.request_patching(db_patch.XMLRpcLibPatch)
        self.assertTrue(db_patch.XMLRpcLibPatch.requested())

    def test_xmlrpclib_not_warranted(self):
        """
        Simulate xmlrpclib not failing so that the patch is not warranted.
        """
        # We set things so that getparser will return mocks that won't
        # cause an exception when the test is run, so the test will pass
        # and the patch won't be warranted.
        with patch("eulexistdb.patch.xmlrpclib.getparser") as getparser:
            getparser.return_value = (Mock(), Mock())
            # Clear the cached value. So that it is recomputed.
            db_patch.XMLRpcLibPatch._warranted = None
            self.assertFalse(db_patch.XMLRpcLibPatch.warranted())
