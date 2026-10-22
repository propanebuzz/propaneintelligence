"""Build a dashboard from user-supplied legacy workbooks and a complete EIA PDF.

Read-only with respect to workbooks and Drive. Previously validated supplemental
fields remain attached to their original dates; missing observations stay null.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import date, datetime, timedelta
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import pdfplumber
from openpyxl import load_workbook
from pipeline.eia import parse_pages
from pipeline.storage import PRIVATE, archive_bytes, atomic_json, run_lock
from pipeline.workbooks import FIELDS, daily_prices
from scripts.build_dashboard import build
from scripts.export_site import export

LEGACY = {4:'inv', 5:'midwest', 6:'gulf', 7:'other', 8:'ready',
          10:'build', 11:'exports', 12:'production'}
PDF_FIELDS = {'inv_bbl':('inv',1e6), 'midwest_bbl':('midwest',1e6),
              'gulf_bbl':('gulf',1e6), 'ready_bbl':('ready',1e6),
              'build_bbl':('build',1e6), 'exports_bpd':('exports',1e6),
              'production_bpd':('production',1e6)}


def merge_weekly(legacy, previous, record):
    known = {r['date']:deepcopy(r) for r in previous}
    seen = set()
    for number, values in legacy:
        day = values[0]
        if not isinstance(day, datetime): raise ValueError('Invalid weekly date')
        iso = day.date().isoformat()
        if iso in seen or day.date() > date.today(): raise ValueError('Duplicate/future weekly date')
        seen.add(iso)
        year = day.year if day.month >= 4 else day.year - 1
        first = date(year,4,1)
        first += timedelta(days=(4-first.weekday())%7)
        row = known.get(iso, dict.fromkeys(FIELDS.values()))
        row.update(date=iso, season=year, week=round((day.date()-first).days/7)+1,
                   row=number, cached_week=values[3], cached_yoy=None)
        for index, key in LEGACY.items():
            value = values[index]
            if value is None: continue
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError('Invalid weekly numeric input')
            if key != 'build' and value < 0: raise ValueError('Negative stock/flow')
            value /= 1e6
            if iso in known and row.get(key) is not None and not math.isclose(value,row[key],abs_tol=1e-6):
                raise ValueError(f'Historical revision requires review: {iso} {key}')
            row[key] = value
        # Legacy J is propylene; N is residual demand. Neither is official demand.
        known[iso] = row
    if record['date'] not in known: raise ValueError('PDF week absent from supplied workbook')
    if record['date'] != max(known): raise ValueError('PDF is not the latest supplied week')
    latest = known[record['date']]
    for source, value in record.items():
        if source == 'date': continue
        target, divisor = PDF_FIELDS.get(source,(source,1))
        if target not in FIELDS.values(): continue
        incoming = value/divisor
        if target in LEGACY.values() and latest.get(target) is not None:
            if not math.isclose(incoming,latest[target],abs_tol=0.050001):
                raise ValueError('PDF/workbook conflict: '+target)
        latest[target] = incoming
    totals = defaultdict(float)
    rows = sorted(known.values(),key=lambda r:r['date'])
    for row in rows:
        if row['build'] is not None: totals[row['season']] += row['build']
        row['cumulative'] = totals[row['season']]
    return rows


def run(weekly, daily, pdf):
    with run_lock(PRIVATE/'state/nightly.lock'):
        previous = json.loads((PRIVATE/'state/dashboard-last-good.json').read_text())
        incoming = daily_prices(daily)
        old = {r['date']:r for r in previous['daily']}
        new = {r['date']:r for r in incoming}
        if not old.keys() <= new.keys(): raise ValueError('Daily file omits saved history')
        for day, row in old.items():
            if any(not math.isclose(row[k],new[day][k],abs_tol=1e-9) for k in ('cwy','tet','wti')):
                raise ValueError('Daily historical revision requires review: '+day)
        with pdfplumber.open(pdf) as document:
            record = parse_pages([p.extract_text() or '' for p in document.pages])
        workbook = load_workbook(weekly,read_only=True,data_only=True)
        try:
            values = list(workbook['MasterData'].values)
            if values[0][9] != 'Propylene (bbl)' or len(values[0]) != 18:
                raise ValueError('Unexpected legacy weekly layout')
            rows = merge_weekly([(n,r) for n,r in enumerate(values[1:],2) if r[0] is not None],
                                previous['archive'],record)
        finally: workbook.close()
        archived = []
        for path in (weekly,daily,pdf):
            saved,digest = archive_bytes(PRIVATE/'archives/local-imports',path.read_bytes(),path.suffix)
            archived.append({'sha256':digest,'archive':str(saved)})
        atomic_json(PRIVATE/'archives/pre-import'/('snapshot-'+previous['meta']['built'].replace(':','-')+'.json'),previous)
        missing = [r['date'] for r in rows if r['date'] > previous['archive'][-1]['date']
                   and r['product_supplied_bpd'] is None]
        warnings = ['Official demand, imports and regional detail unavailable for '+', '.join(missing)+'; no values estimated.'] if missing else []
        data = build(weekly,daily,warnings,observations=rows,
                     supplemental_sources=[{'file':'EIA supplied PDF','sha256':archived[2]['sha256']}])
        export(PRIVATE/'site-export')
        atomic_json(PRIVATE/'state/local-import.json',{'status':'validated','sources':archived,
                    'daily_date':incoming[-1]['date'],'weekly_date':rows[-1]['date'],
                    'daily_count':len(incoming),'weekly_count':len(rows),'drive_written':False})
        return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('weekly',type=Path)
    parser.add_argument('daily',type=Path)
    parser.add_argument('pdf',type=Path)
    args = parser.parse_args()
    run(args.weekly,args.daily,args.pdf)
