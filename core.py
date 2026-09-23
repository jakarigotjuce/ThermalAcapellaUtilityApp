"""Acapella Downloader: filesystem rules and cancellable processing pipeline."""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Frozen installs keep all downloads and logs outside the read-only app folder.
SOURCE_DIR = Path(__file__).resolve().parent
FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = (Path(os.environ.get("LOCALAPPDATA", Path.home())) / "AcapellaDownloader") if FROZEN else SOURCE_DIR
BUNDLED_TOOLS = Path(getattr(sys, "_MEIPASS", SOURCE_DIR)) / "tools"


def configure_runtime_tools():
    """Make bundled FFmpeg, ffprobe, and Deno visible to yt-dlp and Demucs."""
    if FROZEN and BUNDLED_TOOLS.is_dir():
        paths = os.environ.get("PATH", "").split(os.pathsep)
        if str(BUNDLED_TOOLS) not in paths:
            os.environ["PATH"] = str(BUNDLED_TOOLS) + os.pathsep + os.environ.get("PATH", "")


def worker_command(kind, *args):
    """Use the console helper after freezing; use Python when run from source."""
    if FROZEN:
        worker = Path(sys.executable).with_name("AcapellaWorker.exe")
        if not worker.is_file():
            raise RuntimeError("AcapellaWorker.exe is missing. Reinstall the complete application.")
        return [str(worker), kind, *args]
    if kind in ("yt-dlp", "demucs"):
        return [sys.executable, "-m", {"yt-dlp": "yt_dlp", "demucs": "demucs"}[kind], *args]
    if kind == "analyze":
        return [sys.executable, str(SOURCE_DIR / "analyze.py"), *args]
    raise ValueError("Unknown worker type: " + kind)


PROCESSING_NAME = "Acapella Download Processing Folder"


def clean_title(title):
    title = re.sub(r"\(\s*official\s+(?:music\s+)?video\s*\)|\[\s*official\s+(?:music\s+)?video\s*\]", "", title, flags=re.I)
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title)
    title = re.sub(r"\s+", " ", title).strip(" .")[:120].rstrip(" .") or "Untitled"
    if title.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1,10)), *(f"LPT{i}" for i in range(1,10))}:
        title = "_" + title
    return title


def youtube_url(value):
    parsed = urlparse(value.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Paste a full YouTube video URL beginning with https://.")
    host = (parsed.hostname or "").lower()
    if host in ("youtu.be", "www.youtu.be"):
        video = parsed.path.strip("/")
    elif host in ("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"):
        parts = parsed.path.strip("/").split("/")
        video = parse_qs(parsed.query).get("v", [""])[0] if parsed.path == "/watch" else (parts[1] if len(parts) == 2 and parts[0] in ("shorts", "embed", "live") else "")
    else:
        raise ValueError("Only YouTube video links are supported.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video):
        raise ValueError("That link does not contain a valid YouTube video ID.")
    return "https://www.youtube.com/watch?v=" + video


class Settings:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(os.environ.get("LOCALAPPDATA", Path.home() / ".config")) / "AcapellaDownloader" / "settings.json"

    def load(self):
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(value, dict) and isinstance(value.get("output"), str) and value["output"]:
                return value
        except (OSError, ValueError):
            pass
        return {"output": str(Path.home() / "Music" / "Acapellas")}

    def save(self, output):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"output": str(output)}, indent=2), encoding="utf-8")
        temporary.replace(self.path)


def export_unique(source, output, title, key, bpm):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    stem = f"{clean_title(title)} ({clean_title(key)}, {bpm} BPM)"
    for number in range(1, 10000):
        destination = output / (stem + (f" ({number})" if number > 1 else "") + ".mp3")
        try:
            handle = destination.open("xb")
        except FileExistsError:
            continue
        try:
            with handle, Path(source).open("rb") as incoming:
                shutil.copyfileobj(incoming, handle)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        return destination
    raise RuntimeError("Too many files with the same title in the destination.")


class Cancelled(Exception):
    pass


