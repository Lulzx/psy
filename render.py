#!/usr/bin/env python3
"""Render psytrance tracks.

    python3 render.py                      # every style
    python3 render.py goa darkpsy --seed 7
    python3 render.py fullon --length 0.5  # half-length arrangement
    python3 render.py --list
"""
import argparse
import os
import shutil
import subprocess
import time

from scipy.io import wavfile

from psy import Song, STYLES
from psy.dsp import SR, to_int16


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("styles", nargs="*", help="style keys (default: all)")
    ap.add_argument("--seed", type=int, default=1, help="random seed: changes riffs, key, fx")
    ap.add_argument("--length", type=float, default=1.0, help="arrangement length multiplier")
    ap.add_argument("--root", type=int, help="override key root as MIDI note (e.g. 30 = F#1)")
    ap.add_argument("--out", default="out")
    ap.add_argument("--no-mp3", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    if a.list:
        for k, s in STYLES.items():
            print(f"{k:<12} {s['name']:<22} {s['bpm']} BPM  {s['scale']}")
        return
    os.makedirs(a.out, exist_ok=True)
    for key in a.styles or list(STYLES):
        if key not in STYLES:
            raise SystemExit(f"unknown style '{key}', try --list")
        t0 = time.time()
        song = Song(key, seed=a.seed, length=a.length, root=a.root)
        print(song.describe())
        audio = song.render()
        base = os.path.join(a.out, f"{key}_s{a.seed}")
        wavfile.write(base + ".wav", SR, to_int16(audio))
        with open(base + ".txt", "w") as f:
            f.write(song.describe() + "\n")
        if not a.no_mp3 and shutil.which("ffmpeg"):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", base + ".wav",
                            "-b:a", "320k", base + ".mp3"], check=True)
        print(f"  -> {base}.wav ({time.time() - t0:.1f}s)\n")


if __name__ == "__main__":
    main()
