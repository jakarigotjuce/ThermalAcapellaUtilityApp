"""Console helper for bundled audio jobs; kept separate from the windowed GUI."""
import json
import multiprocessing
import shutil
import sys
from core import configure_runtime_tools


def main(args):
    configure_runtime_tools()
    if not args:
        print("Usage: AcapellaWorker.exe [yt-dlp|demucs|analyze|self-test] ...", file=sys.stderr)
        return 2
    command, *rest = args
    if command == "yt-dlp":
        # yt-dlp's CLI expects its own argv without this helper's command name.
        from yt_dlp import main as ytdlp_main
        sys.argv = [sys.argv[0], *rest]
        return ytdlp_main() or 0
    if command == "demucs":
        from demucs.separate import main as demucs_main
        sys.argv = [sys.argv[0], *rest]
        return demucs_main() or 0
    if command == "analyze":
        if len(rest) != 1:
            print("Analyze requires one audio path.", file=sys.stderr)
            return 2
        from analyze import analyze
        print(json.dumps(analyze(rest[0])))
        return 0
    if command == "self-test":
        import tkinter
        import yt_dlp
        import demucs.separate
        import librosa
        import torch
        import torchaudio
        for executable in ("ffmpeg", "ffprobe", "deno"):
            if not shutil.which(executable):
                raise RuntimeError(f"Bundled tool not found: {executable}")
        print("Bundled imports and media tools: OK")
        return 0
    print("Unknown command: " + command, file=sys.stderr)
    return 2


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main(sys.argv[1:]))
