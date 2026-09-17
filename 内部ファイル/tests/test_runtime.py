import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class RuntimeTests(unittest.TestCase):
    def test_data_directory_can_be_overridden_for_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ, YUKI_TRANSLATOR_DATA_DIR=folder)
            output = subprocess.check_output(
                [sys.executable, '-c', 'from runtime import DATA_DIR; print(DATA_DIR)'],
                cwd=Path(__file__).resolve().parents[1], env=env, text=True,
            ).strip()
            self.assertEqual(Path(output), Path(folder).resolve())


if __name__ == '__main__':
    unittest.main()
