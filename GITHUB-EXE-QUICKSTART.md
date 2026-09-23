# Make your Acapella Downloader installer EXE using GitHub

**What this package is:** the app source plus build scripts. An actual Windows `.exe` cannot be compiled or verified on the Linux machine where this package was prepared. GitHub Actions runs on Windows and creates `AcapellaDownloaderSetup.exe` for you.

## Upload the source to GitHub

1. Extract `AcapellaDownloader_Windows_BuildKit.zip` fully. The extracted folder should contain `app.py`, `worker.py`, `AcapellaDownloader.spec`, `Build-Windows.ps1`, and the hidden `.github/workflows/windows-release.yml`.
2. Create a **public** repository named `AcapellaDownloader` at https://github.com/new (make it private until you're ready to publish, if you prefer). If you already created a repository, use that.
3. Easiest way to upload a whole folder including the hidden `.github` workflow: install [GitHub Desktop](https://desktop.github.com/), clone your repository, and copy **all the extracted files and folders** into the local clone. In GitHub Desktop, write a commit message and click **Commit to main**, then **Push origin**. If your repo is new, you can alternatively upload all the extracted files using GitHub's **Add file → Upload files**; make sure the `.github/workflows/windows-release.yml` file is actually present afterward.
4. On your repository page, select **Actions**. If asked, enable workflows. Open **Build Windows EXE release**, select **Run workflow**, leave `version` as `1.0.0`, and run it. To publish another release later, enter a different version such as `1.0.1`.
5. When the workflow succeeds, go to your repository's **Releases** page. Download `AcapellaDownloaderSetup.exe` and test it yourself on Windows. You can also download `AcapellaDownloader-Windows-Portable.zip` if you prefer not to run an installer.
6. Your shareable Instagram download page will look like `https://github.com/YOUR-USERNAME/AcapellaDownloader/releases/latest` (replace YOUR-USERNAME with yours).

If Actions reports a failure while publishing the release, check that workflow permission to write repository contents is allowed in **Settings → Actions → General → Workflow permissions** (repository/organization policy may limit this).

## What gets installed

- `AcapellaDownloader.exe` – your GUI
- `AcapellaWorker.exe` – console helper used by the GUI for yt-dlp, Demucs and key/BPM detection
- `_internal/` – packaged Python, Torch, audio dependencies and FFmpeg/ffprobe/Deno

**Do not send `AcapellaDownloader.exe` from the portable build alone.** It needs its companion files. Send `AcapellaDownloaderSetup.exe`, which contains everything in a single installer, or share the **whole portable ZIP**.

The recipient does **not** need Python or the original `Setup.cmd`. Audio separation runs locally on the recipient's CPU; on the first run, Demucs downloads the audio model. The build is not code-signed, so Windows may show a publisher or reputation warning. Never ask anyone to disable antivirus. Download and process only audio you are authorized to use.

## Build directly on your own Windows laptop (alternative)

Install 64-bit Python 3.11 from https://www.python.org/downloads/ and [Inno Setup 6](https://jrsoftware.org/isinfo.php) if you want the installer EXE. Then double-click `Build-EXE.cmd` while online. The script creates its own `.build-venv`, installs the dependencies, downloads Windows FFmpeg and Deno, runs tests, bundles the software, and runs a bundled-worker smoke test. A portable ZIP appears in `release/`; if Inno Setup is installed, `release/AcapellaDownloaderSetup.exe` also appears.

The build kit cannot guarantee a successful build without running it on Windows. If compilation fails, paste the GitHub Actions error log into ChatGPT to diagnose it.
