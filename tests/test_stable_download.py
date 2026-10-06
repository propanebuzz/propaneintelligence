import unittest
from unittest.mock import Mock, patch
from pipeline.google import GoogleReader


class StableDownloadTests(unittest.TestCase):
    def client(self, versions):
        client = GoogleReader.__new__(GoogleReader)
        client.file_metadata = Mock(side_effect=[{'version': str(v), 'modifiedTime': str(v)} for v in versions])
        client.download_file = Mock(side_effect=[b'first', b'second', b'third'])
        return client

    @patch('pipeline.google.time.sleep')
    def test_discards_unstable_download(self, sleep):
        client = self.client([1, 2, 2, 2])
        data, metadata = client.stable_download('file')
        self.assertEqual(data, b'second')
        self.assertEqual(metadata['version'], '2')
        self.assertEqual(client.download_file.call_count, 2)

    @patch('pipeline.google.time.sleep')
    def test_continuous_changes_stop_after_three_reads(self, sleep):
        client = self.client([1, 2, 2, 3, 3, 4])
        with self.assertRaisesRegex(RuntimeError, 'kept changing'):
            client.stable_download('file')
        self.assertEqual(client.download_file.call_count, 3)
