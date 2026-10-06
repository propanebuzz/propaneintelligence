import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from pipeline.storage import atomic_json,archive_bytes,run_lock
from pipeline.google import GoogleReader


class RecoveryTests(unittest.TestCase):
    def test_failed_serialization_preserves_last_good(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'snapshot.json';atomic_json(path,{'version':1})
            with self.assertRaises(ValueError):atomic_json(path,{'bad':float('nan')})
            self.assertEqual(json.loads(path.read_text()),{'version':1})
            self.assertEqual(len(list(Path(folder).iterdir())),1)

    def test_overlapping_run_rejected_and_lock_released(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'run.lock'
            with run_lock(path):
                with self.assertRaises(RuntimeError):
                    with run_lock(path):pass
            with run_lock(path):pass

    def test_archive_is_content_addressed_and_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p,d=archive_bytes(folder,b'synthetic source','.pdf')
            p2,d2=archive_bytes(folder,b'synthetic source','.pdf')
            self.assertEqual((p,d),(p2,d2));self.assertEqual(len(list(Path(folder).iterdir())),1)
            p.write_bytes(b'corrupt')
            with self.assertRaises(RuntimeError):archive_bytes(folder,b'synthetic source','.pdf')

    def test_transient_google_failures_retry_but_auth_does_not(self):
        reader=GoogleReader.__new__(GoogleReader)
        for status,attempts in [(503,4),(429,4),(403,1),(401,1)]:
            error=HTTPError('https://example.invalid',status,'private response',{},None)
            with patch('pipeline.google.urlopen',side_effect=error) as request,patch('pipeline.google.time.sleep'):
                with self.assertRaises(RuntimeError) as caught:reader._request('https://example.invalid')
                self.assertEqual(request.call_count,attempts)
                self.assertNotIn('private response',str(caught.exception))
