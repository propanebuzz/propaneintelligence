"""Read-only integration check. Source files and credentials stay outside Git."""
import base64
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

PRIVATE = Path.home() / 'Documents/Codex/propane-private'
ROOT = Path(__file__).resolve().parents[1]


def main():
    os.umask(0o077)
    credential_dir = PRIVATE / 'credentials'
    client = json.loads((credential_dir / 'google-client.json').read_text())['installed']
    token = json.loads((credential_dir / 'google-token.json').read_text())
    # Exercise unattended refresh, without printing tokens or response bodies.
    body = urlencode({'client_id': client['client_id'], 'client_secret': client['client_secret'],
                      'refresh_token': token['refresh_token'], 'grant_type': 'refresh_token'}).encode()
    with urlopen(Request('https://oauth2.googleapis.com/token', data=body), timeout=30) as response:
        refreshed = json.load(response)
    access = refreshed['access_token']

    def get(url, binary=False):
        with urlopen(Request(url, headers={'Authorization': 'Bearer ' + access}), timeout=60) as response:
            return response.read() if binary else json.load(response)

    gmail = 'https://gmail.googleapis.com/gmail/v1/users/me'
    profile = get(gmail + '/profile')
    if profile.get('emailAddress', '').lower() != 'propanebuzz@gmail.com':
        raise RuntimeError('Wrong Gmail account; stopped')
    print('PASS: unattended token refresh and Gmail identity propanebuzz@gmail.com', flush=True)
    config = json.loads((ROOT / 'config/sources.json').read_text())
    archive = PRIVATE / 'access-check'
    archive.mkdir(parents=True, exist_ok=True)
    evidence = {'checked_at': time.time(), 'gmail_account': profile['emailAddress'], 'drive_files': []}
    for source in config['drive_files'].values():
        url = 'https://www.googleapis.com/drive/v3/files/' + quote(source['id'], safe='')
        meta = get(url + '?' + urlencode({'fields': 'id,name,mimeType,size,modifiedTime,version,capabilities(canEdit)'}))
        data = get(url + '?alt=media', binary=True)
        if not data.startswith(b'PK'):
            raise RuntimeError('Expected Office ZIP package; stopped')
        target = archive / (source['id'] + '.' + source['format'])
        target.write_bytes(data)
        meta['sha256'] = hashlib.sha256(data).hexdigest()
        meta['download_bytes'] = len(data)
        evidence['drive_files'].append(meta)
        print('PASS: Drive download', meta['name'], len(data), 'bytes', flush=True)
    messages = get(gmail + '/messages?' + urlencode({'q': config['opis_candidate_query'], 'maxResults': 10})).get('messages', [])
    attachment_saved = False
    for item in messages:
        message = get(gmail + '/messages/' + item['id'] + '?format=full')
        pending = [message.get('payload', {})]
        while pending:
            part = pending.pop()
            pending.extend(part.get('parts', []))
            name = part.get('filename', '')
            if not name.lower().endswith('.pdf'):
                continue
            body = part.get('body', {})
            if body.get('attachmentId'):
                body = get(gmail + '/messages/' + item['id'] + '/attachments/' + quote(body['attachmentId'], safe=''))
            encoded = body.get('data', '')
            data = base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4))
            if not data.startswith(b'%PDF'):
                raise RuntimeError('Invalid PDF attachment; stopped')
            (archive / ('opis-' + item['id'] + '.pdf')).write_bytes(data)
            evidence['opis_attachment'] = {'message_id': item['id'], 'filename': name,
                                          'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
            print('PASS: OPIS PDF downloaded privately:', name, len(data), 'bytes', flush=True)
            attachment_saved = True
            break
        if attachment_saved:
            break
    if not attachment_saved:
        raise RuntimeError('No PDF found among the latest ten OPIS candidate messages')
    (archive / 'verification.json').write_text(json.dumps(evidence, indent=2))
    print('No emails or Drive files changed. PDF price extraction still needs verification.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Check failed:', str(error) if isinstance(error, RuntimeError) else type(error).__name__)
        raise SystemExit(1)
