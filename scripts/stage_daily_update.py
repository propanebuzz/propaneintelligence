"""Prepare and verify an update on a private copy; never uploads to Drive."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.package_edit import daily_plan,merge_numeric
from pipeline.storage import PRIVATE,atomic_json,archive_bytes
from pipeline.workbooks import daily_prices

ROOT=Path(__file__).resolve().parents[1]
NODE=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'


def stage(source,records,folder,allow_revisions=False):
    folder.mkdir(parents=True,exist_ok=True)
    modules=ROOT/'node_modules'
    bundled=NODE.parent/'node_modules'
    if not modules.exists():
        if not bundled.is_dir():raise RuntimeError('Bundled artifact-tool dependency unavailable')
        modules.symlink_to(bundled,target_is_directory=True)
    plan=daily_plan(source,records,allow_revisions)
    atomic_json(folder/'cell-plan.json',plan)
    original=source.read_bytes()
    if plan['cells']:
        subprocess.run([str(NODE),str(ROOT/'scripts/author_cells.mjs'),str(folder/'cell-plan.json'),str(folder/'authored-cells.xlsx')],check=True,capture_output=True)
        candidate=merge_numeric(original,(folder/'authored-cells.xlsx').read_bytes(),plan)
    else:candidate=original
    output=folder/'candidate.xlsm';output.write_bytes(candidate)
    rows=daily_prices(output)
    for r in records:
        if r is None:continue
        observed=next((x for x in rows if x['date']==r['date']),None)
        if observed is None or (observed['cwy'],observed['tet'],observed['wti'])!=(r['conway'],r['tet'],r['wti']):raise ValueError('Candidate readback differs from source record')
    archive_bytes(PRIVATE/'archives/pre-write',original,source.suffix)
    return output,plan


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-report',type=Path,default=PRIVATE/'state/latest-run.json')
    parser.add_argument('--allow-revisions',action='store_true')
    args=parser.parse_args()
    report=json.loads(args.run_report.read_text())
    if report['failures']:raise SystemExit('Report has extraction failures; review required')
    source=report['drive_sources']['daily_prices']
    path=PRIVATE/'archives/workbooks'/(source['sha256']+'.xlsm')
    output,plan=stage(path,[p['record'] for p in report['plans']],PRIVATE/'update-staging/daily',args.allow_revisions)
    print('Private candidate verified. Actions:',', '.join(p['action'] for p in plan['actions']))
    print('Changed input cells:',len(plan['cells']),'; Drive unchanged.')
