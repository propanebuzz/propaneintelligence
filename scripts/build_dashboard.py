"""Build a private preview from workbook observations, without public export."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.analytics import monthly_prices,reconciliation_flags,summarize
from pipeline.storage import PRIVATE,atomic_json
from pipeline.workbooks import daily_prices,weekly_observations

ROOT=Path(__file__).resolve().parents[1]


def build(weekly_path,daily_path,extra_warnings=None):
    archive=weekly_observations(weekly_path);daily=daily_prices(daily_path)
    latest=archive[-1];year=latest['season']
    weekly=[r for r in archive if r['season']>=year-5]
    summary=summarize(weekly,daily)
    now=datetime.now(timezone.utc).isoformat()
    today=datetime.now(ZoneInfo('America/Chicago')).date()
    warnings=list(extra_warnings or [])
    if (today-date.fromisoformat(latest['date'])).days>10:warnings.append('Weekly EIA data is more than ten calendar days old')
    if (today-date.fromisoformat(daily[-1]['date'])).days>4:warnings.append('Daily prices are more than four calendar days old')
    regions=[{'region':'PADD '+str(i),'now':latest['padd'+str(i)+'_ready_bbl']/1e6 if latest['padd'+str(i)+'_ready_bbl'] is not None else None,'prior':None} for i in range(1,6)]
    sources=[{'file':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for name,path in [('Propane_Analytics.xlsx',weekly_path),('Daily Prices.xlsm',daily_path)]]
    data={'meta':{'built':now,'snapshot':'Private preview','status':'Private preview; live updates disabled. '+('; '.join(warnings) if warnings else ''),'sources':sources,'release_date':None},
          'summary':summary,'weekly':weekly,'archive':archive,'daily':daily,'monthly':monthly_prices(daily),
          'anomalies':reconciliation_flags(archive),'nonfriday':[r['date'] for r in archive if date.fromisoformat(r['date']).weekday()!=4],
          'regional_ready':regions,
          'public_snapshot':{'stale':False,'week':latest['date'],'release':None,'source':'#audit','regional_ready':regions},
          'warnings':warnings}
    # Build completely before atomically replacing last-good state.
    preview=PRIVATE/'dashboard-preview';preview.mkdir(parents=True,exist_ok=True)
    payload='window.PROPANE_SNAPSHOT='+json.dumps(data,allow_nan=False).replace('<','\\u003c')+';\n'
    temp=preview/'snapshot.js.tmp';temp.write_text(payload);temp.replace(preview/'snapshot.js')
    shutil.copyfile(ROOT/'dashboard/index.html',preview/'index.html')
    atomic_json(PRIVATE/'state/dashboard-last-good.json',data)
    print('Private dashboard built:',len(daily),'daily records;',len(archive),'weekly records;',len(data['anomalies']),'stock/build flags')
    print('Source dates:',daily[-1]['date'],latest['date'])
    print('Warnings:', '; '.join(warnings) or 'none')
    return data


if __name__=='__main__':
    folder=PRIVATE/'access-check'
    build(folder/'14XA_BnMC8wf0jgXMqKvB21yEi51fbP9q.xlsx',folder/'1VxyMTDFJj8Wb6Lp04yAxKn93uD4RXBOG.xlsm')
