#!/usr/bin/env python3
"""Render a piece.  python3 make_song.py [--piece mycelium|journey|twisted|wild_current|follower] [--seed N] [--root MIDI] [--air X]"""
import argparse, os, shutil, subprocess, time
from scipy.io import wavfile
from psy.journey import Journey
from psy.mycelium import Mycelium
from psy.twisted import Twisted
from psy.wild_current import WildCurrent
from psy.follower import Follower
from psy.dsp import SR, to_int16

ap = argparse.ArgumentParser()
ap.add_argument("--piece", default="mycelium", choices=["mycelium", "journey", "twisted", "wild_current", "follower"])
ap.add_argument("--seed", type=int, help="changes every melodic/rhythmic decision, keeps the story")
ap.add_argument("--root", type=int, help="home key as MIDI note (mycelium: 28 = E1, journey/twisted: 30 = F#1)")
ap.add_argument("--air", type=float, help="soft top end above 3 kHz: 0 = fully dark (old sound), 1 = default")
ap.add_argument("--out")
a = ap.parse_args()
t0 = time.time()
cls = dict(mycelium=Mycelium, journey=Journey, twisted=Twisted, wild_current=WildCurrent, follower=Follower)[a.piece]
kw = {k: v for k, v in dict(seed=a.seed, root=a.root).items() if v is not None}
if a.air is not None:
    cls.AIR = a.air
song = cls(**kw)
a.out = a.out or f"out/{a.piece}.wav"
print(song.describe())
audio = song.render()
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
wavfile.write(a.out, SR, to_int16(audio))
if shutil.which("ffmpeg"):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.out, "-b:a", "320k", a.out[:-4] + ".mp3"], check=True)
print(f"-> {a.out} ({time.time() - t0:.0f}s)")
