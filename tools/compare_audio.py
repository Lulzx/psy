"""Compare rendered WAVs without treating stereo width as a quality score.

python3 tools/compare_audio.py out/mycelium.wav out/mycelium_improved.wav
Writes out/mycelium_comparison.json and matched 30–75 s MP3 previews.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, welch


def db(x):
    return float(10 * np.log10(max(float(x), 1e-15)))


def analyze(path, preview):
    sr, pcm = wavfile.read(path)
    scale = float(max(abs(np.iinfo(pcm.dtype).min), np.iinfo(pcm.dtype).max)) if pcm.dtype.kind == "i" else 1.0
    x = pcm.astype(np.float64) / scale
    if x.ndim != 2 or x.shape[1] != 2:
        raise ValueError("Expected a stereo WAV")
    report = dict(path=str(path), seconds=len(x) / sr,
                  finite=bool(np.isfinite(x).all()), sample_peak_db=db(np.max(x*x)))
    seconds = np.array([db(np.mean(x[i:i + sr] ** 2)) for i in range(0, len(x) - sr, sr)])
    # Exclude opening/fade when summarizing chapter dynamics.
    report["dynamics_p90_minus_p10_db"] = float(np.percentile(seconds[10:-10], 90) - np.percentile(seconds[10:-10], 10))
    report["windows"] = []
    for start in (30, 90, 150):
        a = x[start*sr:(start+15)*sr]
        mid, side = a.mean(1), (a[:, 0] - a[:, 1]) / 2
        high = sosfilt(butter(4, 300, btype="highpass", fs=sr, output="sos"), a, axis=0)
        low = sosfilt(butter(4, 120, fs=sr, output="sos"), a, axis=0)
        f, power = welch(a, fs=sr, nperseg=8192, axis=0); power = power.sum(1)
        report["windows"].append(dict(start_seconds=start, rms_db=db(np.mean(a*a)),
            lr_correlation=float(np.corrcoef(a.T)[0, 1]),
            correlation_above_300hz=float(np.corrcoef(high.T)[0, 1]),
            correlation_below_120hz=float(np.corrcoef(low.T)[0, 1]),
            side_mid_db=db(np.mean(side*side) / max(np.mean(mid*mid), 1e-15)),
            mono_loss_db=db(np.mean(mid*mid) / max(np.mean(a*a), 1e-15)),
            bands_percent={f"{lo}-{hi}": float(100*power[(f>=lo)&(f<hi)].sum()/power.sum())
                           for lo,hi in ((20,120),(120,1000),(1000,3000),(3000,8000))}))
    # Equal excerpt RMS, with ample headroom, for a fair listening comparison.
    excerpt = x[30*sr:75*sr].copy()
    excerpt *= 10 ** (-20/20) / max(np.sqrt(np.mean(excerpt**2)), 1e-12)
    if np.max(np.abs(excerpt)) >= 1:
        raise ValueError("Matched preview would clip")
    fade = min(int(0.04 * sr), len(excerpt)//2)
    excerpt[:fade] *= np.linspace(0, 1, fade)[:, None]
    excerpt[-fade:] *= np.linspace(1, 0, fade)[:, None]
    wavfile.write(preview, sr, np.round(excerpt * 32767).astype(np.int16))
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(preview),
                        "-b:a", "320k", str(preview.with_suffix(".mp3"))], check=True)
    return report


if __name__ == "__main__":
    before, after = map(Path, sys.argv[1:3])
    results = [analyze(before, Path("out/mycelium_before_preview.wav")),
               analyze(after, Path("out/mycelium_improved_preview.wav"))]
    Path("out/mycelium_comparison.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
