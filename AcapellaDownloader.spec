# -*- mode: python ; coding: utf-8 -*-
# Build the GUI and its console worker into ONE portable application folder.
# This lets the GUI remain windowless while child processes return real output.
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve()
TOOLS = ROOT / 'vendor'
required = ['ffmpeg.exe', 'ffprobe.exe', 'deno.exe']
missing = [name for name in required if not (TOOLS / name).is_file()]
if missing:
    raise FileNotFoundError('Missing build tools: ' + ', '.join(missing) + '. Run Build-Windows.ps1.')

app_analysis = Analysis(
    ['app.py'], pathex=[str(ROOT)], binaries=[], datas=[], hiddenimports=[],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
worker_analysis = Analysis(
    ['worker.py'], pathex=[str(ROOT)],
    binaries=[(str(TOOLS / name), 'tools') for name in required],
    datas=collect_data_files('demucs') + collect_data_files('librosa'),
    hiddenimports=collect_submodules('demucs', on_error='ignore')
                 + collect_submodules('yt_dlp.extractor', on_error='ignore'),
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
# Share native libraries and other dependencies rather than bundling Torch twice.
MERGE((app_analysis, 'app', 'AcapellaDownloader'),
      (worker_analysis, 'worker', 'AcapellaWorker'))

app_pyz = PYZ(app_analysis.pure)
app_exe = EXE(
    app_pyz, app_analysis.scripts, app_analysis.dependencies,
    exclude_binaries=True, name='AcapellaDownloader', console=False,
    debug=False, strip=False, upx=False,
)
worker_pyz = PYZ(worker_analysis.pure)
worker_exe = EXE(
    worker_pyz, worker_analysis.scripts, worker_analysis.dependencies,
    exclude_binaries=True, name='AcapellaWorker', console=True,
    debug=False, strip=False, upx=False,
)
coll = COLLECT(
    app_exe, worker_exe,
    app_analysis.binaries, app_analysis.datas,
    worker_analysis.binaries, worker_analysis.datas,
    strip=False, upx=False, name='AcapellaDownloader',
)
