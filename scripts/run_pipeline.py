"""Read-only catch-up run. Archives sources, checks reports, builds private preview."""
from datetime import date,datetime,timezone
from zoneinfo import ZoneInfo
import base64
import io
import json
from pathlib import Path
import sys
import time
from urllib.parse import quote
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pdfplumber
from pipeline.google import GoogleReader
from pipeline.opis import parse_pages,VERSION
from pipeline.records import classify_upsert
from pipeline.storage import PRIVATE,archive_bytes,atomic_json,run_lock
from pipeline.workbooks import daily_prices
from build_dashboard import build

ROOT=Path(__file__).resolve().parents[1]


def run():
    config=json.loads((ROOT/'config/sources.json').read_text())
    started=datetime.now(timezone.utc).isoformat();plans=[];failures=[]
    with run_lock(PRIVATE/'state/run.lock'):
        google=GoogleReader();inputs={};provenance={}
        for key,item in config['drive_files'].items():
            before=google.file_metadata(item['id'])
            data=google.download_file(item['id'])
            after=google.file_metadata(item['id'])
            if before['version']!=after['version'] or before['modifiedTime']!=after['modifiedTime']:
                raise RuntimeError('Drive workbook changed during download; retry required')
            path,digest=archive_bytes(PRIVATE/'archives/workbooks',data,'.'+item['format'])
            inputs[key]=path;provenance[key]={'id':item['id'],'version':before['version'],'modifiedTime':before['modifiedTime'],'sha256':digest}
        history=daily_prices(inputs['daily_prices'])
        existing=[{'date':r['date'],'conway':r['cwy'],'tet':r['tet'],'wti':r['wti'],'propane_unit':'USD/gal','wti_unit':'USD/bbl'} for r in history]
        messages=google.opis_messages(config['opis_candidate_query']+' newer_than:14d')
        seen=set();candidates={}
        for message in messages:
            pending=[message.get('payload',{})]
            while pending:
                part=pending.pop();pending.extend(part.get('parts',[]))
                filename=part.get('filename','')
                if not filename.lower().endswith('.pdf'):continue
                try:
                    body=part.get('body',{})
                    if body.get('attachmentId'):
                        body=google.get('https://gmail.googleapis.com/gmail/v1/users/me/messages/'+message['id']+'/attachments/'+quote(body['attachmentId'],safe=''))
                    encoded=body.get('data','');data=base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4))
                    if not data.startswith(b'%PDF'):raise ValueError('Invalid PDF attachment')
                    path,digest=archive_bytes(PRIVATE/'archives/opis',data,'.pdf')
                    if digest in seen:continue
                    seen.add(digest)
                    with pdfplumber.open(io.BytesIO(data)) as document:
                        candidate=parse_pages([p.extract_text() or '' for p in document.pages])
                    if candidate and date.fromisoformat(candidate['date'])>datetime.now(ZoneInfo('America/Chicago')).date():raise ValueError('Future report date')
                    plan={'message_id':message['id'],'filename':filename,'email_received_ms':message.get('internalDate'),
                          'source_sha256':digest,'parser_version':VERSION,'record':candidate,'action':classify_upsert(existing,candidate)}
                    if candidate:
                        day=candidate['date']
                        if day in candidates and candidates[day]!=candidate:raise ValueError('Conflicting source revisions for one date')
                        candidates[day]=candidate
                    plans.append(plan)
                except Exception as error:
                    failures.append({'message_id':message['id'],'filename':filename,'reason':str(error) if isinstance(error,(RuntimeError,ValueError)) else type(error).__name__})
        result={'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'mode':'read_only',
                'drive_sources':provenance,'messages_checked':len(messages),'plans':plans,'failures':failures,
                'drive_changed':False,'schedule_enabled':False}
        atomic_json(PRIVATE/'state/latest-run.json',result)
        if failures:
            raise RuntimeError('One or more reports require review; last-good dashboard retained')
        pending_count=sum(p['action'] in ('insert','revision') for p in plans)
        build(inputs['weekly_analytics'],inputs['daily_prices'],[f'{pending_count} OPIS updates await a workbook write; preview uses existing workbook history'] if pending_count else [])
        atomic_json(PRIVATE/'state/last-successful-run.json',result)
        print('Reports checked:',len(plans),'Actions:',', '.join(p['action'] for p in plans) or 'no candidate PDFs')
        print('Drive unchanged; live writes and scheduling disabled.')


if __name__=='__main__':
    try:run()
    except Exception as error:
        atomic_json(PRIVATE/'state/last-failure.json',{'at':datetime.now(timezone.utc).isoformat(),'reason':str(error) if isinstance(error,(RuntimeError,ValueError)) else type(error).__name__})
        print('Pipeline stopped; last-good snapshot retained:',str(error) if isinstance(error,(RuntimeError,ValueError)) else type(error).__name__)
        raise SystemExit(1)
