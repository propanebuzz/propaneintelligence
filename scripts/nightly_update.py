"""Single nightly entrypoint; defaults to read-only until deployment is enabled."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.storage import PRIVATE, atomic_json, run_lock


def steps(apply, config):
    if apply and not config.get('live_updates_enabled'):
        raise RuntimeError('Unattended writes have not passed deployment checks')
    result = ['run_pipeline.py', 'stage_daily_update.py']
    if apply:
        result += ['apply_daily_update.py', 'run_pipeline.py', 'publish_site.py']
    return result


def run(apply=False):
    config = json.loads((ROOT / 'config/sources.json').read_text())
    sequence = steps(apply, config)
    with run_lock(PRIVATE / 'state/nightly.lock'):
        report = {'started_at': datetime.now(timezone.utc).isoformat(),
                  'mode': 'apply_daily' if apply else 'read_only', 'steps': [],
                  'status': 'running', 'weekly_updates_enabled': False}
        path = PRIVATE / 'state/nightly-run.json'
        atomic_json(path, report)
        for script in sequence:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts' / script)],
                                    cwd=ROOT, capture_output=True, text=True)
            report['steps'].append({'script': script, 'exit_code': result.returncode})
            if result.returncode:
                report.update(status='failed', failed_step=script,
                              finished_at=datetime.now(timezone.utc).isoformat())
                atomic_json(path, report)
                raise RuntimeError('Nightly run stopped at ' + script + '; review private state before retrying')
        report.update(status='verified', finished_at=datetime.now(timezone.utc).isoformat())
        atomic_json(path, report)
        print('Nightly workflow verified:', report['mode'], '; daily data and site publication checked.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        run(args.apply)
    except RuntimeError as error:
        print(str(error))
        raise SystemExit(1)
