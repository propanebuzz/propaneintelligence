from datetime import datetime
import unittest
from scripts.import_local_sources import merge_weekly


class LocalImportTests(unittest.TestCase):
    def test_residual_demand_not_imported(self):
        values = [datetime(2026,10,16),2026,'2026-2027',29,
                  105800000,26100000,65900000,13800000,70200000,
                  35600000,-500000,2032000,2889000,928428,0,0,0,0]
        record = {'date':'2026-10-16','product_supplied_bpd':1020000,
                  'imports_bpd':88000,'ready_bbl':70200000}
        row = merge_weekly([(2,values)],[],record)[0]
        self.assertEqual(row['product_supplied_bpd'],1020000)
        self.assertEqual(row['imports_bpd'],88000)
        self.assertEqual(row['ready'],70.2)
        self.assertIsNone(row['padd1_ready_bbl'])

    def test_conflicting_pdf_stops(self):
        values = [datetime(2026,10,16),2026,'2026-2027',29]+[None]*14
        values[8] = 70200000
        with self.assertRaisesRegex(ValueError,'conflict'):
            merge_weekly([(2,values)],[],{'date':'2026-10-16','ready_bbl':80000000})
