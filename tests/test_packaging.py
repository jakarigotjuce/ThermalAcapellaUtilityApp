import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import core


class PackagingTests(unittest.TestCase):
    def test_python_fallback_dispatch(self):
        with patch.object(core, 'FROZEN', False):
            self.assertEqual(core.worker_command('yt-dlp', '--version')[:3],
                             [core.sys.executable, '-m', 'yt_dlp'])
            self.assertEqual(core.worker_command('demucs', '--help')[:3],
                             [core.sys.executable, '-m', 'demucs'])
            self.assertTrue(core.worker_command('analyze', 'audio.mp3')[1].endswith('analyze.py'))

    def test_frozen_worker_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / 'AcapellaDownloader.exe'
            worker = Path(d) / 'AcapellaWorker.exe'
            worker.touch()
            with patch.object(core, 'FROZEN', True), patch.object(core.sys, 'executable', str(exe)):
                self.assertEqual(core.worker_command('yt-dlp', '--version'), [str(worker), 'yt-dlp', '--version'])
            worker.unlink()
            with patch.object(core, 'FROZEN', True), patch.object(core.sys, 'executable', str(exe)):
                with self.assertRaisesRegex(RuntimeError, 'AcapellaWorker.exe is missing'):
                    core.worker_command('yt-dlp')

    def test_bundled_tools_path(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(core, 'FROZEN', True), patch.object(core, 'BUNDLED_TOOLS', Path(d)):
                with patch.dict(os.environ, {'PATH': 'other'}, clear=False):
                    core.configure_runtime_tools()
                    self.assertEqual(os.environ['PATH'].split(os.pathsep)[0], d)
                    core.configure_runtime_tools()
                    self.assertEqual(os.environ['PATH'].split(os.pathsep).count(d), 1)


if __name__ == '__main__':
    unittest.main()
