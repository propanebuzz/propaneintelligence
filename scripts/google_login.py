"""One-time read-only desktop OAuth login; never prints credentials."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen

PRIVATE = Path.home() / 'Documents/Codex/propane-private/credentials'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/drive.readonly']


def main():
    client = json.loads((PRIVATE / 'google-client.json').read_text())['installed']
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    result = {}

    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            valid = secrets.compare_digest(query.get('state', [''])[0], state)
            if valid:
                result.update(query)
            self.send_response(200 if valid else 400)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Return to Terminal for the verification result.' if valid else b'Invalid login callback.')

    with HTTPServer(('127.0.0.1', 0), Callback) as server:
        server.timeout = 1
        redirect = f'http://127.0.0.1:{server.server_port}'
        url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
            'client_id': client['client_id'], 'redirect_uri': redirect,
            'response_type': 'code', 'scope': ' '.join(SCOPES),
            'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256',
            'access_type': 'offline', 'prompt': 'consent', 'login_hint': 'propanebuzz@gmail.com'})
        subprocess.run(['open', '-a', 'Firefox', url], check=True)
        print('In Firefox, authorize propanebuzz@gmail.com for read-only Gmail and Drive access.', flush=True)
        deadline = time.monotonic() + 600
        while not result and time.monotonic() < deadline:
            server.handle_request()
    if 'code' not in result:
        raise RuntimeError('Login was denied or timed out; no credentials saved.')
    body = urlencode({'client_id': client['client_id'], 'client_secret': client['client_secret'],
                      'code': result['code'][0], 'code_verifier': verifier,
                      'redirect_uri': redirect, 'grant_type': 'authorization_code'}).encode()
    with urlopen(Request('https://oauth2.googleapis.com/token', data=body), timeout=30) as response:
        token = json.load(response)
    if not set(SCOPES).issubset(set(token.get('scope', '').split())):
        raise RuntimeError('Both read-only permissions are required; no credentials saved.')
    headers = {'Authorization': 'Bearer ' + token['access_token']}
    with urlopen(Request('https://gmail.googleapis.com/gmail/v1/users/me/profile', headers=headers), timeout=30) as response:
        profile = json.load(response)
    if profile.get('emailAddress', '').lower() != 'propanebuzz@gmail.com':
        raise RuntimeError('Wrong Gmail account; no credentials saved. Retry with propanebuzz@gmail.com.')
    if not token.get('refresh_token'):
        raise RuntimeError('Offline access was not issued; no credentials saved.')
    token['obtained_at'] = time.time()
    os.umask(0o077)
    temporary = PRIVATE / 'google-token.tmp'
    temporary.write_text(json.dumps(token))
    os.chmod(temporary, 0o600)
    temporary.replace(PRIVATE / 'google-token.json')
    print('Verified Gmail account: propanebuzz@gmail.com. Login saved privately. No workbook changes made.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Avoid HTTP response bodies, callback codes or tokens in diagnostics.
        print('Login failed:', str(error) if isinstance(error, RuntimeError) else type(error).__name__)
        raise SystemExit(1)