class Runner:
    def __init__(self, emit=lambda kind, data: None):
        self.emit = emit
        self.cancelled = threading.Event()

    def check(self):
        if self.cancelled.is_set():
            raise Cancelled("Cancelled. No final file was exported.")

    def run(self, command, log=None):
        self.check()
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", **kwargs) as process:
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=0.2)
                    break
                except subprocess.TimeoutExpired:
                    if self.cancelled.is_set():
                        if os.name == "nt":
                            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        else:
                            import signal
                            try:
                                os.killpg(process.pid, signal.SIGTERM)
                            except ProcessLookupError:
                                pass
                        try:
                            process.communicate(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.communicate()
                        self.check()
        self.check()
        if log:
            with Path(log).open("a", encoding="utf-8") as handle:
                handle.write("\n" + subprocess.list2cmdline(command) + "\n" + stdout + "\n" + stderr)
        if process.returncode:
            raise RuntimeError((stderr or stdout or "Command failed")[-2200:])
        return stdout

    def search(self, query):
        text = self.run(worker_command("yt-dlp", "--ignore-config", "--flat-playlist", "--dump-single-json", "--no-warnings", "--socket-timeout", "30", "--", "ytsearch8:" + query))
        data = json.loads(text)
        return [entry for entry in data.get("entries", []) if entry and re.fullmatch(r"[A-Za-z0-9_-]{11}", entry.get("id", ""))]

    def process(self, url, output, title_override="", key_override="", bpm_override="", local=None, app_dir=APP_DIR):
        if bpm_override:
            bpm = float(bpm_override)
            if not 20 <= bpm <= 400:
                raise ValueError("BPM must be between 20 and 400, or left blank for detection.")
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise RuntimeError("FFmpeg is missing. Run Setup.cmd, then reopen the app.")
        Path(output).mkdir(parents=True, exist_ok=True)
        probe = Path(output) / (".write-test-" + uuid.uuid4().hex)
        probe.touch()
        probe.unlink()
        job = Path(app_dir) / PROCESSING_NAME / uuid.uuid4().hex[:12]
        job.mkdir(parents=True)
        log = job / "job.log"
        self.emit("log", f"Working folder: {job}")
        source = job / "source.mp3"
        if local:
            title = title_override or Path(local).stem
            self.emit("stage", "1/4 · Preparing local audio")
            self.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(local), "-vn", "-c:a", "libmp3lame", "-b:a", "320k", str(source)], log)
        else:
            url = youtube_url(url)
            self.emit("stage", "1/4 · Downloading audio at 320 kb/s")
            self.run(worker_command("yt-dlp", "--ignore-config", "--no-playlist", "--no-progress", "--socket-timeout", "30", "--retries", "3", "--write-info-json", "-f", "bestaudio/best", "-x", "--audio-format", "mp3", "--audio-quality", "320K", "-o", str(job / "source.%(ext)s"), "--", url), log)
            metadata = json.loads((job / "source.info.json").read_text(encoding="utf-8"))
            title = title_override or metadata.get("title", "Untitled")
        if not source.is_file():
            raise RuntimeError("Download did not produce the expected audio file. See job.log.")
        self.emit("stage", "2/4 · Estimating key and BPM from the full song")
        key, bpm = key_override or "Unknown key", bpm_override or "Unknown"
        if not (key_override and bpm_override):
            try:
                analysis = json.loads(self.run(worker_command("analyze", str(source)), log))
                key = key_override or analysis["key"]
                bpm = bpm_override or analysis["bpm"]
            except Cancelled:
                raise
            except Exception as error:
                self.emit("log", "Detection unavailable; keeping unknown labels or your overrides. " + str(error)[-300:])
        self.emit("stage", "3/4 · Isolating vocals (first run downloads the model)")
        self.run(worker_command("demucs", "--two-stems", "vocals", "-n", "htdemucs", "-d", "cpu", "-j", "1", "--segment", "7", "-o", str(job / "stems"), str(source)), log)
        vocals = job / "stems" / "htdemucs" / "source" / "vocals.wav"
        if not vocals.is_file():
            raise RuntimeError("The separator did not produce vocals.wav. See job.log.")
        self.emit("stage", "4/4 · Exporting vocals at 320 kb/s")
        encoded = job / "acapella.mp3"
        self.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(vocals), "-c:a", "libmp3lame", "-b:a", "320k", str(encoded)], log)
        self.check()
        result = export_unique(encoded, output, title, key, bpm)
        self.emit("log", f"Key/BPM: {key}, {bpm} BPM (automatic values are estimates)")
        return result
