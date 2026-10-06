"""Export the user-authorized no-login dashboard; never export source files or credentials."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.storage import PRIVATE

ROOT = Path(__file__).resolve().parents[1]
TOP = {'summary', 'weekly', 'archive', 'daily', 'monthly', 'anomalies',
       'nonfriday', 'regional_ready', 'public_snapshot', 'warnings'}


def export(destination):
    original = json.loads((PRIVATE / 'state/dashboard-last-good.json').read_text())
    data = {key: original[key] for key in TOP}
    data['meta'] = {'built': original['meta']['built'], 'snapshot': 'Propane Intelligence',
                    'status': 'Validated snapshot. ' + '; '.join(data['warnings']),
                    'sources': [{'file': 'EIA weekly observations', 'sha256': original['meta']['sources'][0]['sha256']},
                                {'file': 'OPIS-derived daily prices', 'sha256': original['meta']['sources'][1]['sha256']}],
                    'release_date': original['meta'].get('release_date')}
    for key in ('weekly', 'archive', 'daily'):
        data[key] = [{k: v for k, v in row.items() if k not in ('row', 'cached_week', 'cached_yoy')} for row in data[key]]
    text = json.dumps(data, allow_nan=False).replace('<', '\\u003c')
    if any(marker in text for marker in ('refresh_token', 'client_secret', 'access_token', '/Users/', 'gmail.com', '14XA_BnMC8wf', '1VxyMTDFJj8')):
        raise RuntimeError('Private information in site export; stopped')
    destination.mkdir(parents=True, exist_ok=True)
    html = (ROOT / 'dashboard/index.html').read_text().replace('Private snapshot not loaded', 'Dashboard snapshot not loaded')
    html = html.replace('PRIVATE PREVIEW', 'MARKET DASHBOARD')
    html = html.replace('<head>', '<head>\n<meta name="robots" content="noindex,nofollow">')
    (destination / 'index.html').write_text(html)
    temporary = destination / 'snapshot.js.tmp'
    temporary.write_text('window.PROPANE_SNAPSHOT=' + text + ';\n')
    temporary.replace(destination / 'snapshot.js')
    print('No-login site export prepared. Source reports, workbooks and credentials excluded.')


if __name__ == '__main__':
    export(PRIVATE / 'site-export')
