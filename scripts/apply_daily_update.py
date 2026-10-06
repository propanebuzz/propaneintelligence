"""Apply a reviewed OPIS plan to the existing daily workbook; no scheduler."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.google import GoogleReader
from pipeline.drive_update import apply_daily
from pipeline.storage import PRIVATE,run_lock
from stage_daily_update import stage,ROOT

if __name__=='__main__':
    with run_lock(PRIVATE/'state/run.lock'):
        report=json.loads((PRIVATE/'state/latest-run.json').read_text())
        if report['failures']:raise SystemExit('Extraction failures require review; no upload')
        journal=PRIVATE/'state/daily-write-journal.json'
        if journal.exists() and json.loads(journal.read_text())['status'] not in ('verified','conflict_rejected'):
            raise SystemExit('Unresolved prior upload journal requires recovery review')
        config=json.loads((ROOT/'config/sources.json').read_text())
        observed=report['drive_sources']['daily_prices']
        source=PRIVATE/'archives/workbooks'/(observed['sha256']+'.xlsm')
        candidate,plan=stage(source,[p['record'] for p in report['plans']],PRIVATE/'update-staging/daily')
        result=apply_daily(GoogleReader(),observed['id'],source.read_bytes(),candidate.read_bytes(),observed['version'],config['drive_files']['daily_prices']['id'])
        print('Daily update:',result['action'],'; workbook ID and format preserved. Scheduling remains disabled.')
