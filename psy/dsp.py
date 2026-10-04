"""Low-level DSP: oscillators, envelopes, filters, effects, mastering."""
import numpy as np
from scipy.signal import lfilter, butter, sosfilt, oaconvolve
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d

SR = 44100


def midi_hz(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=np.float64) - 69.0) / 12.0)


def secs(n):
    return np.arange(n) / SR


# ---------------------------------------------------------------- oscillators

def phasor(freq, n, phase0=0.0):
    f = np.asarray(freq, dtype=np.float64)
    inc = np.full(n, f / SR) if f.ndim == 0 else f[:n] / SR
    ph = (phase0 + np.cumsum(inc) - inc) % 1.0
    return ph, inc


def _blep(p, dt):
    out = np.zeros_like(p)
    m = p < dt
    t = p[m] / dt[m]
    out[m] = t + t - t * t - 1.0
    m = p > 1.0 - dt
    t = (p[m] - 1.0) / dt[m]
    out[m] = t * t + t + t + 1.0
    return out


def saw(freq, n, phase0=0.0):
    """Band-limited (polyBLEP) sawtooth."""
    p, dt = phasor(freq, n, phase0)
    return 2.0 * p - 1.0 - _blep(p, dt)


def pulse(freq, n, width=0.5, phase0=0.0):
    p, dt = phasor(freq, n, phase0)
    q = (p + 1.0 - width) % 1.0
    a = 2.0 * p - 1.0 - _blep(p, dt)
    b = 2.0 * q - 1.0 - _blep(q, dt)
    out = a - b
    return out - out.mean() if n else out


def sine(freq, n, phase0=0.0):
    p, _ = phasor(freq, n, phase0)
    return np.sin(2 * np.pi * p)


def noise(n, rng):
    return rng.uniform(-1.0, 1.0, n)


# ---------------------------------------------------------------- envelopes

