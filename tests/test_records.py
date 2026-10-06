import unittest
from pipeline.records import normalize_opis, classify_upsert


class RecordsTest(unittest.TestCase):
    def sample(self):
        return dict(date="2026-01-12", conway=51.25, tet=70, wti=75,
                    propane_unit="cents/gal", wti_unit="USD/bbl")

    def test_conversion_and_repeat(self):
        r = normalize_opis(self.sample())
        self.assertAlmostEqual(r["conway"], .5125)
        self.assertEqual(normalize_opis(r), r)
        self.assertEqual(classify_upsert([], r), "insert")
        self.assertEqual(classify_upsert([r], r), "duplicate")

    def test_empty_and_partial(self):
        self.assertIsNone(normalize_opis({}))
        self.assertEqual(classify_upsert([], None), "skip_empty")
        r = self.sample(); r["tet"] = None
        with self.assertRaises(ValueError): normalize_opis(r)

    def test_invalid_values_dates_units(self):
        for key, value in [("wti", float("nan")), ("conway", True), ("tet", -1),
                           ("date", "2026-02-30"), ("propane_unit", "unknown")]:
            r = self.sample(); r[key] = value
            with self.assertRaises(ValueError): normalize_opis(r)

    def test_revision_and_duplicate_history(self):
        r = normalize_opis(self.sample()); changed = dict(r, wti=90)
        self.assertEqual(classify_upsert([r], changed), "revision")
        with self.assertRaises(ValueError): classify_upsert([r, r], changed)

    def test_zero_is_observed(self):
        r = self.sample(); r["conway"] = 0
        self.assertEqual(normalize_opis(r)["conway"], 0)
