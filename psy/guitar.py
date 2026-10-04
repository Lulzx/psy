"""Steel-string guitar synthesis: picked strings, palm muting and strums."""
import numpy as np
from scipy.signal import lfilter
from . import dsp


def picked_string(midi, duration, rng, muted=False, strength=0.8):
    """Fractionally tuned string loop with pick-position notch and body modes."""
    hz = dsp.midi_hz(midi)
    tail = 0.12 if muted else 0.65
    n = int((duration + tail) * dsp.SR)
    period = dsp.SR / hz
    delay = period - 0.5  # averaging filter contributes half a sample
    integer = int(np.floor(delay))
    fraction = delay - integer
    w = 2 * np.pi / period
    ratio = np.tan(w * fraction / 2) / np.tan(w / 2)
    alpha = (1 - ratio) / (1 + ratio)
    excitation = np.zeros(n)
    size = min(int(period), n)
    pick = dsp.static(rng.normal(size=size), "lp", 4200)
    pick -= 0.75 * np.roll(pick, max(1, int(period * rng.uniform(0.12, 0.2))))
    excitation[:size] = pick * np.hanning(size)
    decay = 0.32 if muted else 2.5
    loss = 10 ** (-3 / (hz * decay))
    denominator = np.zeros(integer + 4)
    denominator[0], denominator[1] = 1, alpha
    denominator[integer:integer+3] -= 0.5 * loss * np.array([alpha, 1+alpha, 1])
    string = lfilter([1, alpha], denominator, excitation)
    body = string + 0.32*dsp.static(string,"bp",(180,700))
    body = dsp.drive(body / max(np.max(np.abs(body)),1e-9), 1.15 if muted else 0.8)
    t = np.arange(n)/dsp.SR
    body *= np.clip((duration+tail-t)/tail,0,1)
    if muted:
        body *= np.exp(-t/0.065)
    return dsp.fade_edges(body*strength,0.0005,0.015)


def strum(midis, duration, rng, muted=False, up=False):
    """One human strum; adjacent strings are picked 5-10 ms apart."""
    order = list(midis)[::-1] if up else list(midis)
    spacing = rng.uniform(0.005,0.010)
    n = int((duration+(0.12 if muted else 0.65)+spacing*len(order))*dsp.SR)
    out = np.zeros(n)
    for j,midi in enumerate(order):
        string = picked_string(midi,duration,rng,muted,strength=0.85-0.08*j)
        start = int(j*spacing*dsp.SR)
        end = min(n,start+len(string))
        out[start:end] += string[:end-start]
    return out / max(np.max(np.abs(out)),1e-9)*0.85
