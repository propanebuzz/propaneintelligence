import unittest
from unittest.mock import patch
from pipeline.weekly_update import weekly_plan

class WeeklyInputTests(unittest.TestCase):
    def test_incomplete_report_rejected_before_authoring(self):
        with patch('pipeline.weekly_update.weekly_observations',return_value=[]),patch('pipeline.weekly_update.load_workbook') as load:
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                weekly_plan('unused',{'date':'2026-09-25'})
            load.assert_not_called()
    def test_non_friday_rejected(self):
        with patch('pipeline.weekly_update.weekly_observations',return_value=[]):
            with self.assertRaisesRegex(ValueError,'Friday'):
                weekly_plan('unused',{'date':'2026-09-26'})
