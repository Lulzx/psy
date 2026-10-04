"""Low-level DSP: oscillators, envelopes, filters, effects, mastering."""
import numpy as np
from itertools import product
from scipy.linalg import hadamard
from scipy.signal import lfilter, butter, sosfilt, oaconvolve, resample_poly
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

def drive(x, amt, os=2):
    """tanh saturation, oversampled so the new harmonics do not fold back as
    inharmonic aliases (part of the 'artificial' edge of naive distortion)."""
    if amt <= 0:
        return x
    if os > 1 and len(x) > 64:
        up = np.tanh(resample_poly(x, os, 1, axis=0) * amt) / np.tanh(amt)
        return resample_poly(up, 1, os, axis=0)[: len(x)]
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


def room_ir(rt60=0.7, predelay=0.009, seed=0):
    """Sparse lateral reflections followed by a gradually diffusing dark tail.
    Shape (samples, output, input); every source reaches both ears/channels.
    The late component is an offline approximation, not a room measurement."""
    rng = np.random.default_rng(seed)
    n = int((rt60 * 1.2 + predelay + 0.1) * SR)
    t = secs(n)
    ir = np.zeros((n, 2, 2))
    late_t = np.maximum(t - predelay - 0.025, 0)
    ramp = (1 - np.exp(-late_t / 0.035)) ** 2
    for source in range(2):
        for ear in range(2):
            tail = static(rng.standard_normal(n), "lp", 2600)
            tail *= ramp * np.exp(-late_t * 6.9 / rt60)
            tail /= max(np.linalg.norm(tail), 1e-12)
            late_level = 0.7 if rt60 > 1.0 else 0.22
            ir[:, ear, source] = tail * late_level * (1.0 if ear == source else 0.86)
            # A stable stage: mirrored geometry, irregular wall path lengths.
            for j, ms in enumerate((7, 17, 29, 43, 61, 83)):
                delay = predelay + (ms + (3 if ear != source else 0)) / 1000
                k = int(delay * SR)
                if k < n:
                    ir[k, ear, source] += (0.55 if ear == source else 0.38) * 0.72 ** j
    for source in range(2):
        ir[:, :, source] /= np.sqrt(np.sum(ir[:, :, source] ** 2))
    return ir


def spatial_reverb(x, ir):
    """True stereo convolution, including opposite-channel reflections."""
    out = np.zeros_like(x)
    for ear in range(2):
        for source in range(2):
            out[:, ear] += oaconvolve(x[:, source], ir[:, ear, source])[:len(x)]
    return out


def stereo_width(x, amount=1.5, crossover=300):
    """Increase existing side detail above a crossover; preserve the mono sum.
    No phase inversion of the direct signal and no widening of the sub bass."""
    mid = x.mean(axis=1)
    side = (x[:, 0] - x[:, 1]) * 0.5
    side = side + (amount - 1) * static(side, "hp", crossover)
    return np.stack([mid + side, mid - side], axis=1)


def tempo_echo(x, bar_times, feedback=0.43, taps=5):
    """Dotted-eighth echoes on a continuous beat map, preserving source position.
    Subsequent echoes alternate channels; finite taps bound CPU and tail length."""
    out = np.zeros_like(x)
    bar_times = np.asarray(bar_times)
    beats = np.arange(len(bar_times)) * 4.0
    # Extend the last tempo into the render tail.
    end = max(len(x) / SR, bar_times[-1] + 0.01)
    beat_end = beats[-1] + (end - bar_times[-1]) * 4 / (bar_times[-1] - bar_times[-2])
    times = np.append(bar_times, end)
    grid = np.append(beats, beat_end)
    wet = x.copy()
    for tap in range(1, taps + 1):
        wet = static(wet, "lp", 2900)
        # Chunk interpolation to avoid multiple song-sized automation arrays.
        for s in range(0, len(x), 262144):
            e = min(s + 262144, len(x))
            t = np.arange(s, e) / SR
            b = np.interp(t, times, grid) - 0.75 * tap
            source_t = np.interp(b, grid, times)
            source_idx = source_t * SR
            i = np.minimum(source_idx.astype(np.int64), len(x) - 1)
            j = np.minimum(i + 1, len(x) - 1)
            f = source_idx - i
            for ch in range(2):
                src = ch if tap % 2 else 1 - ch
                y = wet[i, src] * (1 - f) + wet[j, src] * f
                out[s:e, ch] += np.where(b >= 0, y, 0) * feedback ** (tap - 1)
    return out


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


