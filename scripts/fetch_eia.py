"""Fetch release-time EIA tables and prepare a dated private validation record."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.eia_csv import parse_tables, VERSION
from pipeline.storage import PRIVATE, archive_bytes, atomic_json, run_lock
from pipeline.workbooks import weekly_observations
from pipeline.weekly_update import CORE


def fetch():
    with run_lock(PRIVATE / 'state/run.lock'):
        files, sources = [], []
        for name in ('table1.csv', 'table9.csv'):
            url = 'https://ir.eia.gov/wpsr/' + name
            with urlopen(url, timeout=30) as response:
                data = response.read(2000001)
            if len(data) > 2000000: raise RuntimeError('EIA source exceeds expected size')
            _, digest = archive_bytes(PRIVATE / 'archives/eia', data, '.csv')
            files.append(data)
            sources.append({'url': url, 'sha256': digest})
        record = parse_tables(*files)
        report = json.loads((PRIVATE / 'state/latest-run.json').read_text())
        source = report['drive_sources']['weekly_analytics']
        workbook = PRIVATE / 'archives/workbooks' / (source['sha256'] + '.xlsx')
        history = weekly_observations(workbook)
        existing = next((r for r in history if r['date'] == record['date']), None)
        mismatches = {}
        if existing:
            applied_path = PRIVATE / 'state/eia-applied-release.json'
            precise = applied_path.exists() and json.loads(applied_path.read_text())['record']['date'] == record['date']
            for key, value in record.items():
                if key == 'date' or key == 'production_4wk_bpd': continue
                field = next((k for k, v in CORE.items() if v == key), key)
                actual = existing.get(field)
                if field in CORE: actual = actual * 1000000 if actual is not None else None
                # Earlier workbook stocks came from the PDF, rounded to 0.1 million barrels.
                tolerance = 50001 if key.endswith('_bbl') and not precise else 0
                if actual is None or abs(actual - value) > tolerance:
                    mismatches[key] = {'workbook': actual, 'csv': value}
        action = 'review' if mismatches else ('duplicate' if existing else 'insert_preview')
        if record['date'] < history[-1]['date']:
            action = 'stale_source'
        result = {'parser': VERSION, 'fetched_at': datetime.now(timezone.utc).isoformat(),
                  'record': record, 'sources': sources, 'mismatches': mismatches,
                  'action': action, 'drive_written': False, 'workbook_source': source}
        atomic_json(PRIVATE / 'state/eia-release-verification.json', result)
        if mismatches: raise RuntimeError('EIA CSV differs beyond source rounding; review required')
        print('EIA release:', record['date'], ';', action, '; all 25 required inputs checked. Drive unchanged.')
        return result


if __name__ == '__main__':
    try: fetch()
    except Exception as error:
        print('EIA retrieval stopped:', str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__)
        raise SystemExit(1)
