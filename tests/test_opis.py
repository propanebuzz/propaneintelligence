import unittest
from pipeline.opis import parse_pages

# Synthetic values; these fixtures contain no source report content.
def sample():
    return ['January 12, 2026\nWTI Crude Oil ($/bbl)\nMonth Price Change\nFEB 70.00 1.00\nMAR 71.00 1.00\nBrent Crude Oil ($/bbl)\nOPIS Mont Belvieu Spot Gas Liquids Prices (cts/gal)\nAny Current Month Prompt Current Month Out Month (Feb)\nProduct Low High Avg MTD Low High Avg MTD Low High Avg MTD\nNon-TET Propane 58 62 60 59 58 62 60 59 58 62 60 59\nTET Propane 68 72 70 69 68 72 70 69 78 82 80 79',
            'OPIS North America LPG Report January 12, 2026\nOPIS Conway In-Well Spot Gas Liquids Prices (cts/gal)\nAny Current Month Prompt Current Month Out Month (Feb)\nProduct Low High Avg MTD Low High Avg MTD Low High Avg MTD\nPropane 48 52 50 49 48 52 50 49 58 62 60 59']

class OpisTests(unittest.TestCase):
    def test_selects_current_average_and_front_month(self):
        r = parse_pages(sample())
        self.assertEqual((r['conway'], r['tet'], r['wti']), (.5, .7, 70))

    def test_conflicting_dates_rejected(self):
        pages = sample(); pages[1] = pages[1].replace('January 12', 'January 13')
        with self.assertRaises(ValueError): parse_pages(pages)

    def test_missing_row_or_layout_rejected(self):
        for source, replacement in [('TET Propane 68', 'TET propane 68'),
                                    ('Product Low High Avg MTD', 'Product High Low Avg MTD')]:
            pages = sample(); pages[0] = pages[0].replace(source, replacement)
            with self.assertRaises(ValueError): parse_pages(pages)

    def test_holiday_and_unknown_blank_report(self):
        self.assertIsNone(parse_pages(['January 12, 2026\nHoliday: no price assessments']))
        with self.assertRaises(ValueError): parse_pages(['January 12, 2026\nUnreadable market table'])
