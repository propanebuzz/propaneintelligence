import unittest
from scripts.backfill_eia_reports import supplement, correct_approved_midwest


class BackfillTests(unittest.TestCase):
    def test_fills_missing_without_rewriting_core(self):
        rows = [{'date':'2026-11-06','inv':104.2,'imports_bpd':None}]
        self.assertEqual(supplement(rows,{'date':'2026-11-06','inv_bbl':104200000,'imports_bpd':124000}),1)
        self.assertEqual(rows[0]['inv'],104.2)
        self.assertEqual(rows[0]['imports_bpd'],124000)
        self.assertEqual(supplement(rows,{'date':'2026-11-06','imports_bpd':124000}),0)

    def test_revision_stops(self):
        with self.assertRaisesRegex(ValueError,'revises'):
            supplement([{'date':'2026-11-06','imports_bpd':124000}],
                       {'date':'2026-11-06','imports_bpd':129000})

    def test_unmatched_week_stops(self):
        with self.assertRaises(ValueError): supplement([],{'date':'2026-11-06'})

    def test_exact_approved_correction_reconciles_regions(self):
        rows = [{'date':'2026-11-06','midwest':25.6,'other':13.6,'inv':104.2,'gulf':65.0}]
        report = {'date':'2026-11-06','midwest_bbl':24600000}
        correct_approved_midwest(rows,report)
        self.assertEqual(rows[0]['midwest'],24.6)
        self.assertEqual(rows[0]['other'],14.6)
        self.assertEqual(rows[0]['inv'],104.2)
        self.assertEqual(supplement(rows,report),0)

    def test_approval_does_not_allow_other_revisions(self):
        with self.assertRaises(ValueError):
            correct_approved_midwest([],{'date':'2026-10-30','midwest_bbl':24600000})
