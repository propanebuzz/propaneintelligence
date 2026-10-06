"""Validate an EIA PDF against the existing workbook without changing Drive."""
import argparse
import hashlib
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pdfplumber
from pipeline.eia import VERSION,parse_pages
from pipeline.storage import PRIVATE,archive_bytes,atomic_json
from pipeline.workbooks import weekly_observations

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('pdf',type=Path)
parser.add_argument('--workbook',type=Path,default=PRIVATE/'access-check/14XA_BnMC8wf0jgXMqKvB21yEi51fbP9q.xlsx')
args=parser.parse_args()
raw=args.pdf.read_bytes()
with pdfplumber.open(args.pdf) as pdf: record=parse_pages([p.extract_text() or '' for p in pdf.pages])
rows=weekly_observations(args.workbook)
existing=next((r for r in rows if r['date']==record['date']),None)
mismatches={k:{'workbook':existing[k],'report':v} for k,v in record.items() if existing and k in existing and existing[k] is not None and existing[k]!=v}
archive_bytes(PRIVATE/'archives/eia',raw,'.pdf')
result={'parser':VERSION,'record':record,'sha256':hashlib.sha256(raw).hexdigest(),'mismatches':mismatches,'action':'review' if mismatches else ('duplicate' if existing else 'insert_preview'),'drive_written':False}
atomic_json(PRIVATE/'state/eia-sample-verification.json',result)
print('EIA',record['date'],result['action'],';',len(mismatches),'mismatches. No workbook changes made.')
if mismatches:raise SystemExit(1)
