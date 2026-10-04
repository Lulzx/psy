"""Stem levels, spectral balance, repetition score and spectrogram for the twisted track."""
import sys, inspect
import numpy as np
from scipy.signal import spectrogram
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, ".")
from psy.twisted import Twisted
from psy.dsp import SR

song = Twisted(seed=int(sys.argv[1]) if len(sys.argv) > 1 else 11)
orig = Twisted.add
stats = []
def add(self, buf, gain=1.0, **kw):
    before = self.mix.copy(); orig(self, buf, gain, **kw); d = self.mix - before
    act = np.abs(d).max(axis=1) > 1e-4
    rms = np.sqrt((d[act] ** 2).mean()) if act.any() else 0
    stats.append((inspect.stack()[1].function, 20*np.log10(rms+1e-12), 20*np.log10(np.abs(d).max()+1e-12)))
Twisted.add = add
y = song.render(log=lambda *a: None)
for c, r, p in stats: print(f"  {c:<10} rms {r:6.1f}  peak {p:6.1f}")
m = y.mean(axis=1)
print("nan", np.isnan(y).any(), "peak", np.abs(y).max().round(3), "rms dB", round(20*np.log10(np.sqrt((m**2).mean())), 1))
f, t, S = spectrogram(m, SR, nperseg=4096, noverlap=2048)
tot = S.sum()
print("band %:", {f"{a}-{b}": round(float(100*S[(f>=a)&(f<b)].sum()/tot), 1) for a, b in [(20,60),(60,120),(120,300),(300,1000),(1000,3000),(3000,8000),(8000,22050)]})
# repetition: per-bar log-spectral fingerprint, cosine similarity between bars
B = int(song.bar*SR); nb = song.bars
F = []
for b in range(nb):
    seg = m[b*B:(b+1)*B]
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    edges = np.geomspace(30, 16000, 97); fr = np.fft.rfftfreq(len(seg), 1/SR)
    F.append(np.log1p([sp[(fr>=edges[i])&(fr<edges[i+1])].sum() for i in range(96)]))
F = np.array(F); F = F - F.mean(1, keepdims=True); F /= np.linalg.norm(F, axis=1, keepdims=True) + 1e-9
C = F @ F.T; np.fill_diagonal(C, 0)
# also sample-level identity: max normalized xcorr at zero lag between bars
W = np.array([m[b*B:(b+1)*B] for b in range(nb)]); W = W / (np.linalg.norm(W, axis=1, keepdims=True)+1e-9)
X = W @ W.T; np.fill_diagonal(X, 0)
print(f"bars whose audio is ≥0.95 identical to another bar: {int((X.max(1) >= 0.95).sum())}/{nb}  (≥0.8: {int((X.max(1) >= 0.8).sum())})")
fig, ax = plt.subplots(1, 2, figsize=(18, 5), gridspec_kw=dict(width_ratios=[3, 1]))
ax[0].pcolormesh(t, f, 10*np.log10(S+1e-12), shading="auto", vmin=-110, vmax=-30, cmap="magma")
ax[0].set_yscale("symlog", linthresh=200); ax[0].set_ylim(20, 20000)
for name, s, n, _ in song.sections: ax[0].axvline(s*song.bar, color="c", lw=0.6); ax[0].text(s*song.bar+1, 15000, name, color="c")
ax[1].imshow(X, cmap="viridis", vmin=0, vmax=1); ax[1].set_title("bar-vs-bar waveform similarity")
plt.savefig("out/twisted_check.png", dpi=65, bbox_inches="tight")