# ---------------------------------------------------------------- organic motion

def wander(n, rate, rng, octaves=3):
    """Smooth random motion (roughly -1..1), 1/f-weighted across `octaves` rates
    starting at `rate` Hz. A natural replacement for sine LFOs: players and
    analog circuits drift, they do not oscillate."""
    out = np.zeros(n)
    total = 0.0
    u = np.arange(n) / SR
    for k in range(octaves):
        r = rate * 2 ** k
        m = int(n / SR * r) + 3
        pts = rng.standard_normal(m)
        x = u * r
        i = np.minimum(x.astype(np.int64), m - 2)
        w = (1 - np.cos(np.pi * (x - i))) / 2
        out += (pts[i] * (1 - w) + pts[i + 1] * w) * 0.6 ** k
        total += 0.6 ** k
    return out / total


# ---------------------------------------------------------------- EQ + loudness

def _rbj(kind, fc, gain_db, q):
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * fc / SR
    c, s = np.cos(w0), np.sin(w0)
    al = s / (2 * q)
    if kind == "peak":
        b = [1 + al * A, -2 * c, 1 - al * A]
        a = [1 + al / A, -2 * c, 1 - al / A]
    else:  # high/low shelf
        sq = 2 * np.sqrt(A) * al
        if kind == "hs":
            b = [A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq)]
            a = [(A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq]
        else:
            b = [A * ((A + 1) - (A - 1) * c + sq), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sq)]
            a = [(A + 1) + (A - 1) * c + sq, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sq]
    return np.array(b) / a[0], np.array(a) / a[0]


def eq(x, kind, fc, gain_db, q=0.707):
    """Static RBJ EQ: kind = peak | hs (high shelf) | ls (low shelf)."""
    b, a = _rbj(kind, fc, gain_db, q)
    return lfilter(b, a, x, axis=0)


def lufs(x):
    """Integrated loudness (ITU-R BS.1770: K-weighting, 400 ms blocks, gating)."""
    x = np.atleast_2d(x.T).T
    y = eq(x, "hs", 1500, 4.0, 0.707)
    y = static(y, "hp", 38)
    W, H = int(0.4 * SR), int(0.1 * SR)
    if len(y) < W:
        return -70.0
    c = np.cumsum(np.concatenate([np.zeros((1, y.shape[1])), y ** 2]), axis=0)
    st = np.arange(0, len(y) - W + 1, H)
    z = ((c[st + W] - c[st]) / W).sum(axis=1)
    l = -0.691 + 10 * np.log10(z + 1e-20)
    z = z[l > -70]
    if not len(z):
        return -70.0
    rel = -0.691 + 10 * np.log10(z.mean()) - 10
    z = z[-0.691 + 10 * np.log10(z) > rel]
    return float(-0.691 + 10 * np.log10(z.mean()))


# ---------------------------------------------------------------- space

def frac_delay(x, d):
    """Delay by d samples (scalar or per-sample array), linear interpolation."""
    if np.ndim(d) == 0 and d == 0:
        return x
    idx = np.arange(len(x), dtype=np.float64)
    return np.interp(idx - d, idx, x, left=0.0)


def early_ir(az, r, room=(22.0, 18.0, 7.0), absorb=(0.55, 0.35, 1.0), order=2, seed=0):
    """Early reflections (image-source model) of a shoebox space for a source at
    azimuth `az` degrees (0 = front, + = right) and `r` metres, heard by two ears.
    absorb = (walls, floor, ceiling); ceiling 1.0 = open sky. Returns (samples, 2)
    with taps relative to the direct sound (direct = 1, not included)."""
    rng = np.random.default_rng(seed)
    dims = np.array(room)
    lis = np.array([dims[0] * 0.5, dims[1] * 0.38, 1.7])
    th = np.radians(az)
    src = lis + r * np.array([np.sin(th), np.cos(th), 0.0]) + [0, 0, -0.2]
    src = np.clip(src, 0.4, dims - 0.4)
    r0 = np.linalg.norm(src - lis)
    ears = lis + np.array([[-0.09, 0, 0], [0.09, 0, 0]])
    beta = np.sqrt(1 - np.clip(np.array(absorb), 0, 1))
    n = int(0.17 * SR)
    irs = [np.zeros((n, 2)), np.zeros((n, 2))]
    for q in product(range(-order, order + 1), repeat=3):
        o = sum(abs(v) for v in q)
        if o == 0 or o > order:
            continue
        img = np.array([q[a] * dims[a] + (src[a] if q[a] % 2 == 0 else dims[a] - src[a]) for a in range(3)])
        ceil_hits = (q[2] + 1) // 2 if q[2] > 0 else abs(q[2]) // 2
        g = beta[0] ** (abs(q[0]) + abs(q[1])) * beta[2] ** ceil_hits * beta[1] ** (abs(q[2]) - ceil_hits)
        if g < 1e-3:
            continue
        dvec = (img - lis) / np.linalg.norm(img - lis)
        jitter = rng.uniform(-0.0004, 0.0004)  # irregular, diffusing surfaces (trees, rock)
        for e in range(2):
            d = np.linalg.norm(img - ears[e])
            k = max((d - r0) / 343.0 + jitter, 0.0) * SR
            i = int(k)
            if i + 1 >= n:
                continue
            side = dvec[0] if e else -dvec[0]
            amp = g * r0 / d * (0.78 + 0.22 * side) * rng.choice([-1, 1], p=[0.25, 0.75])
            f = k - i
            irs[min(o, 2) - 1][i, e] += amp * (1 - f)
            irs[min(o, 2) - 1][i + 1, e] += amp * f
    return static(irs[0], "lp", 5500) + static(irs[1], "lp", 2800)


