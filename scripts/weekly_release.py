"""EIA release-day update using the official holiday calendar and guarded same-ID writes."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen
from zoneinfo import ZoneInfo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.google import GoogleReader
from pipeline.drive_update import apply_daily
from pipeline.storage import PRIVATE, atomic_json, run_lock
from scripts.stage_weekly_update import stage
from scripts.stage_daily_update import ROOT
from scripts.fetch_eia import fetch
from scripts.run_pipeline import run as refresh

CALENDAR = 'https://www.eia.gov/petroleum/supply/weekly/includes/wpsr-calendar.json'


def due_release(calendar, now):
    local = now.astimezone(ZoneInfo('America/New_York'))
    matches = [r for r in calendar if r['release_date'] == local.date().isoformat()]
    if not matches:
        if not calendar or local.date().isoformat() > max(r['release_date'] for r in calendar):
            raise RuntimeError('EIA calendar coverage ended; refresh schedule before continuing')
        return None
    if len(matches) != 1: raise RuntimeError('Ambiguous EIA release calendar')
    row = matches[0]
    deadline = datetime.fromisoformat(row['release_date'] + 'T' + row['release_time']).replace(tzinfo=ZoneInfo('America/New_York')) + timedelta(minutes=1)
    return row if local >= deadline else None


def run(apply=False, release_day_only=True):
    config = json.loads((ROOT / 'config/sources.json').read_text())
    if apply and not config.get('live_updates_enabled'): raise RuntimeError('Live deployment is disabled')
    with run_lock(PRIVATE / 'state/nightly.lock'):
        expected = None
        if release_day_only:
            with urlopen(CALENDAR, timeout=30) as response: calendar = json.load(response)
            expected = due_release(calendar, datetime.now(timezone.utc))
            if not expected:
                print('No EIA release due now; no changes.'); return
        report = {'started_at': datetime.now(timezone.utc).isoformat(), 'status': 'running',
                  'mode': 'apply' if apply else 'read_only', 'expected_release': expected}
        path = PRIVATE / 'state/weekly-release-run.json'
        atomic_json(path, report)
        try:
            refresh(check_opis=False)
            verification = None
            for attempt in range(3):
                verification = fetch()
                if not expected or verification['record']['date'] == expected['data_for_date']: break
                if attempt < 2: time.sleep(20)
            if expected and verification['record']['date'] != expected['data_for_date']:
                report.update(status='release_pending', observed_week=verification['record']['date'])
                atomic_json(path, report)
                raise RuntimeError('EIA has not published the expected complete week; prior dashboard retained')
            if verification['action'] == 'stale_source': raise RuntimeError('EIA source is older than the saved workbook')
            if verification['action'] == 'insert_preview':
                observed = verification['workbook_source']
                source = PRIVATE / 'archives/workbooks' / (observed['sha256'] + '.xlsx')
                candidate, plan = stage(source, verification['record'], PRIVATE / 'update-staging/weekly')
                if apply:
                    with run_lock(PRIVATE / 'state/run.lock'):
                        journal = PRIVATE / 'state/weekly-write-journal.json'
                        if journal.exists() and json.loads(journal.read_text())['status'] not in ('verified', 'conflict_rejected'):
                            raise RuntimeError('Unresolved weekly upload journal; manual recovery required')
                        result = apply_daily(GoogleReader(), observed['id'], source.read_bytes(), candidate.read_bytes(), observed['version'],
                                             config['drive_files']['weekly_analytics']['id'], changed_part=plan['sheet_part'],
                                             suffix='.xlsx', journal_name='weekly-write-journal.json')
                        report['drive_result'] = result
                        atomic_json(PRIVATE / 'state/eia-applied-release.json', verification)
                    refresh(check_opis=False)
            if apply:
                subprocess.run([sys.executable, str(ROOT / 'scripts/publish_site.py')], cwd=ROOT, check=True)
            report.update(status='verified', action=verification['action'], finished_at=datetime.now(timezone.utc).isoformat())
            atomic_json(path, report)
            print('Weekly release workflow verified:', verification['action'])
        except Exception as error:
            report.update(status='failed' if report['status'] != 'release_pending' else 'release_pending',
                          finished_at=datetime.now(timezone.utc).isoformat(),
                          reason=str(error) if isinstance(error, (RuntimeError, ValueError)) else type(error).__name__)
            atomic_json(path, report)
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--check-current', action='store_true', help='Validate current files even outside the release window')
    args = parser.parse_args()
    try: run(args.apply, not args.check_current)
    except Exception as error:
        print('Weekly update stopped:', str(error) if isinstance(error, (RuntimeError, ValueError)) else type(error).__name__)
        raise SystemExit(1)
