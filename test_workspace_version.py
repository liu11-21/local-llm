import unittest
from check_workspace_version import check
from workspace_version import VERSION, build_info, require_identity
from app_update import select_workspace_update


class WorkspaceVersionTests(unittest.TestCase):
    def test_first_party_versions_and_mixed_worker_rejection(self):
        self.assertEqual(check()['version'], '0.7.0')
        self.assertEqual(require_identity(build_info())['version'], VERSION)
        for changed in ({'version':'0.6.2'}, {'channel':'Stable'}, {'commit':'other'}):
            with self.assertRaisesRegex(ValueError, '不一致'):
                require_identity({**build_info(), **changed}, expected_commit=build_info()['commit'])

    def test_development_does_not_offer_legacy_or_absent_releases(self):
        self.assertIsNone(select_workspace_update([], VERSION))
        self.assertIsNone(select_workspace_update([{'tag_name':'v0.6.2'}, {'tag_name':'v9.9.9'},
                                                  {'tag_name':'workspace-v0.7.0'}], VERSION))
