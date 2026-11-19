"""Fill missing official EIA detail in saved dashboard rows; never rewrite history."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pdfplumber
from pipeline.eia import parse_pages
from pipeline.storage import PRIVATE, archive_bytes, atomic_json, run_lock
from pipeline.workbooks import FIELDS
from scripts.import_local_sources import PDF_FIELDS, LEGACY
from scripts.build_dashboard import build
from scripts.export_site import export


def supplement(rows, record):
    matches = [r for r in rows if r['date'] == record['date']]
    if len(matches) != 1: raise ValueError('Report week must match one saved observation')
    row = matches[0]
    changes = 0
    for key, value in record.items():
        if key == 'date': continue
        target, divisor = PDF_FIELDS.get(key,(key,1))
        if target not in FIELDS.values(): continue
        incoming = value/divisor
        old = row.get(target)
        if target in LEGACY.values():
            if old is None or not math.isclose(old,incoming,abs_tol=0.050001):
                raise ValueError('Report conflicts with saved core history: '+target)
            continue
        if old is not None and not math.isclose(old,incoming,abs_tol=1e-6):
            raise ValueError('Report revises saved official detail: '+target)
        if old is None:
            row[target] = incoming
            changes += 1
    return changes


def correct_approved_midwest(rows, record):
    """Apply only the exact November 6 correction approved by the user."""
    if record['date'] != '2026-11-06' or record['midwest_bbl'] != 24600000:
        raise ValueError('Approved correction does not match report')
    row = next(r for r in rows if r['date'] == record['date'])
    if row['midwest'] not in (25.6,24.6):
        raise ValueError('Approved correction does not match saved history')
    before = {'midwest':row['midwest'],'other':row['other']}
    row['midwest'] = 24.6
    row['other'] = round(row['inv'] - row['midwest'] - row['gulf'],10)
    return {'week':record['date'],'before':before,
            'after':{'midwest':row['midwest'],'other':row['other']}}


def run(paths, correct_nov6_midwest=False):
    with run_lock(PRIVATE/'state/nightly.lock'):
        previous = json.loads((PRIVATE/'state/dashboard-last-good.json').read_text())
        rows = deepcopy(previous['archive'])
        sources = deepcopy(previous['meta']['sources'][2:])
        plans = []
        corrections = []
        for path in paths:
            with pdfplumber.open(path) as doc:
                record = parse_pages([p.extract_text() or '' for p in doc.pages])
            if correct_nov6_midwest and record['date'] == '2026-11-06':
                corrections.append(correct_approved_midwest(rows,record))
            changes = supplement(rows,record)
            archived,digest = archive_bytes(PRIVATE/'archives/local-imports',path.read_bytes(),'.pdf')
            if digest not in {s['sha256'] for s in sources}:
                sources.append({'file':'EIA supplied PDF','sha256':digest})
            plans.append({'week':record['date'],'fields_added':changes,'sha256':digest})
        if correct_nov6_midwest and not corrections:
            raise ValueError('Approved correction requires the November 6 report')
        originals = []
        for source in previous['meta']['sources'][:2]:
            matches = list((PRIVATE/'archives/local-imports').glob(source['sha256']+'.xlsx'))
            if len(matches) != 1: raise ValueError('Archived input workbook missing')
            originals.append(matches[0])
        atomic_json(PRIVATE/'archives/pre-import'/('snapshot-'+previous['meta']['built'].replace(':','-')+'.json'),previous)
        detail_start = min(r['date'] for r in rows if r['season'] == rows[-1]['season']
                           and r['product_supplied_bpd'] is not None)
        missing = [r['date'] for r in rows if r['date'] >= detail_start and r['product_supplied_bpd'] is None]
        warnings = ['Official demand, imports and regional detail unavailable for '+', '.join(missing)+'; no values estimated.'] if missing else []
        build(*originals,warnings,observations=rows,supplemental_sources=sources)
        export(PRIVATE/'site-export')
        atomic_json(PRIVATE/'state/eia-backfill.json',{'status':'validated','reports':plans,'corrections':corrections,'missing_weeks':missing,'drive_written':False})
        print(json.dumps({'reports':plans,'missing_weeks':missing}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdfs',nargs='+',type=Path)
    parser.add_argument('--correct-2026-11-06-midwest',action='store_true',
                        help='Apply user-approved Midwest correction 25.6M to 24.6M and recompute other regions')
    args = parser.parse_args()
    run(args.pdfs,args.correct_2026_11_06_midwest)
