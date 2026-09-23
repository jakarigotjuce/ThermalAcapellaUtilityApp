param([string]$Version = '1.0.0')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Version must look like 1.0.0.' }

function Check-Exit([string]$step) {
    if ($LASTEXITCODE -ne 0) { throw "$step failed (exit code $LASTEXITCODE)." }
}

# Build inside a disposable environment. The PC receiving the EXE needs no Python.
$venv = Join-Path $PSScriptRoot '.build-venv'
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    & python -c 'import sys; assert sys.version_info[:2] == (3, 11) and sys.maxsize > 2**32, "Python 3.11 x64 required"'
    Check-Exit 'Python version check'
    & python -m venv $venv
    Check-Exit 'Create build environment'
}
$py = Join-Path $venv 'Scripts\python.exe'
& $py -m pip install --disable-pip-version-check --upgrade pip
Check-Exit 'Update pip'
& $py -m pip install --disable-pip-version-check torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
Check-Exit 'Install CPU PyTorch'
& $py -m pip install --disable-pip-version-check -r requirements.txt 'pyinstaller>=6.15,<7' 'pyinstaller-hooks-contrib>=2025.6'
Check-Exit 'Install application and packager'
& $py -c 'import tkinter, yt_dlp, demucs.separate, librosa, torch, torchaudio; print("Dependency imports OK")'
Check-Exit 'Verify dependencies'
& $py -m unittest discover -s tests -v
Check-Exit 'Run source tests'

$vendor = Join-Path $PSScriptRoot 'vendor'
New-Item -ItemType Directory -Force -Path $vendor | Out-Null
if (-not (Test-Path "$vendor\ffmpeg.exe") -or -not (Test-Path "$vendor\ffprobe.exe")) {
    Write-Host 'Fetching FFmpeg Windows essentials...'
    $download = Join-Path $env:TEMP ('acapella_ffmpeg_' + [guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $download | Out-Null
    try {
        Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile "$download\ffmpeg.zip"
        Expand-Archive -LiteralPath "$download\ffmpeg.zip" -DestinationPath "$download\unpacked"
        $bin = Get-ChildItem -Path "$download\unpacked" -File -Recurse -Filter ffmpeg.exe | Select-Object -First 1
        if (-not $bin) { throw 'Could not find ffmpeg.exe inside the FFmpeg archive.' }
        Copy-Item -LiteralPath $bin.FullName -Destination "$vendor\ffmpeg.exe" -Force
        Copy-Item -LiteralPath (Join-Path $bin.DirectoryName 'ffprobe.exe') -Destination "$vendor\ffprobe.exe" -Force
    } finally { Remove-Item -LiteralPath $download -Force -Recurse -ErrorAction SilentlyContinue }
}
if (-not (Test-Path "$vendor\deno.exe")) {
    Write-Host 'Fetching Deno Windows runtime...'
    $download = Join-Path $env:TEMP ('acapella_deno_' + [guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $download | Out-Null
    try {
        Invoke-WebRequest -Uri 'https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip' -OutFile "$download\deno.zip"
        Expand-Archive -LiteralPath "$download\deno.zip" -DestinationPath "$download\unpacked"
        Copy-Item -LiteralPath "$download\unpacked\deno.exe" -Destination "$vendor\deno.exe" -Force
    } finally { Remove-Item -LiteralPath $download -Force -Recurse -ErrorAction SilentlyContinue }
}
& $py -m PyInstaller --noconfirm --clean AcapellaDownloader.spec
Check-Exit 'Bundle executable'

$worker = Join-Path $PSScriptRoot 'dist\AcapellaDownloader\AcapellaWorker.exe'
& $worker self-test
Check-Exit 'Test frozen worker imports and tools'
& $worker yt-dlp --version
Check-Exit 'Test frozen yt-dlp command'
$release = Join-Path $PSScriptRoot 'release'
New-Item -ItemType Directory -Force -Path $release | Out-Null
$portable = Join-Path $release 'AcapellaDownloader-Windows-Portable.zip'
if (Test-Path $portable) { Remove-Item -LiteralPath $portable -Force }
Compress-Archive -Path (Join-Path $PSScriptRoot 'dist\AcapellaDownloader') -DestinationPath $portable -CompressionLevel Optimal

$env:ACAPELLA_VERSION = $Version
$compilerCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$compilerPath = if ($compilerCommand) { $compilerCommand.Source } else { $null }
if (-not $compilerPath) {
    $known = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
    if (Test-Path $known) { $compilerPath = $known }
}
if ($compilerPath) {
    & $compilerPath installer.iss
    Check-Exit 'Build Windows installer'
    Write-Host "Installer: $release\AcapellaDownloaderSetup.exe"
} else {
    Write-Warning 'Inno Setup 6 is missing. Portable ZIP was built, but no single installer EXE. Install Inno Setup and rerun this script.'
}
Write-Host "Portable build: $portable"
