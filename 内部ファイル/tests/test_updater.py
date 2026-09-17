import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import updater
from updater import UpdateInfo, download_update, find_installer_asset, is_newer, version_tuple


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes):
        super().__init__(data)
        self.headers = {'Content-Length': str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class UpdaterTests(unittest.TestCase):
    def test_semantic_version_is_strict(self):
        self.assertEqual(version_tuple('v6.1.2'), (6, 1, 2))
        self.assertEqual(version_tuple('not-a-version'), (0, 0, 0))
        self.assertTrue(is_newer('6.2.0', '6.1.9'))
        self.assertFalse(is_newer('6.1.0-beta1', '6.0.0'))

    def test_release_asset_must_be_exact_and_from_this_repository(self):
        good = {
            'tag_name': 'v6.2.0',
            'assets': [{
                'name': 'YukiTranslator-Setup-v6.2.0.exe',
                'browser_download_url': 'https://github.com/yuki1221xxx/yuki-Translator/releases/download/v6.2.0/YukiTranslator-Setup-v6.2.0.exe',
                'digest': 'sha256:' + 'a' * 64,
            }],
        }
        info = find_installer_asset(good)
        self.assertEqual(info.version, '6.2.0')
        self.assertEqual(info.sha256, 'a' * 64)
        good['assets'][0]['browser_download_url'] = 'https://example.com/update.exe'
        self.assertIsNone(find_installer_asset(good))

    def test_download_is_verified_before_becoming_executable(self):
        payload = b'installer bytes'
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(updater, 'DATA_DIR', Path(folder)), \
                patch('urllib.request.urlopen', return_value=FakeResponse(payload)):
            info = UpdateInfo('6.2.0', 'https://github.com/example', 'update.exe', hashlib.sha256(payload).hexdigest())
            installed = download_update(info)
            self.assertEqual(installed.read_bytes(), payload)

    def test_bad_checksum_is_deleted(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(updater, 'DATA_DIR', Path(folder)), \
                patch('urllib.request.urlopen', return_value=FakeResponse(b'tampered')):
            info = UpdateInfo('6.2.0', 'https://github.com/example', 'update.exe', '0' * 64)
            with self.assertRaises(ValueError):
                download_update(info)
            self.assertFalse((Path(folder) / 'updates' / 'update.exe.partial').exists())


if __name__ == '__main__':
    unittest.main()