def stage(x, az, dist, width=1.0, room=None, er_level=0.6, seed=0):
    """Place a stereo bus on a stage. az: degrees, scalar or per-sample (moving
    source); dist: 0 (close) .. 1 (far). The bus centre gets interaural time and
    level differences plus head shadow; distance darkens and lowers the direct
    sound, narrows it, and lets the room's early reflections take over."""
    n = len(x)
    m = x.mean(axis=1)
    s = (x[:, 0] - x[:, 1]) * 0.5 * width * (1 - 0.45 * dist)
    p = np.sin(np.radians(az))
    m_lo = static(m, "lp", 1400)
    m_hi = m - m_lo
    mL = m_lo + m_hi * (1 - 0.55 * np.clip(p, 0, 1))
    mR = m_lo + m_hi * (1 - 0.55 * np.clip(-p, 0, 1))
    itd = 0.00066 * p * SR
    a = (0.75 * p + 1) * np.pi / 4
    L = frac_delay(mL, np.maximum(itd, 0)) * np.cos(a) * np.sqrt(2) + s
    R = frac_delay(mR, np.maximum(-itd, 0)) * np.sin(a) * np.sqrt(2) - s
    out = np.stack([L, R], axis=1)
    if dist > 0.05:
        out = static(out, "lp", 16000 * 2 ** (-2.6 * dist))
    out *= 1 / (1 + 0.9 * dist)
    if room is not None:
        ir = early_ir(float(np.mean(az)), 1.0 + 9.0 * dist, seed=seed, **room)
        er = np.stack([oaconvolve(m, ir[:, e])[:n] for e in range(2)], axis=1)
        out += er * er_level / (1 + 0.9 * dist)
    return out


def _velvet(n, rng, density=2200.0, decay=0.012):
    v = np.zeros(n)
    k = int(n / SR * density)
    pos = rng.integers(0, n, k)
    v[pos] = rng.choice([-1.0, 1.0], k) * np.exp(-pos / SR / decay)
    return v / np.sqrt((v ** 2).sum())


