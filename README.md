# Acapella Downloader — Windows EXE build kit

**For sharing on Instagram:** create a public GitHub repo containing this extracted project (including `.github/workflows/`), then go to **Actions → Build Windows EXE release → Run workflow**. The Windows workflow builds `AcapellaDownloaderSetup.exe`, tests its console helper, packages a portable ZIP, and publishes both to **Releases**. See [GITHUB-EXE-QUICKSTART.md](GITHUB-EXE-QUICKSTART.md) for exact steps.

**Run locally on Windows 10/11:** install Python 3.11 x64, optionally install Inno Setup 6, and double-click `Build-EXE.cmd`. Without Inno Setup you still get a portable ZIP containing `AcapellaDownloader.exe`; with it you also get a single installer EXE. This build kit is source code and build automation, **not itself a compiled Windows EXE**. A real Windows build and end-to-end audio test are required before distributing to others.

**For recipients:** provide only `AcapellaDownloaderSetup.exe` from the release; they do not need the source ZIP or Python. The installer includes the Python application, FFmpeg, ffprobe, and Deno. The first audio separation still needs internet to download the Demucs model. Unsigned apps may show a Windows reputation warning.

---

## Original source-install instructions (legacy)

# Acapella Downloader — Windows desktop app, v0.2

Thermal interface: dark teal panels, warm yellow-green controls, a procedural thermal glow with grain, and a three-part search/export/save layout. The reference photo is not embedded. Decorative thermal artwork is not a waveform or live analysis.

**Already installed?** Close the app, extract this ZIP, and run **Update-GUI.cmd** from the extracted folder. It updates the interface without reinstalling audio dependencies or changing your saved destination. Open your usual desktop shortcut afterward. The previous interface is backed up as `app.previous.py` in the installed app folder.

Installer fix: a missing Python 3.11 runtime now falls through to installation instead of stopping on the Python launcher's diagnostic message. Runtime detection is repeated after installation.

## Start here

1. Extract this entire ZIP into a folder. Do not launch from inside the ZIP.
2. Double-click **Setup.cmd**. Internet access and Windows App Installer are required. Windows may show normal installer prompts for dependencies.
3. Open **Acapella Downloader** from the desktop shortcut.
4. Click **Choose folder** once to set your destination. It remains saved when you restart.
5. Search for a song, select the correct result, and click **Download acapella**. You can also paste a full YouTube video URL or use a local audio file.

Example output: `Artist - Song (F minor, 94.0 BPM).mp3`

## What this version does

- Searches YouTube and lets you pick from eight results, showing title, channel, and duration.
- Downloads the chosen video's audio and converts it to a 320 kb/s MP3.
- Removes parenthesized or bracketed “Official Video” and “Official Music Video” from the final title. Preserves other parenthesized text.
- Uses Demucs locally to separate vocals, then exports just the vocals at 320 kb/s.
- Estimates the key and tempo from up to the first three minutes of the original mix, before vocal separation.
- Allows title, key, and BPM overrides before processing.
- Saves the destination globally for this Windows user. Uses numbered filenames for duplicates rather than overwriting.
- Runs one job at a time and supports cancellation. Closing while working cancels the active process first.

## Workflow difference from your specification

This version uses yt-dlp and local Demucs processing instead of controlling CnvMP3 and vocalremover.org. No browser clicks or uploads to those sites are implemented. The result and folder workflow are the same, but separation quality and key/BPM estimates can differ from those websites.

The app is installed in your **per-user Programs folder**:

`%LOCALAPPDATA%\Programs\AcapellaDownloader`

Its working folder is inside that app folder:

`Acapella Download Processing Folder`

This avoids requiring administrator permission to write under `C:\Program Files`. Each job has its own subfolder, so the app processes the exact download it just made rather than an unrelated “most recent” file. These subfolders contain source audio, separated WAV files, and a job log. They remain available after success, failure, or cancellation. You can delete completed job subfolders when the app is idle to reclaim disk space.

Settings live at `%LOCALAPPDATA%\AcapellaDownloader\settings.json`.

## Setup and performance

Requires 64-bit Windows 10/11, Python 3.11, FFmpeg, and Deno. Setup installs missing tools with winget, then creates an isolated Python environment. It installs matching PyTorch 2.5.1 CPU packages, Demucs 4.0.1, librosa 0.11.0, and the current yt-dlp with its default dependencies. Third-party software retains its own licenses.

Allow several GB of free disk space and several minutes for setup. The first separation downloads the model. CPU separation can take several minutes or longer per song; the activity bar does not estimate completion time. GPU acceleration is not configured in this version.

## Accuracy and troubleshooting

- Key/BPM are estimates, not verified metadata. Relative major/minor and half/double-time tempo errors are possible. Set overrides if you know the correct values. If analysis fails, the app uses “Unknown” labels and still attempts vocal extraction.
- 320 kb/s is the output encoding rate; it cannot restore quality absent from YouTube's source. Some instruments or reverb may remain in isolated vocals.
- If YouTube downloading fails, run **Update-Downloader.cmd** from the installed app folder. Private, restricted, unavailable, or bot-challenged videos may not download. This version has no login/cookie flow; you can use a local audio file instead.
- For processing errors, see the on-screen details and `job.log` in that job's processing subfolder.
- If setup fails, read the error and rerun Setup.cmd after fixing the indicated dependency or connection issue.
- Source and output filenames are sanitized for Windows. Long title text is shortened to reduce path-length problems.

Use audio you own or have permission to download and process.

## Verification status

This is a source-based desktop app with Windows setup scripts, not a compiled `.exe`. Core automated checks cover title cleanup, URL validation, persistent settings, collision handling, real FFmpeg encoding, cancellation, and the pipeline's file routing with simulated external tools. Windows setup, GUI appearance, live YouTube downloading, and actual model separation have not been verified in this build environment. A complete test on your Windows PC remains necessary.

Run the included checks with `python -m unittest discover -s tests -v` from the extracted source folder. A real FFmpeg encoding check runs when FFmpeg and ffprobe are present.

## Upstream documentation

- yt-dlp: https://github.com/yt-dlp/yt-dlp
- Demucs: https://github.com/facebookresearch/demucs
- librosa: https://librosa.org/doc/latest/
- Requested converter: https://cnvmp3.com/v55
- Requested vocal separator: https://vocalremover.org/
