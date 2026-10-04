"""Before/after comparison of two renders: loudness, width, depth, spectrum.
python3 tools/compare.py out/mycelium_before.wav out/mycelium.wav"""
import sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import welch
sys.path.insert(0, ".")
from psy.dsp import lufs, static, SR


def stats(path):
    sr, x = wavfile.read(path)
    x = x.astype(float) / 32768
    hi = static(x, "hp", 300, order=4)
    M, S = x.mean(1), (x[:, 0] - x[:, 1]) / 2
    f, P = welch(M, sr, nperseg=8192)
    _, Ps = welch(S, sr, nperseg=8192)
    band = lambda a, b: (f >= a) & (f < b)
    # crest of the 300 Hz+ band: lower = denser/more diffuse, reverberant space
    out = {"LUFS": lufs(x), "L/R corr (all)": np.corrcoef(x[:, 0], x[:, 1])[0, 1],
           "L/R corr (>300 Hz)": np.corrcoef(hi[:, 0], hi[:, 1])[0, 1],
           "side/mid 300-3k dB": 10 * np.log10(Ps[band(300, 3000)].sum() / P[band(300, 3000)].sum()),
           "side/mid 3-8k dB": 10 * np.log10(Ps[band(3000, 8000)].sum() / P[band(3000, 8000)].sum())}
    for a, b in [(20, 120), (120, 1000), (1000, 3000), (3000, 8000), (8000, 20000)]:
        out[f"% {a}-{b} Hz"] = 100 * (P[band(a, b)].sum() + Ps[band(a, b)].sum()) / (P.sum() + Ps.sum())
    return out


a, b = stats(sys.argv[1]), stats(sys.argv[2])
print(f"{'':<22}{'before':>10}{'after':>10}")
for k in a:
    print(f"{k:<22}{a[k]:>10.2f}{b[k]:>10.2f}")
