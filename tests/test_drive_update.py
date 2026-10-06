import unittest
from unittest.mock import Mock,patch
from pipeline.drive_update import apply_daily
from test_package_edit import package,BASE

class DriveUpdateTests(unittest.TestCase):
    def test_duplicate_never_uploads(self):
        google=Mock()
        self.assertFalse(apply_daily(google,'allowed',b'same',b'same','1','allowed')['drive_changed'])
        google.file_metadata.assert_not_called()
    def test_other_id_rejected(self):
        with self.assertRaises(ValueError):apply_daily(Mock(),'other',b'a',b'b','1','allowed')
    def test_changed_version_never_uploads(self):
        google=Mock();google.file_metadata.return_value={'version':'2'}
        with patch('pipeline.drive_update.urlopen') as upload:
            with self.assertRaises(RuntimeError):apply_daily(google,'allowed',package(BASE),package(BASE.replace('46000','46001')),'1','allowed')
            upload.assert_not_called()
    def test_missing_etag_never_uploads(self):
        google=Mock();google.file_metadata.return_value={'version':'1'};google.get.return_value={'version':'1'}
        with patch('pipeline.drive_update.urlopen') as upload:
            with self.assertRaises(RuntimeError):apply_daily(google,'allowed',package(BASE),package(BASE.replace('46000','46001')),'1','allowed')
            upload.assert_not_called()
    def test_success_requires_exact_readback(self):
        source=package(BASE);candidate=package(BASE.replace('46000','46001'))
        google=Mock();google.access='synthetic'
        google.file_metadata.side_effect=[{'id':'allowed','version':'1','name':'Daily.xlsm','mimeType':'binary'}, {'id':'allowed','version':'2','name':'Daily.xlsm','mimeType':'binary'}]
        google.get.return_value={'version':'1','etag':'"guard"','mimeType':'binary'}
        google.download_file.side_effect=[source,candidate]
        with patch('pipeline.drive_update.urlopen') as upload,patch('pipeline.drive_update.archive_bytes',return_value=('private-backup','hash')),patch('pipeline.drive_update.atomic_json') as journal:
            response=Mock();upload.return_value.__enter__.return_value=response
            result=apply_daily(google,'allowed',source,candidate,'1','allowed')
            self.assertTrue(result['drive_changed'])
            request=upload.call_args.args[0]
            self.assertEqual(request.get_header('If-match'),'"guard"')
            self.assertEqual(request.method,'PUT')
            self.assertEqual(journal.call_args.args[1]['status'],'verified')
    def test_readback_mismatch_stops_without_second_upload(self):
        source=package(BASE);candidate=package(BASE.replace('46000','46001'))
        google=Mock();google.access='synthetic'
        google.file_metadata.return_value={'version':'1'}
        google.get.return_value={'version':'1','etag':'"guard"','mimeType':'binary'}
        google.download_file.side_effect=[source,b'different']
        with patch('pipeline.drive_update.urlopen') as upload,patch('pipeline.drive_update.archive_bytes',return_value=('private-backup','hash')),patch('pipeline.drive_update.atomic_json') as journal:
            with self.assertRaises(RuntimeError):apply_daily(google,'allowed',source,candidate,'1','allowed')
            self.assertEqual(upload.call_count,1)
            self.assertEqual(journal.call_args.args[1]['status'],'readback_mismatch')
