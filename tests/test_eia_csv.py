import csv
from datetime import date
import io
import unittest
from pipeline.eia_csv import parse_tables


def encode(rows):
    output = io.StringIO(); csv.writer(output).writerows(rows)
    return output.getvalue().encode('cp1252')


def sample():
    day = '9/25/26'
    one = [['STUB_1', day, '9/18/26', 'Difference', 'Percent Change', '9/26/25', 'Difference', 'Percent Change'],
           ['Propane/Propylene', '100.123', '99.000', '1.123', '1', '90', '10', '11'],
           ['STUB_1', 'STUB_2', day, '9/18/26', 'Difference', '9/26/25', 'Difference', day, '9/26/25', 'Percent Change', day, '9/26/25', 'Percent Change'],
           ['Products Supplied', '(35) Propane/Propylene', '100', '1', '1', '1', '1', '80', '1', '1', '1', '1', '1']]
    nine = [['STUB_1', 'STUB_2', day, '9/18/26', '9/26/25', '9/27/24', day, '9/26/25']]
    labels = ['East Coast (PADD 1)', 'Midwest (PADD 2)', 'Gulf Coast (PADD 3)', 'PADDs 4 and 5']
    def row(section, label, value):
        nine.append([section, label, str(value), '1', '1', '1', '70', '1'])
    for section in ['Refiner and Blender Net Production', 'Imports']:
        row(section, 'Propane/Propylene', 100)
        for label, value in zip(labels, [10, 20, 30, 40]): row(section, label, value)
    section = 'Stocks (Million Barrels)'
    row(section, 'Propane/Propylene', '100.123')
    for label, value in zip(labels, [10, 20, 30, 40]): row(section, label, value)
    row(section, 'Propane, fractionated and ready for sale', 15)
    for label, value in zip(labels[:3] + ['Rocky Mountain (PADD 4)', 'West Coast (PADD 5)'], [1, 2, 3, 4, 5]): row(section, label, value)
    row('Exports', 'Propane', 50)
    return one, nine


class EIACSVTests(unittest.TestCase):
    def test_units_precision_and_four_week_column(self):
        one, nine = sample()
        record = parse_tables(encode(one), encode(nine), date(2026, 10, 6))
        self.assertEqual(record['inv_bbl'], 100123000)
        self.assertEqual(record['build_bbl'], 1123000)
        self.assertEqual(record['production_bpd'], 100000)
        self.assertEqual(record['product_supplied_4wk_bpd'], 80000)
        self.assertEqual(record['padd5_ready_bbl'], 5000000)
        self.assertEqual(len(record), 26)

    def test_mixed_release_is_rejected(self):
        one, nine = sample(); nine[0][2] = '9/18/26'
        with self.assertRaisesRegex(ValueError, 'different releases'):
            parse_tables(encode(one), encode(nine))

    def test_missing_region_is_rejected(self):
        one, nine = sample(); del nine[2]
        with self.assertRaisesRegex(ValueError, 'Missing EIA regional flow'):
            parse_tables(encode(one), encode(nine))

    def test_suppression_is_rejected(self):
        one, nine = sample(); one[1][1] = '–'
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            parse_tables(encode(one), encode(nine))
