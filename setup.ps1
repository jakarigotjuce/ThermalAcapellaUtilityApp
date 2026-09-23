$ErrorActionPreference = 'Stop'
$install = Join-Path $env:LOCALAPPDATA 'Programs\AcapellaDownloader'
New-Item -ItemType Directory -Force -Path $install | Out-Null
if ($PSScriptRoot -ne $install) {
    Get-ChildItem -LiteralPath $PSScriptRoot -File | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $install -Force
    }
}
Set-Location -LiteralPath $install

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links')
}
function Install-Package([string]$id) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw 'Windows App Installer (winget) is required. Install App Installer from Microsoft Store, then run Setup.cmd again.'
    }
    & winget install --id $id --exact --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -ne 0) { throw "Could not install $id. Install it manually and run Setup.cmd again." }
    Refresh-Path
}

function Find-Python311 {
    $defaultPython = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    if (Test-Path -LiteralPath $defaultPython -PathType Leaf) { return $defaultPython }
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        # An absent runtime is an expected probe result. Read native stderr
        # directly so Windows PowerShell 5.1 cannot turn it into a fatal error.
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = $launcher.Source
        $startInfo.Arguments = '-3.11 -c "import sys; print(sys.executable)"'
        $startInfo.UseShellExecute = $false
        $startInfo.CreateNoWindow = $true
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $probe = New-Object System.Diagnostics.Process
        $probe.StartInfo = $startInfo
        try {
            $null = $probe.Start()
            $outputTask = $probe.StandardOutput.ReadToEndAsync()
            $errorTask = $probe.StandardError.ReadToEndAsync()
            if (-not $probe.WaitForExit(15000)) {
                $probe.Kill()
                $probe.WaitForExit()
                return $null
            }
            $candidate = $outputTask.Result.Trim()
            $null = $errorTask.Result
            if ($probe.ExitCode -eq 0 -and $candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
                return $candidate
            }
        } catch {
            # A missing/broken launcher does not prevent a winget install.
        } finally {
            $probe.Dispose()
        }
    }
    return $null
}

Refresh-Path
$python = Find-Python311
if (-not $python) {
    Write-Host 'Python 3.11 was not found. Installing it now...'
    Install-Package 'Python.Python.3.11'
    $python = Find-Python311
    if (-not $python) { throw 'Python 3.11 was installed but could not be located. Close this window and run Setup.cmd again.' }
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Install-Package 'Gyan.FFmpeg' }
if (-not (Get-Command deno -ErrorAction SilentlyContinue)) { Install-Package 'DenoLand.Deno' }
if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) { throw 'ffprobe is not on PATH. Reopen Windows and rerun Setup.cmd.' }

& $python -m venv (Join-Path $install '.venv')
if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
$venvPython = Join-Path $install '.venv\Scripts\python.exe'
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Could not update pip.' }
# Matching CPU builds avoid GPU-driver requirements and newer Torch API changes.
& $venvPython -m pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) { throw 'Could not install the audio processing engine.' }
& $venvPython -m pip install -r (Join-Path $install 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Could not install the app dependencies.' }
& $venvPython -c 'import tkinter, yt_dlp, demucs, librosa, torch, torchaudio'
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }
New-Item -ItemType Directory -Force -Path (Join-Path $install 'Acapella Download Processing Folder') | Out-Null
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Acapella Downloader.lnk'))
$shortcut.TargetPath = Join-Path $install 'Launch.cmd'
$shortcut.WorkingDirectory = $install
$shortcut.WindowStyle = 7
$shortcut.Save()
Write-Host "Installed in $install"