def fdn_reverb(x, rt60=2.8, hf_ratio=0.45, size=1.0, predelay=0.025, mod_ms=0.35, seed=0):
    """8-line feedback delay network: dense, slowly modulated (alive, never
    metallic) tail with frequency-dependent decay (highs die hf_ratio times
    faster). x: (n, 2) -> wet (n, 2), unit energy per input channel."""
    rng = np.random.default_rng(seed)
    N = 8
    lens = (np.array([31.3, 37.9, 41.3, 47.9, 53.1, 61.7, 67.3, 79.1]) * size * SR / 1000).astype(int)
    md = mod_ms * SR / 1000
    H = hadamard(N) / np.sqrt(N)
    g = 10 ** (-3 * lens / (rt60 * SR))
    b = np.log(10) / 4 * np.log10(g) * (1 - 1 / hf_ratio ** 2)
    c0 = g * (1 - b)
    rates = rng.uniform(0.06, 0.3, N)
    phs = rng.uniform(0, 2 * np.pi, N)
    sgn = rng.choice([-1.0, 1.0], N)
    cL, cR = hadamard(N)[1] / N, hadamard(N)[2] / N
    B = int(lens.min() - md - 2)
    Lb = 1 << int(np.ceil(np.log2(lens.max() + md + B + 4)))
    rows = np.arange(N)[:, None]

    def run(xin):
        n = len(xin)
        buf = np.zeros((N, Lb))
        zi = np.zeros(N)
        out = np.zeros((n, 2))
        for start in range(0, n, B):
            m = min(B, n - start)
            t = start + np.arange(m)
            d = lens[:, None] + md * (1 + np.sin(2 * np.pi * rates[:, None] * t / SR + phs[:, None])) / 2
            rp = t[None, :] - d
            i0 = np.floor(rp).astype(np.int64)
            f = rp - i0
            o = buf[rows, i0 % Lb] * (1 - f) + buf[rows, (i0 + 1) % Lb] * f
            for i in range(N):
                o[i], z = lfilter([c0[i]], [1, -b[i]], o[i], zi=zi[i:i + 1])
                zi[i] = z[0]
            out[start:start + m, 0] = cL @ o
            out[start:start + m, 1] = cR @ o
            fb = H @ o
            fb[0::2] += xin[start:start + m, 0] * sgn[0::2, None]
            fb[1::2] += xin[start:start + m, 1] * sgn[1::2, None]
            buf[:, t % Lb] = fb
        return out

    vel = np.stack([_velvet(int(0.04 * SR), rng) for _ in range(2)], axis=1)
    pre = int(predelay * SR)

    def feed(y):
        d = np.stack([oaconvolve(y[:, c], vel[:, c])[:len(y)] for c in range(2)], axis=1)
        return np.concatenate([np.zeros((pre, 2)), d])[:len(y)]

    imp = np.zeros((int((rt60 * 1.5 + predelay) * SR), 2))
    imp[0] = 1.0
    ir = run(feed(imp))
    norm = np.sqrt((ir ** 2).sum() / 2)
    return run(feed(x)) / max(norm, 1e-12)


# ---------------------------------------------------------------- bus glue

def glue(x, thresh_db, ratio=2.0, attack=0.03, release=0.25, knee=6.0):
    """Slow RMS bus compressor that holds a mix together instead of squashing it."""
    blk = 44
    nb = len(x) // blk + 1
    p = np.pad((x ** 2).mean(axis=1), (0, nb * blk - len(x)))
    lev = 10 * np.log10(p.reshape(nb, blk).mean(axis=1) + 1e-12)
    a = np.exp(-blk / (0.01 * SR))
    lev = lfilter([1 - a], [1, -a], lev)  # 10 ms RMS detector
    over = lev - thresh_db
    gr = np.where(over <= -knee / 2, 0.0,
                  np.where(over >= knee / 2, over * (1 / ratio - 1),
                           (1 / ratio - 1) * (over + knee / 2) ** 2 / (2 * knee)))
    ka, kr = np.exp(-blk / (attack * SR)), np.exp(-blk / (release * SR))
    sm = np.empty(nb)
    g = 0.0
    for i, v in enumerate(gr):
        g = ka * g + (1 - ka) * v if v < g else kr * g + (1 - kr) * v
        sm[i] = g
    gain = np.interp(np.arange(len(x)), np.arange(nb) * blk + blk / 2, 10 ** (sm / 20))
    return x * gain[:, None]


def master_glue(x, target_lufs=-9.0, glue_db=2.0, low_dip_db=-1.5):
    """Master chain: rumble HP, gentle low-end dip (clears the low mids), slow
    glue compression, oversampled soft saturation, loudness-matched limiting."""
    x = static(x, "hp", 28, order=2)
    if low_dip_db:
        x = eq(x, "peak", 68, low_dip_db, 0.8)
    x = x * 10 ** ((target_lufs - lufs(x)) / 20)
    lv = 10 * np.log10((x ** 2).mean(axis=1) + 1e-12)
    loud = np.percentile(uniform_filter1d(lv, int(0.4 * SR))[::4410], 90)
    x = glue(x, loud - glue_db * 2.0, ratio=2.0)
    up = resample_poly(x, 2, 1, axis=0)
    up = np.tanh(up * 0.9 + 0.04) / 0.9 * 0.5 + up * 0.5  # slight asymmetry = even (warm) harmonics
    x = static(resample_poly(up, 1, 2, axis=0)[: len(x)], "hp", 12)
    for _ in range(2):
        x = x * 10 ** ((target_lufs - lufs(limiter(x))) / 20)
    return limiter(x)
