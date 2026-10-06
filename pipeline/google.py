"""Read-only Google API client with bounded retries and private token storage."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from .storage import PRIVATE


class GoogleReader:
    def __init__(self):
        folder = PRIVATE / 'credentials'
        client = json.loads((folder / 'google-client.json').read_text())['installed']
        token = json.loads((folder / 'google-token.json').read_text())
        body = urlencode({'client_id': client['client_id'], 'client_secret': client['client_secret'],
                          'refresh_token': token['refresh_token'], 'grant_type': 'refresh_token'}).encode()
        response = self._request('https://oauth2.googleapis.com/token', data=body)
        self.access = json.loads(response)['access_token']
        profile = self.get('https://gmail.googleapis.com/gmail/v1/users/me/profile')
        if profile.get('emailAddress', '').lower() != 'propanebuzz@gmail.com':
            raise RuntimeError('Wrong Gmail identity; stopped')

    def _request(self, url, data=None, headers=None):
        for attempt in range(4):
            try:
                with urlopen(Request(url, data=data, headers=headers or {}), timeout=60) as response:
                    return response.read()
            except HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                    raise RuntimeError(f'Google request failed (HTTP {error.code}); reauthorization may be required for 401/403') from None
            except (URLError, TimeoutError):
                if attempt == 3: raise RuntimeError('Google network request failed after four attempts') from None
            time.sleep(2 ** attempt)

    def get(self, url, binary=False):
        data = self._request(url, headers={'Authorization': 'Bearer ' + self.access})
        return data if binary else json.loads(data)

    def file_metadata(self, file_id):
        return self.get('https://www.googleapis.com/drive/v3/files/' + quote(file_id, safe='') + '?' +
                        urlencode({'fields': 'id,name,mimeType,size,modifiedTime,version,capabilities(canEdit)'}))

    def download_file(self, file_id):
        return self.get('https://www.googleapis.com/drive/v3/files/' + quote(file_id, safe='') + '?alt=media', binary=True)

    def opis_messages(self, query, limit=100):
        url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages'
        messages, cursor = [], None
        while len(messages) < limit:
            params = {'q': query, 'maxResults': min(limit - len(messages), 100)}
            if cursor: params['pageToken'] = cursor
            page = self.get(url + '?' + urlencode(params))
            messages.extend(page.get('messages', []))
            cursor = page.get('nextPageToken')
            if not cursor: break
        if cursor: raise RuntimeError('OPIS catch-up message limit reached; review mailbox coverage')
        return [self.get(url + '/' + item['id'] + '?format=full') for item in messages]
