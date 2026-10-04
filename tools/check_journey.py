"""Levels, flow (loudness jumps), 5-second novelty and spectrogram.  python3 tools/check_journey.py [mycelium|journey] [seed]"""
import sys, inspect
import numpy as np
from scipy.signal import spectrogram
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, ".")
from psy.journey import Journey
from psy.mycelium import Mycelium
from psy.dsp import SR, static

piece = sys.argv[1] if len(sys.argv) > 1 else "mycelium"
cls = dict(mycelium=Mycelium, journey=Journey)[piece]
song = cls(**({"seed": int(sys.argv[2])} if len(sys.argv) > 2 else {}))
orig, stats = Journey.add, []
def add(self, buf, gain=1.0, **kw):
    before = self.mix.copy(); orig(self, buf, gain, **kw); d = self.mix - before
    act = np.abs(d).max(axis=1) > 1e-4
    stats.append((kw.get("src") or self.active_layer[2:], 20*np.log10(np.sqrt((d[act]**2).mean()) + 1e-12) if act.any() else -240))
Journey.add = add
y = song.render(log=lambda *a: None)
for c, r in stats: print(f"  {c:<12} rms {r:6.1f} dB")
m = y.mean(1)
from psy.dsp import lufs
print("nan", np.isnan(y).any(), " peak", round(float(np.abs(y).max()), 3), " dur", round(len(m)/SR, 1), "s",
      " LUFS", round(lufs(y), 1), " L/R corr", round(float(np.corrcoef(y[:, 0], y[:, 1])[0, 1]), 2))
f, t, S = spectrogram(m, SR, nperseg=4096, noverlap=2048); tot = S.sum()
print("band %:", {f"{a}-{b}": round(float(100*S[(f>=a)&(f<b)].sum()/tot), 2) for a, b in [(20,120),(120,1000),(1000,3000),(3000,8000),(8000,22050)]})
# flow: loudness per second, biggest 1-s jump
W = SR
L = np.array([10*np.log10(np.mean(m[i:i+W]**2)+1e-12) for i in range(0, len(m)-W, W)])
J = np.abs(np.diff(L))
print(f"loudness per second: jumps >4 dB at (s, dB): {[(int(i), round(float(J[i]),1)) for i in np.where(J > 4)[0]]}")
# novelty: 5 s windows, mel-ish spectral + chroma fingerprint, similarity to every other window
win = 5 * SR
segs = [m[i:i+win] for i in range(0, len(m) - win, win)]
def fp(x):
    sp = np.abs(np.fft.rfft(x * np.hanning(len(x)))); fr = np.fft.rfftfreq(len(x), 1/SR)
    band = [sp[(fr >= a) & (fr < b)].sum() for a, b in zip(np.geomspace(150, 6000, 49)[:-1], np.geomspace(150, 6000, 49)[1:])]
    pc = np.zeros(12); sel = (fr > 100) & (fr < 2000)
    np.add.at(pc, (np.round(12*np.log2(fr[sel]/440)) % 12).astype(int), sp[sel])
    return np.concatenate([np.log1p(band), 3 * pc / (pc.sum()+1e-9)])
F = np.array([fp(s) for s in segs]); F = (F - F.mean(0)) / (F.std(0) + 1e-9)
F /= np.linalg.norm(F, axis=1, keepdims=True); C = F @ F.T; np.fill_diagonal(C, -1)
adj = [float(F[i] @ F[i+1]) for i in range(len(F)-1)]
print(f"5-s windows: {len(F)};  most similar other window (median): {np.median(C.max(1)):.2f};  "
      f"adjacent-window similarity: mean {np.mean(adj):.2f} (1 = identical)")
print("  windows with a near-twin (>0.9) elsewhere:", int((C.max(1) > 0.9).sum()))
fig, ax = plt.subplots(2, 1, figsize=(18, 8), gridspec_kw=dict(height_ratios=[3, 1]))
ax[0].pcolormesh(t, f, 10*np.log10(S+1e-12), shading="auto", vmin=-110, vmax=-30, cmap="magma")
ax[0].set_yscale("symlog", linthresh=200); ax[0].set_ylim(20, 8000)
for ch in song.CHAPTERS:
    s = song.t0[song.chap_start[ch["name"]]]; ax[0].axvline(s, color="c", lw=0.7); ax[0].text(s + 1, 5000, ch["name"], color="c")
ax[1].plot(np.arange(len(L)), L); ax[1].plot(song.t0[:-1], song.E * 20 - 40, "--"); ax[1].set_title("loudness (dB/s) and energy curve")
plt.tight_layout(); plt.savefig(f"out/{piece}_check.png", dpi=60)