def adsr(n, a, d, s, r, gate):
    """Linear attack, exponential decay, linear release. Times in seconds."""
    t = secs(n)
    a = max(a, 1e-4)
    env = np.where(t < a, t / a, s + (1.0 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    g = int(gate * SR)
    if g < n:
        lvl = env[min(g, n - 1)]
        rel = np.clip(1.0 - (t[g:] - gate) / max(r, 1e-4), 0.0, 1.0)
        env[g:] = lvl * rel
    return env


def fade_edges(x, fin=0.002, fout=0.004):
    n = len(x)
    i, o = min(int(fin * SR), n), min(int(fout * SR), n)
    if i:
        x[:i] *= np.linspace(0, 1, i)
    if o:
        x[n - o:] *= np.linspace(1, 0, o)
    return x


# ---------------------------------------------------------------- filters

def _biquad(kind, fc, q):
    fc = np.clip(np.asarray(fc, dtype=np.float64), 15.0, SR * 0.45)
    q = np.maximum(np.asarray(q, dtype=np.float64), 0.1)
    w0 = 2 * np.pi * fc / SR
    c, s = np.cos(w0), np.sin(w0)
    alpha = s / (2 * q)
    if kind == "lp":
        b0 = (1 - c) / 2; b1 = 1 - c; b2 = b0
    elif kind == "hp":
        b0 = (1 + c) / 2; b1 = -(1 + c); b2 = b0
    elif kind == "bp":
        b0 = alpha; b1 = np.zeros_like(c); b2 = -alpha
    else:
        raise ValueError(kind)
    a0 = 1 + alpha
    b = np.stack(np.broadcast_arrays(b0, b1, b2), axis=-1) / np.expand_dims(a0, -1)
    a = np.stack(np.broadcast_arrays(a0, -2 * c, 1 - alpha), axis=-1) / np.expand_dims(a0, -1)
    return b, a


def filt(x, kind, fc, q=0.707, block=32):
    """Biquad filter. `fc` (and `q`) may be per-sample arrays for sweeps;
    coefficients are updated every `block` samples."""
    if np.ndim(fc) == 0 and np.ndim(q) == 0:
        b, a = _biquad(kind, fc, q)
        return lfilter(b, a, x)
    n = len(x)
    idx = np.arange(0, n, block)
    fcs = np.broadcast_to(fc, (n,))[idx]
    qs = np.broadcast_to(q, (n,))[idx]
    B, A = _biquad(kind, fcs, qs)
    y = np.empty(n)
    zi = np.zeros(2)
    for i, s0 in enumerate(idx):
        y[s0:s0 + block], zi = lfilter(B[i], A[i], x[s0:s0 + block], zi=zi)
    return y


def lp4(x, fc, res=0.707, block=32):
    """24 dB/oct resonant lowpass (two cascaded biquads)."""
    return filt(filt(x, "lp", fc, 0.54, block), "lp", fc, res, block)


def sos(kind, fc, order=2):
    return butter(order, fc, btype={"lp": "low", "hp": "high", "bp": "band"}[kind], fs=SR, output="sos")


def static(x, kind, fc, order=2):
    return sosfilt(sos(kind, fc, order), x, axis=0)


# ---------------------------------------------------------------- effects

def drive(x, amt):
    if amt <= 0:
        return x
    return np.tanh(x * amt) / np.tanh(amt)


def crush(x, bits=8, down=1):
    q = 2.0 ** (bits - 1)
    y = np.round(x * q) / q
    if down > 1:
        y = np.repeat(y[::down], down)[: len(x)]
    return y


def pan(x, p):
    """Constant-power pan of a mono signal, p in [-1, 1] -> (n, 2)."""
    a = (np.clip(p, -1, 1) + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=1)


def pingpong(x, delay_s, fb=0.45, damp=3500.0):
    """Ping-pong delay, returns the wet stereo signal. x: (n, 2)."""
    n = len(x)
    D = max(int(delay_s * SR), 1)
    mono = x.mean(axis=1)
    yl = np.zeros(n); yr = np.zeros(n)
    b, a = _biquad("lp", damp, 0.6)
    zl = np.zeros(2); zr = np.zeros(2)
    for k in range(D, n, D):
        e = min(k + D, n)
        m = e - k
        src_in = mono[k - D:k - D + m]
        fb_l = fb * yr[k - D:k - D + m]
        fb_r = fb * yl[k - D:k - D + m]
        yl[k:e], zl = lfilter(b, a, src_in + fb_l, zi=zl)
        yr[k:e], zr = lfilter(b, a, fb_r, zi=zr)
    return np.stack([yl, yr], axis=1)


def chorus(x, base_ms=11.0, depth_ms=3.5, rate=0.45, mix=0.55):
    """Stereo chorus: modulated fractional delay, opposite LFO phase per side."""
    n = len(x)
    t = np.arange(n) / SR
    idx = np.arange(n, dtype=np.float64)
    out = np.empty_like(x)
    for c, ph in ((0, 0.0), (1, np.pi * 0.66)):
        d = (base_ms + depth_ms * np.sin(2 * np.pi * rate * t + ph)) * SR / 1000
        wet = np.interp(idx - d, idx, x[:, c])
        out[:, c] = x[:, c] * (1 - mix * 0.4) + wet * mix
    return out


def make_ir(rt60=2.5, rng=None, predelay=0.012, bright=6000.0, dark=1800.0):
    rng = rng or np.random.default_rng(7)
    n = int((rt60 * 1.1 + predelay) * SR)
    t = secs(n)
    ir = np.zeros((n, 2))
    p = int(predelay * SR)
    for ch in range(2):
        nz = rng.standard_normal(n)
        hi = static(nz, "lp", bright) * np.exp(-t * 6.9 / (rt60 * 0.45))
        lo = static(nz, "lp", dark) * np.exp(-t * 6.9 / rt60)
        sig = hi + lo
        sig[:p] = 0
        ir[:, ch] = sig
    # early reflections
    for _ in range(14):
        d = p + rng.integers(int(0.003 * SR), int(0.08 * SR))
        ir[d, rng.integers(0, 2)] += rng.uniform(0.3, 1.0) * rng.choice([-1, 1]) * 4
    ir = static(ir, "hp", 180)
    ir /= np.sqrt((ir ** 2).sum() / 2)
    return ir


def reverb(x, ir):
    n = len(x)
    return np.stack([oaconvolve(x[:, c], ir[:, c])[:n] for c in range(2)], axis=1)


def sidechain_env(n, hits, depth, release_s, attack_s=0.004):
    env = np.ones(n)
    L = int(release_s * SR)
    A = max(int(attack_s * SR), 1)
    t = np.arange(L) / L
    curve = 1.0 - depth * (1.0 - t) ** 2
    curve[:A] = np.minimum(curve[:A], 1.0 - depth * np.linspace(0, 1, A))
    for h in hits:
        e = min(h + L, n)
        if h < n:
            env[h:e] = np.minimum(env[h:e], curve[: e - h])
    return env


# ---------------------------------------------------------------- mastering

def limiter(x, ceiling=0.93, look_s=0.004, release_s=0.08):
    peak = np.abs(x).max(axis=1)
    W = int(look_s * SR) | 1
    env = maximum_filter1d(peak, W)
    g = np.minimum(1.0, ceiling / np.maximum(env, 1e-9))
    g = minimum_filter1d(g, W)
    g = uniform_filter1d(g, W)
    # slower release: one-pole smoothing that only lets gain recover slowly
    a = np.exp(-1.0 / (release_s * SR))
    g_rel = lfilter([1 - a], [1, -a], g - 1.0) + 1.0
    g = np.minimum(g, g_rel)
    y = x * g[:, None]
    return np.clip(y, -ceiling, ceiling)


def master(x, target_rms_db=-10.5):
    x = static(x, "hp", 28, order=2)
    body = x[int(len(x) * 0.2): int(len(x) * 0.8)]
    rms = np.sqrt(np.mean(body ** 2)) + 1e-12
    x = x * (10 ** (target_rms_db / 20) / rms)
    x = np.tanh(x * 0.9) / 0.9 * 0.5 + x * 0.5  # gentle glue saturation
    return limiter(x)


def to_int16(x, rng=None):
    rng = rng or np.random.default_rng(0)
    d = (rng.random(x.shape) - rng.random(x.shape)) / 32768.0
    return np.clip((x + d) * 32767, -32768, 32767).astype(np.int16)


def melt(x, depth_ms, seed=0, base_ms=9.0):
    """Psychedelic 'melting' pitch wobble: slowly wandering fractional delay.
    depth_ms: scalar or per-sample array (0 = untouched)."""
    n = len(x)
    rng = np.random.default_rng(seed)
    t = np.arange(n) / SR
    idx = np.arange(n, dtype=np.float64)
    out = np.empty_like(x)
    for c in range(2):
        r = rng.uniform(0.07, 0.25, 3)
        p = rng.uniform(0, 6.3, 3)
        lfo = (np.sin(2 * np.pi * r[0] * t + p[0]) + 0.6 * np.sin(2 * np.pi * r[1] * t + p[1])
               + 0.35 * np.sin(2 * np.pi * r[2] * t + p[2])) / 1.95
        d = (base_ms + np.asarray(depth_ms) * lfo) * SR / 1000
        out[:, c] = np.interp(idx - d, idx, x[:, c])
    return out


def phaser(x, rate=0.11, mix=0.6, seed=0):
    """Swirl: two swept notches, opposite phase per side."""
    n = len(x)
    t = np.arange(n) / SR
    out = np.empty_like(x)
    for c, ph in ((0, 0.0), (1, np.pi)):
        fc1 = 300 * 2 ** (2.2 * (0.5 + 0.5 * np.sin(2 * np.pi * rate * t + ph)))
        y = x[:, c] - mix * filt(x[:, c], "bp", fc1, 1.8, 256)
        y = y - mix * 0.7 * filt(y, "bp", fc1 * 2.7, 2.2, 256)
        out[:, c] = y
    return out
