"""Estimate tempo and global musical key; runs out of process for cancellation."""
import json
import sys
import numpy as np
import librosa


def analyze(path):
    # Analyze up to three minutes of the full mix, not the isolated vocal.
    audio, sr = librosa.load(path, sr=22050, duration=180, mono=True)
    if len(audio) < sr or np.max(np.abs(audio)) < 1e-5:
        return {"key": "Unknown key", "bpm": "Unknown"}
    tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
    bpm = float(np.asarray(tempo).reshape(-1)[0])
    harmonic = librosa.effects.harmonic(audio)
    chroma = librosa.feature.chroma_stft(y=harmonic, sr=sr).mean(axis=1)
    profiles = {
        "major": np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]),
        "minor": np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]),
    }
    names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    scores = [(float(np.corrcoef(chroma, np.roll(profile, index))[0, 1]), f"{names[index]} {mode}")
              for mode, profile in profiles.items() for index in range(12)]
    finite = [(score, key) for score, key in scores if np.isfinite(score)]
    key = max(finite)[1] if finite else "Unknown key"
    return {"key": key, "bpm": round(bpm, 1) if np.isfinite(bpm) and bpm > 0 else "Unknown"}


if __name__ == "__main__":
    print(json.dumps(analyze(sys.argv[1])))
