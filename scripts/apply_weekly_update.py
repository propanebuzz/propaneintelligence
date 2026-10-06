"""Apply the validated complete EIA sample to the configured weekly workbook."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.google import GoogleReader
from pipeline.drive_update import apply_daily
from pipeline.storage import PRIVATE,run_lock
from scripts.stage_weekly_update import stage
from scripts.stage_daily_update import ROOT

if __name__=='__main__':
    with run_lock(PRIVATE/'state/run.lock'):
        report=json.loads((PRIVATE/'state/latest-run.json').read_text())
        verification=json.loads((PRIVATE/'state/eia-sample-verification.json').read_text())
        if report['failures'] or verification['mismatches']:raise SystemExit('Source discrepancies require review')
        journal=PRIVATE/'state/weekly-write-journal.json'
        if journal.exists() and json.loads(journal.read_text())['status'] not in ('verified','conflict_rejected'):
            raise SystemExit('Unresolved prior weekly upload requires recovery review')
        config=json.loads((ROOT/'config/sources.json').read_text())
        observed=report['drive_sources']['weekly_analytics']
        source=PRIVATE/'archives/workbooks'/(observed['sha256']+'.xlsx')
        candidate,plan=stage(source,verification['record'],PRIVATE/'update-staging/weekly')
        result=apply_daily(GoogleReader(),observed['id'],source.read_bytes(),candidate.read_bytes(),observed['version'],config['drive_files']['weekly_analytics']['id'],changed_part=plan['sheet_part'],suffix='.xlsx',journal_name='weekly-write-journal.json')
        print('Weekly update:',result['action'],'; same ID and package preserved. Scheduling remains disabled.')
