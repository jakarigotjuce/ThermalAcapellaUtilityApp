import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import clean_title, youtube_url, Settings, export_unique, Runner, Cancelled, PROCESSING_NAME


class CoreTests(unittest.TestCase):
    def test_titles_preserve_song_details(self):
        self.assertEqual(clean_title('Artist - Song (Remix) (Official Music Video)'), 'Artist - Song (Remix)')
        self.assertEqual(clean_title('Song [OFFICIAL VIDEO]'), 'Song')
        self.assertEqual(clean_title('CON'), '_CON')
        self.assertNotIn('/', clean_title('../bad/name:*'))

    def test_youtube_links(self):
        expected = 'https://www.youtube.com/watch?v=abcdefghijk'
        self.assertEqual(youtube_url('https://youtu.be/abcdefghijk?t=3'), expected)
        self.assertEqual(youtube_url('https://www.youtube.com/shorts/abcdefghijk'), expected)
        for bad in ['file:///etc/passwd', 'https://youtube.com.evil.org/watch?v=abcdefghijk', '--help', 'https://youtube.com/playlist?list=123']:
            with self.assertRaises(ValueError): youtube_url(bad)

    def test_settings_persist_and_recover_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            Settings(path).save('C:/Music/Acapellas')
            self.assertEqual(Settings(path).load()['output'], 'C:/Music/Acapellas')
            path.write_text('not json')
            self.assertIn('output', Settings(path).load())

    def test_no_overwrite_and_failed_copy_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.mp3'; source.write_bytes(b'audio')
            output = Path(directory) / 'out'
            first = export_unique(source, output, 'Song', 'F minor', 94)
            second = export_unique(source, output, 'Song', 'F minor', 94)
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_bytes(), b'audio')
            self.assertEqual(second.read_bytes(), b'audio')
            with self.assertRaises(FileNotFoundError):
                export_unique(Path(directory)/'missing', output, 'Broken', 'C', 100)
            self.assertFalse(list(output.glob('Broken*')))

    def test_cancellation_terminates_subprocess(self):
        runner = Runner()
        timer = threading.Timer(.2, runner.cancelled.set)
        timer.start()
        try:
            with self.assertRaises(Cancelled):
                runner.run([sys.executable, '-c', 'import time; time.sleep(30)'])
        finally:
            timer.cancel()

    def test_pipeline_exports_exact_job_vocals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unrelated = root / PROCESSING_NAME / 'unrelated'; unrelated.mkdir(parents=True)
            (unrelated/'source.mp3').write_bytes(b'wrong audio')
            runner = Runner()
            def fake(command, log=None):
                job = Path(log).parent if log else root
                if 'yt_dlp' in command:
                    (job/'source.mp3').write_bytes(b'original')
                    (job/'source.info.json').write_text(json.dumps({'title':'Artist - Song (Official Video)'}))
                elif any(str(arg).endswith('analyze.py') for arg in command):
                    return json.dumps({'key':'F minor','bpm':94})
                elif 'demucs' in command:
                    vocals = job/'stems'/'htdemucs'/'source'/'vocals.wav'
                    vocals.parent.mkdir(parents=True); vocals.write_bytes(b'isolated')
                elif command[0] == 'ffmpeg':
                    self.assertEqual(Path(command[command.index('-i')+1]).read_bytes(), b'isolated')
                    Path(command[-1]).write_bytes(b'encoded vocals')
                return ''
            with patch.object(runner, 'run', side_effect=fake), patch('core.shutil.which', return_value='/tool'):
                result = runner.process('https://youtu.be/abcdefghijk', root/'output', app_dir=root)
            self.assertEqual(result.name, 'Artist - Song (F minor, 94 BPM).mp3')
            self.assertEqual(result.read_bytes(), b'encoded vocals')
            self.assertEqual((unrelated/'source.mp3').read_bytes(), b'wrong audio')

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_real_320k_export(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'tone.mp3'
            Runner().run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','sine=frequency=440:duration=1','-c:a','libmp3lame','-b:a','320k',str(output)])
            value = json.loads(subprocess.check_output(['ffprobe','-v','quiet','-show_streams','-of','json',str(output)]))
            self.assertEqual(value['streams'][0]['codec_name'], 'mp3')
            self.assertEqual(int(value['streams'][0]['bit_rate']), 320000)


if __name__ == '__main__':
    unittest.main()
