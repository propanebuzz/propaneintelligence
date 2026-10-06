from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from pipeline.package_edit import merge_numeric,verify_package


def package(xml,macro=b'preserve-vba'):
    stream=BytesIO()
    with ZipFile(stream,'w') as z:
        z.writestr('xl/worksheets/sheet1.xml',xml)
        z.writestr('xl/vbaProject.bin',macro)
        z.writestr('xl/styles.xml',b'<styles/>')
        z.writestr('xl/worksheets/sheet2.xml',b'<untouched/>')
    return stream.getvalue()

BASE='<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="2"><c r="A2" s="4"><v>46000</v></c><c r="B2" s="5"><v>0.5</v></c><c r="C2" s="5"><v>0.7</v></c><c r="D2" s="6"><v>75</v></c></row></sheetData></worksheet>'

class PackageTests(unittest.TestCase):
    def test_append_preserves_all_other_parts_and_old_row(self):
        authored=package(BASE.replace('r="2"','r="3"').replace('A2','A3').replace('B2','B3').replace('C2','C3').replace('D2','D3'))
        plan={'sheet_part':'xl/worksheets/sheet1.xml','cells':{'A3':46000,'B3':.5,'C3':.7,'D3':75}}
        result=merge_numeric(package(BASE),authored,plan)
        verify_package(package(BASE),result,plan['sheet_part'])
        with ZipFile(BytesIO(result)) as z:
            xml=z.read(plan['sheet_part']).decode()
            self.assertIn(BASE.split('<sheetData>')[1].split('</sheetData>')[0],xml)
            self.assertIn('<c r="A3" s="4">',xml)
            self.assertEqual(z.read('xl/vbaProject.bin'),b'preserve-vba')
    def test_authored_value_mismatch_rejected(self):
        with self.assertRaises(ValueError):merge_numeric(package(BASE),package(BASE),{'sheet_part':'xl/worksheets/sheet1.xml','cells':{'A2':1}})
    def test_formula_overwrite_rejected(self):
        source=package(BASE.replace('<v>0.5</v>','<f>1/2</f><v>0.5</v>'))
        plan={'sheet_part':'xl/worksheets/sheet1.xml','cells':{'A2':46000,'B2':.5,'C2':.7,'D2':75}}
        with self.assertRaises(ValueError):merge_numeric(source,package(BASE),plan)
    def test_no_change_is_byte_identical(self):
        source=package(BASE)
        self.assertEqual(merge_numeric(source,b'',{'cells':{}}),source)
