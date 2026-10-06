import unittest
from pipeline.analytics import monthly_prices,reconciliation_flags


class AnalyticsTests(unittest.TestCase):
    def test_monthly_mean_uses_all_prices_and_skips_zero_crude_ratio(self):
        daily=[{'date':'2026-01-01','cwy':.5,'tet':.6,'wti':50},
               {'date':'2026-01-02','cwy':.7,'tet':.8,'wti':0},
               {'date':'2026-02-02','cwy':1,'tet':1.1,'wti':70}]
        result=monthly_prices(daily)
        self.assertAlmostEqual(result[0]['cwy'],.6)
        self.assertAlmostEqual(result[0]['cwy_ratio'],42)
        self.assertEqual(result[0]['n'],2)
        self.assertEqual(len(result),2)

    def test_flags_only_true_seven_day_discrepancies(self):
        rows=[{'date':'2026-01-02','inv':10,'build':0,'row':2},
              {'date':'2026-01-09','inv':11,'build':.2,'row':3},
              {'date':'2026-01-23','inv':15,'build':1,'row':4},
              {'date':'2026-01-30','inv':15.2,'build':0,'row':5}]
        flags=reconciliation_flags(rows)
        self.assertEqual([r['date'] for r in flags],['2026-01-09'])
