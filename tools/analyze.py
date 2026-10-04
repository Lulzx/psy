"""Per-stem levels, spectral balance and a spectrogram PNG for a style."""
import sys, inspect
import numpy as np
from scipy.signal import spectrogram
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, ".")
from psy import Song
from psy.dsp import SR

style = sys.argv[1]; length = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
song = Song(style, seed=1, length=length)
orig = Song.add
stats = []
def add(self, buf, gain=1.0, **kw):
    caller = inspect.stack()[1].function
    before = self.mix.copy()
    orig(self, buf, gain, **kw)
    d = self.mix - before
    act = np.abs(d).max(axis=1) > 1e-4
    rms = np.sqrt((d[act] ** 2).mean()) if act.any() else 0
    stats.append((caller, 20 * np.log10(rms + 1e-12), 20 * np.log10(np.abs(d).max() + 1e-12)))
Song.add = add
y = song.render(log=lambda *a: None)
print(song.describe())
for c, r, p in stats:
    print(f"  {c:<10} rms(active) {r:6.1f} dB  peak {p:6.1f} dB")
m = y.mean(axis=1)
print("nan:", np.isnan(y).any(), " peak:", np.abs(y).max().round(3), " rms dB:", round(20*np.log10(np.sqrt((m**2).mean())),1))
f, t, S = spectrogram(m, SR, nperseg=4096, noverlap=2048)
bands = [(20, 80), (80, 250), (250, 2000), (2000, 8000), (8000, 20000)]
tot = S.sum()
print("band energy %:", {f"{a}-{b}": round(100*S[(f>=a)&(f<b)].sum()/tot, 1) for a, b in bands})
plt.figure(figsize=(14, 5))
plt.pcolormesh(t, f, 10*np.log10(S+1e-12), shading="auto", vmin=-110, vmax=-30, cmap="magma")
plt.yscale("symlog", linthresh=200); plt.ylim(20, 20000); plt.title(style)
plt.savefig(f"out/{style}_spec.png", dpi=70, bbox_inches="tight")
