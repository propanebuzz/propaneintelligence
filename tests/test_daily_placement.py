from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from openpyxl import Workbook
from pipeline.package_edit import daily_plan


def record(day):
    return dict(date=day,conway=.86,tet=.915,wti=89.44,propane_unit='USD/gal',wti_unit='USD/bbl')


class DailyPlacementTests(unittest.TestCase):
    def fixture(self, folder, gap=False):
        path=Path(folder)/'daily.xlsx'
        w=Workbook();s=w.active;s.title='Sheet1'
        s.append(['Date','Conway','TET','WTI'])
        s.append([datetime(2026,10,6),.86,.915,89.44])
        s.append([datetime(2026,10,5),.87375,.93,89.43])
        for row in (2,3):s.cell(row,1).number_format='mm/dd/yyyy'
        s.cell(999,1).number_format='mm/dd/yyyy'
        if gap:
            for col in range(1,5):s.cell(1000,col).value=s.cell(3,col).value;s.cell(3,col).value=None
            s.cell(1000,1).number_format='mm/dd/yyyy'
        w.save(path);w.close();return path

    def test_new_report_goes_to_row_2_not_after_formatted_row_999(self):
        with tempfile.TemporaryDirectory() as d:
            plan=daily_plan(self.fixture(d),[record('2026-10-07')])
            self.assertEqual(set(plan['cells']),{f'{col}{row}' for col in 'ABCD' for row in (2,3,4)})
            self.assertEqual(plan['cells']['A2'],46302)
            self.assertEqual(plan['cells']['B4'],.87375)

    def test_multiple_catchup_reports_sort_newest_first(self):
        with tempfile.TemporaryDirectory() as d:
            plan=daily_plan(self.fixture(d),[record('2026-10-07'),record('2026-10-08')])
            self.assertGreater(plan['cells']['A2'],plan['cells']['A3'])
            self.assertGreater(plan['cells']['A3'],plan['cells']['A4'])
            self.assertEqual(len(plan['cells']),16)

    def test_duplicate_does_not_rewrite_history(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(daily_plan(self.fixture(d),[record('2026-10-06')])['cells'],{})

    def test_existing_misplaced_record_stops_for_review(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'not contiguous'):
                daily_plan(self.fixture(d,gap=True),[record('2026-10-07')])
