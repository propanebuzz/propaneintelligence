import unittest
from pipeline.eia import _numbers,_block

class EiaLayoutTests(unittest.TestCase):
    def test_units_and_missing_are_distinct(self):
        self.assertEqual(_numbers('Stocks..... 18.0 –',2),[18.0,None])
        with self.assertRaises(ValueError):_numbers('Flow..... 75 90',6)
    def test_imports_not_product_supplied(self):
        page='Table 9.\nImports\nPropane/Propylene..... 75 90 133 86 87 111\nEast Coast (PADD 1)..... 9 10 59 24 12 37\nMidwest (PADD 2)..... 30 41 40 24 39 37\nGulf Coast (PADD 3)..... 0 0 0 1 0 0\nPADDs 4 and 5..... 36 39 34 37 36 37\nProduct Supplied\nPropane/Propylene..... 1085 764 534 879 886 787'
        blocks=_block([page],'Propane/Propylene','Imports')
        self.assertEqual(len(blocks),1)
        self.assertEqual(_numbers(blocks[0][0],6)[0],75)
