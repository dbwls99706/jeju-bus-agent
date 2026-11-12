import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import data_source as ds


class SourceTests(unittest.TestCase):
    def test_default_is_real(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(ds.get_mode(), 'real')
            self.assertEqual(ds.source_path().name, 'bus.csv.gz')

    def test_explicit_real(self):
        with patch.dict(os.environ, {'DATA_MODE': 'real'}):
            self.assertEqual(ds.source_path().name, 'bus.csv.gz')
            self.assertEqual(ds.expected_sha256(), ds.REAL_SHA256)

    def test_bad_mode_fails(self):
        for value in ('', 'REAL', ' real ', 'unknown', '../real'):
            with self.subTest(value=value), patch.dict(os.environ, {'DATA_MODE': value}):
                with self.assertRaises(ds.DataSourceError):
                    ds.source_path()

    def test_synthetic_bytes_and_metadata(self):
        raw, meta = ds.read_source('synthetic')
        self.assertTrue(raw)
        self.assertEqual(meta['sha256'], ds.SYNTHETIC_SHA256)
        self.assertEqual(meta['data_kind'], 'synthetic')

    def test_real_missing_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'data'
            data.mkdir()
            (data / 'synthetic.csv').write_bytes(ds.source_path('synthetic').read_bytes())
            with self.assertRaisesRegex(ds.DataSourceError, 'fallback is disabled'):
                ds.read_source('real', base_dir=folder)

    def test_real_rejects_synthetic(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'data'
            data.mkdir()
            (data / 'bus.csv.gz').write_bytes(__import__('gzip').compress(ds.source_path('synthetic').read_bytes()))
            with self.assertRaisesRegex(ds.DataSourceError, 'checksum'):
                ds.read_source('real', base_dir=folder)

    def test_tampering_rejected(self):
        raw, _ = ds.read_source('synthetic')
        with self.assertRaises(ds.DataSourceError):
            ds.verify_bytes(raw + b'\n', 'synthetic')
        with self.assertRaises(ds.DataSourceError):
            ds.verify_bytes(b'', 'real')
        with self.assertRaises(TypeError):
            ds.verify_bytes('not bytes', 'real')

    def test_metadata_caveat_no_ai_claim(self):
        meta = ds.get_metadata('real')
        self.assertIn('edmgr.kr', meta['metadata_url'])
        self.assertIn('대조하지 못했습니다', meta['license_caveat'])
        self.assertNotIn('ai_enabled', meta)
        self.assertNotIn('path', meta)
        meta['data_kind'] = 'changed'
        self.assertEqual(ds.get_metadata('real')['data_kind'], 'real')

    def test_verify_file_missing_hides_path(self):
        with self.assertRaises(ds.DataSourceError) as caught:
            ds.verify_file('/nonexistent/private-folder/bus.csv', 'real')
        self.assertNotIn('private-folder', str(caught.exception))

    @unittest.skipUnless(os.environ.get('TEST_REAL_CSV'), 'external original-file QA not configured')
    def test_external_original_without_copying(self):
        self.assertEqual(ds.verify_file(os.environ['TEST_REAL_CSV'], 'real'), ds.REAL_SHA256)


if __name__ == '__main__':
    unittest.main()
