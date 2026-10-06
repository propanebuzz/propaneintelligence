"""Same-ID binary update with version guard, backup journal and exact readback.

Never retry an uncertain upload automatically. Preserve its journal for recovery.
"""
from datetime import datetime,timezone
import hashlib
from urllib.parse import urlencode,quote
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from .storage import PRIVATE,atomic_json,archive_bytes
from .package_edit import verify_package


def digest(data):return hashlib.sha256(data).hexdigest()


def apply_daily(google,file_id,source,candidate,expected_version,allowed_id,*,changed_part='xl/worksheets/sheet1.xml',suffix='.xlsm',journal_name='daily-write-journal.json'):
    if file_id!=allowed_id:raise ValueError('Drive file is not the configured workbook')
    if source==candidate:return {'action':'no_change','drive_changed':False}
    verify_package(source,candidate,changed_part)
    before=google.file_metadata(file_id)
    if before['version']!=expected_version:raise RuntimeError('Drive version changed; candidate discarded')
    metadata=google.get('https://www.googleapis.com/drive/v2/files/'+quote(file_id,safe='')+'?'+urlencode({'fields':'id,etag,mimeType,version'}))
    if metadata.get('version')!=expected_version or not metadata.get('etag'):raise RuntimeError('Drive concurrency metadata changed or unavailable')
    if metadata['mimeType'].startswith('application/vnd.google-apps.'):raise RuntimeError('Refusing to convert a native Google document')
    current=google.download_file(file_id)
    if digest(current)!=digest(source):raise RuntimeError('Drive content changed; candidate discarded')
    backup,source_hash=archive_bytes(PRIVATE/'archives/pre-write',source,suffix)
    journal={'at':datetime.now(timezone.utc).isoformat(),'file_id':file_id,'source_sha256':source_hash,'candidate_sha256':digest(candidate),'source_version':expected_version,'backup':str(backup),'status':'upload_pending'}
    atomic_json(PRIVATE/'state'/journal_name,journal)
    url='https://www.googleapis.com/upload/drive/v2/files/'+quote(file_id,safe='')+'?uploadType=media'
    request=Request(url,data=candidate,method='PUT',headers={'Authorization':'Bearer '+google.access,'Content-Type':metadata['mimeType'],'If-Match':metadata['etag']})
    try:
        with urlopen(request,timeout=60) as response:response.read()
    except HTTPError as error:
        journal['status']='conflict_rejected' if error.code==412 else 'upload_failed_or_uncertain'
        atomic_json(PRIVATE/'state'/journal_name,journal)
        raise RuntimeError('Drive upload stopped (HTTP '+str(error.code)+'); review private journal before retry') from None
    except (URLError,TimeoutError):
        journal['status']='upload_uncertain';atomic_json(PRIVATE/'state'/journal_name,journal)
        raise RuntimeError('Upload outcome uncertain; review private journal before retry') from None
    readback=google.download_file(file_id)
    if digest(readback)!=digest(candidate):
        journal['status']='readback_mismatch';atomic_json(PRIVATE/'state'/journal_name,journal)
        raise RuntimeError('Drive readback differs; backup retained, no automatic overwrite attempted')
    after=google.file_metadata(file_id)
    if after['id']!=file_id or after['mimeType']!=before['mimeType'] or after['name']!=before['name']:raise RuntimeError('Drive identity/format changed after upload')
    journal.update(status='verified',saved_version=after['version']);atomic_json(PRIVATE/'state'/journal_name,journal)
    return {'action':'updated','drive_changed':True,'version':after['version']}
