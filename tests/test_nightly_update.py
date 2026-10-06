import unittest
from scripts.nightly_update import steps


class NightlyTests(unittest.TestCase):
    def test_read_only_stages_without_upload(self):
        self.assertEqual(steps(False, {}), ['run_pipeline.py', 'stage_daily_update.py'])

    def test_apply_requires_explicit_deployment_flag(self):
        with self.assertRaisesRegex(RuntimeError, 'deployment checks'):
            steps(True, {'live_updates_enabled': False})

    def test_verified_upload_followed_by_fresh_snapshot(self):
        self.assertEqual(steps(True, {'live_updates_enabled': True})[-2:],
                         ['apply_daily_update.py', 'run_pipeline.py'])
