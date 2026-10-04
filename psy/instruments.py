"""Synthesized instruments. Each returns a mono (n,) or stereo (n, 2) float array."""
import numpy as np
from .dsp import (SR, secs, saw, pulse, sine, noise, adsr, fade_edges, filt, lp4,
                  static, drive, crush, midi_hz, pan, phasor, wander)


# ---------------------------------------------------------------- drums

def kick(root_hz, p, rng):
    """Psy kick: pitch-swept sine, tail tuned to the key, short and punchy."""
    L = p["len"]
    n = int((L + 0.01) * SR)
    t = secs(n)
    f_end = root_hz * p.get("tune", 1.0)
    f = f_end + (p.get("f0", 180) - f_end) * np.exp(-t / p.get("pdecay", 0.03)) \
        + 1400 * np.exp(-t / 0.0018)
    body = sine(f, n)
    amp = np.clip((L - t) / (L * p.get("tail", 0.35)), 0, 1) ** 1.6
    amp *= 0.85 + 0.15 * np.exp(-t / 0.04)
    amp[: int(0.0008 * SR)] *= np.linspace(0, 1, int(0.0008 * SR))
    click = static(noise(n, rng), "hp", 2500) * np.exp(-t / 0.0015) * p.get("click", 0.35)
    out = drive(body * amp + click, p.get("drive", 1.8))
    return fade_edges(out, 0.0003, 0.003)


def hat(rng, decay=0.03, hp=8000, metal=0.35):
    n = int(decay * 6 * SR)
    t = secs(n)
    nz = noise(n, rng)
    ratios = [1.0, 1.4471, 1.6170, 1.9265, 2.5028, 2.6637]
    m = sum(pulse(330 * r, n, 0.5, rng.random()) for r in ratios) / 6
    x = static(nz * (1 - metal) + m * metal, "hp", hp, order=4)
    return fade_edges(x * np.exp(-t / decay))


def ride(rng):
    x = hat(rng, decay=0.16, hp=6500, metal=0.6)
    return filt(x, "bp", 9500, 0.8) * 2.5 + x * 0.3


def clap(rng, tone=1200, decay=0.12):
    n = int((decay * 5 + 0.03) * SR)
    t = secs(n)
    env = np.where(t >= 0.018, np.exp(-(t - 0.018) / decay), 0.0)
    for o in (0.0, 0.009):
        env = np.maximum(env, np.where(t >= o, np.exp(-np.maximum(t - o, 0) / 0.004), 0.0))
    x = filt(noise(n, rng), "bp", tone, 1.2) * env
    return fade_edges(x * 2.5)


def snare(rng, pitch=1.0, decay=0.09):
    n = int(decay * 5 * SR)
    t = secs(n)
    f = (190 * pitch) + 120 * np.exp(-t / 0.01)
    body = sine(f, n) * np.exp(-t / (decay * 0.6))
    nz = static(noise(n, rng), "hp", 1800) * np.exp(-t / decay)
    return fade_edges(drive(body * 0.7 + nz * 0.8, 1.5))


def perc(rng, f=420, decay=0.05, kind="tom"):
    n = int(decay * 6 * SR)
    t = secs(n)
    if kind == "tom":
        x = sine(f * (1 + 1.5 * np.exp(-t / 0.008)), n)
    elif kind == "click":
        x = sine(f * 4, n) * 0.5 + filt(noise(n, rng), "bp", 3000, 1.0) * 0.5
        decay *= 0.25
    else:  # 'fm' blip
        x = sine(f + 3 * f * sine(f * 2.01, n) * np.exp(-t / 0.01), n)
    return fade_edges(x * np.exp(-t / decay))


# ---------------------------------------------------------------- bass

def bass_note(hz, dur, p):
    """Filtered-envelope saw bass note (the 'B' in K-B-B-B)."""
    rel = 0.006
    n = int((dur + rel) * SR)
    t = secs(n)
    w = p.get("wave", "saw")
    osc = saw(hz, n) if w == "saw" else pulse(hz, n, 0.5)
    fc = p["base"] + (p["peak"] - p["base"]) * np.exp(-t / p["env_decay"])
    y = lp4(osc, fc, p.get("res", 1.0), block=16)
    y = y + sine(hz, n) * p.get("sub_lvl", 0.5)
    amp = adsr(n, 0.0015, p.get("amp_decay", 0.25), p.get("sustain", 0.6), rel, dur)
    y = drive(y * amp, p.get("drive", 1.5))
    return fade_edges(y, 0.0008, 0.004)


def sub_note(hz, dur):
    n = int((dur + 0.02) * SR)
    y = sine(hz, n) + 0.15 * sine(hz * 2, n)
    return fade_edges(drive(y * adsr(n, 0.01, 0.5, 0.8, 0.02, dur), 1.2), 0.01, 0.02)


# ---------------------------------------------------------------- acid line

def acid_line(steps, n_total, step_len, root_midi, cutoff, p, rng):
    """Monophonic 303-style line. `steps` is a callable i -> step dict|None,
    `cutoff` a per-sample base cutoff array (Hz). Returns mono."""
    n_steps = int(np.ceil(n_total / step_len))
    logf = np.zeros(n_total)
    amp = np.zeros(n_total)
    env = np.zeros(n_total)
    acc = np.zeros(n_total)
    prev = None
    cur_f = None
    for i in range(n_steps):
        s0 = int(i * step_len)
        s1 = min(int((i + 1) * step_len), n_total)
        m = s1 - s0
        if m <= 0:
            break
        st = steps(i)
        if st is None:
            if cur_f is not None:
                logf[s0:s1] = cur_f
            prev = None
            continue
        target = np.log2(midi_hz(root_midi + st["semi"]))
        tt = np.arange(m) / SR
        sliding_in = prev is not None and prev.get("slide") and cur_f is not None
        gate = m if st.get("slide") else int(m * p.get("gate", 0.55))
        a = np.ones(m)
        if not sliding_in:
            k = min(int(0.002 * SR), m)
            a[:k] = np.linspace(0, 1, k)
        a[gate:] = 0
        r = max(0, min(int(0.006 * SR), m - gate))
        a[gate:gate + r] = np.linspace(1, 0, r)
        amp[s0:s1] = a
        if sliding_in:
            # legato: glide pitch, keep filter envelope running
            logf[s0:s1] = target + (cur_f - target) * np.exp(-tt / 0.035)
            env[s0:s1] = env[s0 - 1] * np.exp(-tt / p["decay"])
            acc[s0:s1] = acc[s0 - 1]
        else:
            logf[s0:s1] = target
            dec = p["decay"] * (0.55 if st["accent"] else 1.0)
            env[s0:s1] = np.exp(-tt / dec)
            acc[s0:s1] = 1.0 if st["accent"] else 0.0
        cur_f = target
        prev = st
    freq = 2.0 ** logf
    amp = filt(amp, "lp", 600, 0.7)  # de-click
    w = p.get("wave", "saw")
    osc = saw(freq, n_total) if w == "saw" else pulse(freq, n_total, 0.5)
    fc = cutoff * 2.0 ** (env * (p["envmod"] + acc * p.get("accent_mod", 1.5)))
    y = lp4(osc, np.minimum(fc, 16000), p.get("res", 6.0), block=32)
    y = drive(y * 1.4, p.get("drive", 2.0))
    return y * amp * (1 + 0.35 * acc)


# ---------------------------------------------------------------- leads

def supersaw(midi, dur, p, rng):
    n = int((dur + p.get("rel", 0.08)) * SR)
    hz = midi_hz(midi)
    voices = p.get("voices", 7)
    spread = p.get("detune", 0.18)
    L = np.zeros(n); R = np.zeros(n)
    t = secs(n)
    rate = 5.5 * (1 + 0.05 * wander(n, 0.7, rng))
    vib = 1 + 0.003 * np.sin(2 * np.pi * np.cumsum(rate) / SR + rng.uniform(0, 6.3)) * np.clip(t / 0.3, 0, 1)
    for v in range(voices):
        d = (v / (voices - 1) - 0.5) * 2 * spread if voices > 1 else 0
        drift = 2 ** (0.035 * wander(n, 0.25, rng, 2) / 12)  # each voice its own slow analog drift
        x = saw(hz * 2 ** (d / 12) * vib * drift, n, rng.random())
        if v % 2:
            L += x * 0.8; R += x * 0.4
        else:
            R += x * 0.8; L += x * 0.4
    fc = p.get("base", 1500) + p.get("peak", 6000) * np.exp(-t / p.get("env_decay", 0.12))
    amp = adsr(n, p.get("att", 0.004), p.get("dec", 0.2), p.get("sus", 0.6), p.get("rel", 0.08), dur)
    out = np.stack([lp4(L, fc, 1.0, 64), lp4(R, fc, 1.0, 64)], axis=1) / voices
    return out * amp[:, None]


def reso_lead(midi, dur, p, rng):
    """Squelchy Goa lead: pulse + saw through resonant filter, vibrato."""
    n = int((dur + 0.06) * SR)
    t = secs(n)
    hz = midi_hz(midi) * (1 + 0.004 * np.sin(2 * np.pi * 6 * t) * np.clip(t / 0.15, 0, 1))
    x = 0.6 * saw(hz, n) + 0.5 * pulse(hz * 1.004, n, 0.3)
    fc = 500 + p.get("peak", 5000) * np.exp(-t / p.get("env_decay", 0.09))
    y = drive(lp4(x, fc, p.get("res", 4.0), 32), 1.6)
    amp = adsr(n, 0.003, 0.15, 0.7, 0.05, dur)
    y = y * amp
    return np.stack([y, np.roll(y, int(0.007 * SR))], axis=1)


def fm_pluck(midi, dur, p, rng):
    n = int((dur + p.get("decay", 0.18) * 3) * SR)
    t = secs(n)
    hz = midi_hz(midi)
    idx = p.get("index", 3.0) * np.exp(-t / p.get("idecay", 0.04))
    mod = sine(hz * p.get("ratio", 2.0), n) * idx * hz
    y = sine(hz + mod, n) * np.exp(-t / p.get("decay", 0.18))
    return fade_edges(y, 0.001, 0.01)


def alien(dur, rng, base=90.0):
    """Talking, formant-swept squelch (dark/forest 'lead')."""
    n = int(dur * SR)
    t = secs(n)
    hz = base * 2 ** (rng.integers(0, 12) / 12)
    x = saw(hz, n) + pulse(hz * 0.5, n, 0.25) * 0.6
    k = int(rng.integers(3, 9))
    pts = rng.uniform(np.log2(300), np.log2(3500), k + 1)
    fc = 2 ** np.interp(t, np.linspace(0, dur, k + 1), pts)
    y = filt(x, "bp", fc, 7.0, 32) * 3 + lp4(x, fc * 0.7, 3.0, 32) * 0.6
    amp = adsr(n, 0.01, 0.4, 0.8, 0.05, dur - 0.05)
    return drive(y * amp, 2.0)


def pad_chord(midis, dur, p, rng):
    rel = p.get("rel", 1.6)
    n = int((dur + rel) * SR)
    t = secs(n)
    L = np.zeros(n); R = np.zeros(n)
    for m in midis:
        for v in range(p.get("voices", 3)):
            d = rng.uniform(-0.12, 0.12)
            drift = 2 ** (0.05 * wander(n, 0.15, rng, 2) / 12)
            x = saw(midi_hz(m) * 2 ** (d / 12) * drift, n, rng.random())
            pp = rng.uniform(-0.8, 0.8)
            L += x * (1 - pp) / 2; R += x * (1 + pp) / 2
    lfo = p.get("fc", 1400) * 2 ** (0.6 * wander(n, 1 / p.get("lfo", 6.0), rng, 2))
    lfo2 = lfo * 2 ** (0.15 * wander(n, 0.3, rng, 1))  # the sides breathe slightly apart
    out = np.stack([lp4(L, lfo, 1.2, 256), lp4(R, lfo2, 1.2, 256)], axis=1)
    amp = adsr(n, p.get("att", 1.2), 2.0, 0.85, rel, dur)
    return out * amp[:, None] / (len(midis) * 2)


# ---------------------------------------------------------------- fx

def riser(dur, rng):
    n = int(dur * SR)
    t = secs(n)
    x = t / dur
    fc = 300 * 2 ** (x * 5.2)
    L = filt(noise(n, rng), "bp", fc, 1.4, 64)
    R = filt(noise(n, rng), "bp", fc * 1.05, 1.4, 64)
    tone = saw(80 * 2 ** (x * 3.5), n) * 0.15
    tone = filt(tone, "lp", fc * 1.5, 2.0, 64)
    amp = x ** 2.2
    return np.stack([(L + tone) * amp, (R + tone) * amp], axis=1) * 1.6


def downlifter(dur, rng):
    n = int(dur * SR)
    t = secs(n)
    fc = 9000 * 2 ** (-t / dur * 5.5)
    L = filt(noise(n, rng), "lp", fc, 2.0, 64)
    R = filt(noise(n, rng), "lp", fc, 2.0, 64)
    amp = np.exp(-t / (dur * 0.35))
    return np.stack([L * amp, R * amp], axis=1)


def impact(rng):
    n = int(2.5 * SR)
    t = secs(n)
    boom = sine(30 + 70 * np.exp(-t / 0.08), n) * np.exp(-t / 0.7)
    nz = static(noise(n, rng), "lp", 3000) * np.exp(-t / 0.25) * 0.5
    return fade_edges(drive(boom + nz, 1.5), 0.0005, 0.2)


def zap(rng):
    dur = rng.uniform(0.12, 0.45)
    n = int(dur * SR)
    t = secs(n)
    f0, f1 = rng.uniform(600, 2200), rng.uniform(30, 90)
    f = f1 + (f0 - f1) * np.exp(-t / (dur * 0.18))
    y = lp4(saw(f, n), np.minimum(f * 3, 4500), 3.0, 32)
    return fade_edges(drive(y * np.exp(-t / (dur * 0.5)), 2.0), 0.0005, 0.01)


def laser(rng):
    dur = rng.uniform(0.25, 0.6)
    n = int(dur * SR)
    t = secs(n)
    f = 4000 * np.exp(-t / (dur * 0.25)) + 200
    y = sine(f + f * 2 * sine(f * 0.51, n), n)
    return fade_edges(y * np.exp(-t / (dur * 0.4)), 0.0005, 0.01)


def bubbles(rng):
    dur = rng.uniform(0.6, 1.4)
    n = int(dur * SR)
    out = np.zeros(n)
    for _ in range(int(rng.integers(6, 16))):
        d = rng.uniform(0.02, 0.07)
        m = int(d * SR)
        s = int(rng.integers(0, n - m))
        tt = secs(m)
        f = rng.uniform(300, 900) * 2 ** (tt / d * rng.uniform(1.0, 2.5))
        out[s:s + m] += sine(f, m) * np.sin(np.pi * tt / d) * rng.uniform(0.4, 1)
    return out


def gurgle(rng):
    dur = rng.uniform(0.4, 1.0)
    n = int(dur * SR)
    t = secs(n)
    rate = rng.uniform(12, 30)
    sh = rng.uniform(120, 700, int(dur * rate) + 2)
    f = np.repeat(sh, int(SR / rate) + 1)[:n]
    f = filt(f, "lp", 40, 0.7)
    y = sine(f + f * 1.5 * sine(f * 1.5, n), n)
    return fade_edges(drive(y * np.exp(-t / (dur * 0.6)), 1.5), 0.005, 0.02)


def stutter(rng, step):
    """Hi-tech style rapid 32nd/64th zap burst."""
    k = int(rng.choice([8, 12, 16]))
    unit = zap(rng)[: int(step * SR * 0.9)]
    n = int(step * SR * k)
    out = np.zeros(n)
    for i in range(k):
        s = int(i * step * SR)
        seg = unit * (0.5 + 0.5 * i / k)
        out[s:s + len(seg)] += seg[: n - s]
    return crush(out, 6, 2)


def blip(rng):
    p = dict(index=rng.uniform(2, 8), ratio=float(rng.choice([1.5, 2.0, 3.5, 7.0])),
             decay=rng.uniform(0.04, 0.12))
    return fm_pluck(int(rng.integers(72, 96)), 0.05, p, rng)


FX = dict(zap=zap, laser=laser, bubbles=bubbles, gurgle=gurgle, blip=blip,
          alien=lambda rng: alien(rng.uniform(0.4, 1.1), rng, base=110))


# ---------------------------------------------------------------- twisted / tribal extras

VOWELS = dict(a=[(800, 1.0), (1150, 0.5), (2900, 0.2)], o=[(450, 1.0), (800, 0.45), (2830, 0.1)],
              e=[(400, 1.0), (1700, 0.4), (2600, 0.25)], i=[(300, 1.0), (2200, 0.3), (3000, 0.2)],
              u=[(325, 1.0), (700, 0.3), (2530, 0.08)])


def glottal(hz, n, oq=0.6):
    """Rosenberg glottal-flow derivative: the pulse real vocal folds radiate,
    soft-cornered instead of a buzzy sawtooth edge."""
    p, _ = phasor(hz, n)
    tp, tn = oq * 0.66, oq * 0.34
    g = np.where(p < tp, 0.5 * (1 - np.cos(np.pi * p / tp)),
                 np.where(p < tp + tn, np.cos(np.pi / 2 * (p - tp) / tn), 0.0))
    d = np.diff(g, prepend=g[0])
    return d / (np.abs(d).max() + 1e-9)


def voice(midi, dur, vowels, rng, singers=3):
    """Formant chant from a small ensemble: glottal-pulse sources with jitter
    (pitch micro-wobble), shimmer (level wobble), breath, slightly staggered
    entries and their own vibrato, through moving vowel formants."""
    rel = 0.35
    n = int((dur + rel) * SR)
    t = secs(n)
    src = np.zeros(n)
    for k in range(singers):
        det = 0.0 if k == 0 else rng.normal(0, 8)
        rate = rng.uniform(4.9, 5.6) * (1 + 0.06 * wander(n, 0.5, rng, 1))
        vib = 0.011 * np.sin(2 * np.pi * np.cumsum(rate) / SR + rng.uniform(0, 6.3)) * np.clip((t - 0.25) / 0.4, 0, 1)
        jit = 0.003 * wander(n, 9.0, rng, 2) + 0.004 * wander(n, 0.4, rng, 1)
        scoop = 2 ** (-0.8 / 12 * np.exp(-t / rng.uniform(0.05, 0.1)))
        hz = midi_hz(midi) * 2 ** (det / 1200) * (1 + vib + jit) * scoop
        x = glottal(hz, n, rng.uniform(0.55, 0.68)) * (1 + 0.1 * wander(n, 7.0, rng, 2))
        x += static(noise(n, rng), "bp", (1000, 3000)) * 0.05  # aspiration
        lag = int(rng.uniform(0, 0.04) * SR) if k else 0
        src[lag:] += x[: n - lag] * (1.0 if k == 0 else 0.7)
    pts = np.linspace(0, dur, len(vowels))
    out = np.zeros(n)
    for k in range(3):
        f = np.interp(t, pts, [VOWELS[v][k][0] for v in vowels])
        g = np.interp(t, pts, [VOWELS[v][k][1] for v in vowels])
        bw = 70 + 0.06 * f
        out += filt(src, "bp", f, f / bw, 128) * g
    amp = adsr(n, 0.09, 0.4, 0.85, rel, dur)
    return drive(out * amp * 4.0 / np.sqrt(singers), 1.3)


def flute(midi, dur, rng):
    rel = 0.15
    n = int((dur + rel) * SR)
    t = secs(n)
    hz = midi_hz(midi) * (1 + 0.006 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.15) / 0.3, 0, 1))
    tone = sine(hz, n) + 0.25 * sine(hz * 2, n) + 0.08 * sine(hz * 3, n)
    breath = filt(noise(n, rng), "bp", midi_hz(midi) * 2, 3.0, 64) * (0.25 + 0.6 * np.exp(-t / 0.05))
    amp = adsr(n, 0.05, 0.3, 0.8, rel, dur)
    return (tone + breath) * amp


def squelch(midi, dur, rng, kind="down"):
    """Twisted full-on riff voice: resonant swept saw/pulse, kind = down|up|wah."""
    n = int((dur + 0.03) * SR)
    t = secs(n)
    hz = midi_hz(midi)
    if kind == "down":
        fc = 220 + 4200 * np.exp(-t / 0.045)
    elif kind == "up":
        fc = 250 * 2 ** (np.clip(t / max(dur, 1e-3), 0, 1) * 4.5)
    else:
        fc = 700 * 2 ** (1.8 * np.sin(np.pi * np.clip(t / max(dur, 1e-3), 0, 1)))
    x = saw(hz * (1 + 0.6 * np.exp(-t / 0.004)), n) + pulse(hz * 1.006, n, 0.25) * 0.6
    y = lp4(x, fc, 7.0, 16) + filt(x, "bp", fc * 1.3, 5.0, 16) * 0.5
    amp = adsr(n, 0.001, 0.09, 0.55, 0.02, dur)
    return drive(y * amp, 2.6)


def tom(hz, decay, rng):
    n = int(decay * 6 * SR)
    t = secs(n)
    body = sine(hz * (1 + 0.7 * np.exp(-t / 0.018)), n)
    skin = static(noise(n, rng), "lp", 1600) * np.exp(-t / 0.012) * 0.35
    return fade_edges(drive((body + skin) * np.exp(-t / decay), 1.4))


def shaker(rng):
    n = int(0.12 * SR)
    t = secs(n)
    env = np.minimum(t / 0.006, 1) * np.exp(-t / 0.03)
    return fade_edges(filt(noise(n, rng), "bp", 6500, 1.4) * env)


def crash(rng, dur=2.6):
    n = int(dur * SR)
    t = secs(n)
    ratios = [1.0, 1.342, 1.783, 2.215, 2.8, 3.41]
    m = sum(pulse(410 * r, n, 0.5, rng.random()) for r in ratios) / 6
    x = static(noise(n, rng) * 0.7 + m * 0.5, "hp", 3800, order=4)
    return fade_edges(x * np.exp(-t / 0.75) * (0.6 + 0.4 * np.exp(-t / 0.05)), 0.0005, 0.1)


def rich_bass(hz, dur, p):
    """Layered rolling bass: clean sub + detuned filtered saw body + mid growl."""
    rel = 0.006
    n = int((dur + rel) * SR)
    t = secs(n)
    amp = adsr(n, 0.0015, p.get("amp_decay", 0.12), p.get("sustain", 0.5), rel, dur)
    sub = sine(hz, n)
    c = p.get("cents", 6)
    ph = p.get("phase", 0.0)
    body = saw(hz * 2 ** (c / 1200), n, ph) + saw(hz * 2 ** (-c / 1200), n, (0.37 + ph * 1.7) % 1)
    if p.get("wave") == "pulse":
        body = body * 0.6 + pulse(hz, n, 0.35) * 0.8
    fc = p["base"] + (p["peak"] - p["base"]) * np.exp(-t / p["env_decay"])
    body = static(lp4(body * 0.6, fc, p.get("res", 1.5), 16), "hp", 85)
    growl = filt(pulse(hz * 2, n, 0.2), "bp", fc * 0.5 + 250, 3.0, 16) * p.get("growl", 0.25)
    y = drive((body * 1.3 + growl) * amp, p.get("drive", 2.0)) + sub * amp * p.get("sub_lvl", 0.6)
    return fade_edges(y, 0.0008, 0.004)


def reese(midi, dur, rng):
    """Sustained detuned-saw bass with a clean sub, for breaks."""
    rel = 1.0
    n = int((dur + rel) * SR)
    t = secs(n)
    hz = midi_hz(midi)
    x = sum(saw(hz * 2 ** (c / 1200), n, rng.random()) for c in (-11, -4, 5, 12)) / 2
    fc = 320 * 2 ** (0.9 * np.sin(2 * np.pi * t / max(dur * 0.8, 0.5)))
    y = drive(lp4(x, fc, 1.6, 128), 1.6) * 0.55 + sine(hz, n) * 0.85
    return y * adsr(n, 0.5, 1.0, 0.9, rel, dur)


def warm_lead(midi, dur, rng):
    """Big but warm lead: 7-voice supersaw + resonant sub-octave layer."""
    p = dict(base=700, peak=3200, env_decay=0.14, dec=0.25, sus=0.7, rel=0.09, detune=0.22, voices=7)
    a = supersaw(midi, dur, p, rng)
    b = reso_lead(midi - 12, dur, dict(peak=2400, env_decay=0.12, res=3.0), rng)
    n = max(len(a), len(b))
    out = np.zeros((n, 2))
    out[: len(a)] += a * 2.2
    out[: len(b)] += b * 0.45
    return out


def ney_phrase(notes, n, rng, expression=1.0, air_amt=1.0):
    """Breathy ney/bansuri line rendered as one continuous breath-driven voice.
    notes: [(start_sample, len_samples, midi, grace)], sorted. Returns mono (n,)."""
    logf = np.full(n, np.nan)
    amp = np.zeros(n)
    trans = np.zeros(n)
    prev_end, prev_lf = -10 ** 9, None
    phrase_t = secs(n)
    # Continuous performer state; it does not reset at each note boundary.
    drift = 0.0035 * expression * wander(n, 0.6, rng)
    vib_rate = rng.uniform(4.4, 5.3) + 0.22 * np.sin(2 * np.pi * 0.31 * phrase_t)
    vib = np.sin(2 * np.pi * np.cumsum(vib_rate) / SR + rng.uniform(0, 6.28))
    pressure = np.zeros(n)
    for s, L, m, grace in notes:
        if s >= n:
            break
        e = min(s + L, n)
        t = np.arange(e - s) / SR
        lf = np.full(e - s, np.log2(midi_hz(m)))
        legato = prev_lf is not None and s - prev_end < int(0.06 * SR)
        if legato:  # glide from the previous note
            lf += (prev_lf - lf[0]) * np.exp(-t / 0.035)
        else:  # breathy scoop up into the note
            lf -= (1.0 / 12) * np.exp(-t / 0.05)
        if grace:  # quick upper-neighbour grace note, then fall onto the note
            k = min(int(0.075 * SR), len(t))
            lf[:k] += 2.0 / 12
            lf[k:] += (2.0 / 12) * np.exp(-(t[k:] - t[k - 1]) / 0.015) if k < len(t) else 0
        strength = rng.uniform(0.78, 1.0)
        breath_curve = strength * (0.84 + 0.16 * np.sin(np.pi * np.clip(t / max(L / SR, 0.01), 0, 1)))
        pressure[s:e] = breath_curve
        lf += drift[s:e] + 0.011 * expression * np.clip((t - 0.3) / 0.8, 0, 1) * vib[s:e]
        lf += (breath_curve - 0.85) * 0.012 * expression
        logf[s:e] = lf
        att = 0.03 if legato else 0.1
        dur = L / SR
        env = np.minimum(t / att, 1.0) * np.clip((dur - t) / 0.14, 0, 1) * (0.85 + 0.15 * np.sin(np.pi * np.clip(t / dur, 0, 1)))
        amp[s:e] = np.maximum(amp[s:e], env * breath_curve)
        trans[s:e] = np.maximum(trans[s:e], np.exp(-t / 0.06))
        prev_end, prev_lf = e, lf[-1]
    valid = ~np.isnan(logf)
    if not valid.any():
        return np.zeros(n)
    idx = np.where(valid, np.arange(n), 0)
    idx = np.maximum.accumulate(idx)
    first = np.argmax(valid)
    idx[:first] = first
    hz = 2.0 ** logf[idx]
    ph = np.cumsum(hz) / SR
    tone = np.sin(2 * np.pi * ph)
    for k, a in ((2, 0.28), (3, 0.11), (4, 0.035)):
        tone += a * (0.5 + 0.7 * pressure) * np.sin(2 * np.pi * k * ph)
    breath = filt(noise(n, rng), "bp", np.clip(hz * 2, 200, 4000), 2.2, 64)
    env = filt(amp, "lp", 40, 0.7)
    y = (tone * 0.8 + breath * (0.12 + 0.22 * pressure + 0.3 * trans)) * env
    # Soft, wide breath 'air' above the tone: no transients, follows the blowing.
    air = static(static(noise(n, rng), "hp", 2500), "lp", 9000) * (0.3 * pressure + 0.5 * trans)
    return static(y, "lp", 4500) + air * env * 0.07 * air_amt


def tanpura(midi, dur, rng):
    """Karplus-Strong drone string with a slowly sweeping 'jawari' shimmer."""
    from scipy.signal import lfilter
    n = int(dur * SR)
    hz = midi_hz(midi)
    D = int(round(SR / hz)) - 1
    exc = np.zeros(n)
    m = 2 * (D + 1)
    exc[:m] = filt(noise(m, rng), "lp", 2200, 0.7) * np.hanning(m)
    a = np.zeros(D + 2)
    a[0], a[D], a[D + 1] = 1.0, -0.4993, -0.4993
    y = lfilter([1.0], a, exc)
    t = secs(n)
    harm = 6 + 6 * np.clip(t / dur, 0, 1)
    shimmer = filt(y, "bp", hz * harm, 5.0, 128)
    y = y + shimmer * 1.2
    y = y / (np.abs(y).max() + 1e-9)
    return fade_edges(y, 0.001, 0.3)


def didgeridoo(midi, dur, accents, rng):
    """Rhythmic didgeridoo bar: low buzzing drone, vowel 'wah' shapes on accent steps.
    accents: list of (beat_pos, strength) within `dur` seconds."""
    n = int((dur + 0.15) * SR)
    t = secs(n)
    hz = midi_hz(midi) * (1 + 0.004 * np.sin(2 * np.pi * 0.7 * t))
    src = saw(hz, n) * 0.8 + pulse(hz, n, 0.18) * 0.4
    shape = np.zeros(n)
    beat = dur / 4
    for b, k in accents:
        s = int(b * beat * SR)
        if s >= n:
            continue
        m = min(int(0.22 * SR), n - s)
        tt = np.arange(m) / SR
        shape[s:s + m] = np.maximum(shape[s:s + m], k * np.exp(-tt / 0.07) * np.minimum(tt / 0.012, 1))
    f1 = 280 + 420 * shape  # 'u' -> 'a' mouth opening
    f2 = 750 + 650 * shape
    y = filt(src, "bp", f1, 4.0, 32) * 1.4 + filt(src, "bp", f2, 6.0, 32) * 0.5 + lp4(src, 260, 0.8, 256) * 0.6
    amp = (0.55 + 0.45 * shape) * np.minimum(t / 0.05, 1) * np.clip((dur + 0.15 - t) / 0.12, 0, 1)
    return drive(static(y * amp, "lp", 1800), 1.4)


# ---------------------------------------------------------------- earth / ceremony kit

MEMBRANE = (1.0, 1.594, 2.136, 2.296, 2.653, 2.918, 3.156, 3.501, 3.600, 4.060)
# Mode weights by stroke: the centre (doum) excites the round (0,n) modes, the rim the diametric ones.
STROKES = dict(doum=(1.0, 0.18, 0.08, 0.32, 0.05, 0.03, 0.02, 0.06, 0.1, 0.02),
               tek=(0.25, 0.9, 0.75, 0.2, 0.6, 0.45, 0.35, 0.3, 0.12, 0.2),
               slap=(0.3, 0.8, 0.9, 0.35, 0.8, 0.6, 0.55, 0.45, 0.25, 0.35))


def hand_drum(kind, hz, rng, strength=0.8):
    """Darbuka/djembe strokes as a modal membrane: ten circular-membrane modes,
    each with its own decay, an amplitude-dependent pitch drop (tension
    modulation), a contact-time excitation (soft hits are darker) and a goblet
    body resonance. kind: doum (deep centre), tek (rim), slap, ghost."""
    strength = float(np.clip(strength, 0.15, 1.0))
    hz *= rng.uniform(0.985, 1.015)
    deep = kind == "doum"
    n = int((0.7 if deep else 0.25) * SR)
    t = secs(n)
    w = STROKES["tek" if kind == "ghost" else kind]
    base = hz if deep else hz * 1.9
    t60 = (0.24 if deep else 0.06) * (0.8 + 0.25 * strength)
    bend = 1 + (0.09 if deep else 0.04) * strength * np.exp(-t / 0.025)
    y = np.zeros(n)
    for r, a in zip(MEMBRANE, w):
        r *= rng.uniform(0.99, 1.01)
        a *= rng.uniform(0.8, 1.2)
        y += a * sine(base * r * bend, n, rng.uniform(0, 0.1)) * np.exp(-t * r ** 0.9 / t60)
    contact = int(SR * (0.0035 - 0.002 * strength) * (1.5 if deep else 0.8))
    h = np.hanning(max(contact, 3))
    y = np.convolve(y, h / h.sum())[:n]
    if deep:  # goblet air resonance underneath the skin
        y += 0.5 * sine(hz * 0.72, n) * np.exp(-t / 0.12) * (1 - np.exp(-t / 0.01))
    skin = static(noise(n, rng), "bp", (2200, 4200)) * np.exp(-t / (0.004 if deep else 0.007))
    y += skin * (0.08 if deep else 0.22) * strength
    y = static(y, "lp", 2600 + 3200 * strength)
    y /= np.abs(y).max() + 1e-9
    if kind == "ghost":
        y *= 0.45
    return fade_edges(drive(y * (0.6 + 0.4 * strength), 1.0 + 0.3 * strength), 0.0003, 0.02)


def udu(hz, rng):
    """Clay pot 'bloop': airy resonance that rises after the hit."""
    n = int(0.55 * SR)
    t = secs(n)
    f = hz * (0.75 + 0.45 * (1 - np.exp(-t / 0.05)))
    y = sine(f, n) * np.exp(-t / 0.17) * (1 - np.exp(-t / 0.008))
    y += sine(hz * 0.5, n) * np.exp(-t / 0.05) * 0.4
    return fade_edges(y, 0.001, 0.05)


def log_drum(hz, rng):
    """Wooden slit drum: damped inharmonic partials, no bell sustain."""
    n = int(0.4 * SR)
    t = secs(n)
    u = rng.uniform(0.85, 1.15, 3)
    y = sine(hz, n) * np.exp(-t / (0.11 * u[0])) + 0.3 * u[1] * sine(hz * 2.76 * rng.uniform(0.99, 1.01), n) * np.exp(-t / 0.04) \
        + 0.12 * u[2] * sine(hz * 5.4 * rng.uniform(0.98, 1.02), n) * np.exp(-t / 0.015)
    y += static(noise(n, rng), "lp", 1800) * np.exp(-t / 0.004) * 0.25
    return fade_edges(y, 0.0005, 0.03)


def oud(midi, dur, rng, bright=1800.0, strength=0.8, stroke=1):
    """Paired plucked strings with fractional tuning and intensity-dependent pick/body."""
    from scipy.signal import lfilter
    n = int((dur + 0.6) * SR)
    strength = float(np.clip(strength, 0.15, 1.0))
    hz = midi_hz(midi)
    y = np.zeros(n)
    for cents, level in ((-2.5, 0.72), (2.5, 0.45)):
        # Two-tap loss filter contributes half a sample of phase delay.
        period = SR / (hz * 2 ** (cents / 1200))
        delay = period - 0.5
        D = int(np.floor(delay))
        fraction = delay - D
        # First-order allpass has fractional phase delay at the fundamental.
        w = 2 * np.pi / period
        alpha = (1 - np.tan(w * fraction / 2) / np.tan(w / 2)) / (1 + np.tan(w * fraction / 2) / np.tan(w / 2))
        m = min(2 * (D + 2), n)
        exc = np.zeros(n)
        exc[:m] = filt(noise(m, rng), "lp", bright * (0.65 + 0.55 * strength), 0.7) * np.hanning(m)
        pick = rng.uniform(0.10, 0.19) if stroke > 0 else rng.uniform(0.18, 0.27)
        exc[:m] -= 0.65 * np.roll(exc[:m], max(1, int(period * pick)))
        # Loop = delay * averaging loss * fractional allpass.
        g = 0.992 + 0.004 * strength
        a = np.zeros(D + 4)
        a[0], a[1] = 1.0, alpha
        a[D:D + 3] -= g * 0.5 * np.array([alpha, 1 + alpha, 1])
        y += level * lfilter([1.0, alpha], a, exc)
    y += filt(y, "bp", 260, 1.2) * 0.4 + filt(y, "bp", 620, 1.6) * 0.25
    y /= max(np.max(np.abs(y)), 1e-9)
    y *= 0.65 + 0.35 * strength
    t = secs(n)
    y *= np.clip((dur + 0.6 - t) / 0.12, 0, 1)
    return fade_edges(y, 0.0005, 0.02)


def throat_phrase(notes, n, f0, rng):
    """Overtone (throat) singing: a low drone whose whistling harmonic carries the melody.
    notes: [(start_sample, len_samples, target_hz)]; whistle snaps to the nearest harmonic of f0."""
    t = secs(n)
    k = np.full(n, np.nan)
    amp = np.zeros(n)
    for s, L, hz in notes:
        e = min(s + L, n)
        if s >= n:
            break
        h = float(np.clip(np.round(hz / f0), 4, 14))
        k[s:e] = h
        tt = np.arange(e - s) / SR
        amp[s:e] = np.maximum(amp[s:e], np.minimum(tt / 0.15, 1) * np.clip((L / SR - tt) / 0.2, 0, 1))
    valid = ~np.isnan(k)
    if not valid.any():
        return np.zeros(n)
    idx = np.maximum.accumulate(np.where(valid, np.arange(n), 0))
    first = np.argmax(valid)
    idx[:first] = first
    kk = filt(k[idx], "lp", 12, 0.7)  # glide between harmonics
    drone_env = np.minimum(t / 0.6, 1) * np.clip((t[-1] - t) / 0.8, 0, 1)
    f = f0 * (1 + 0.003 * np.sin(2 * np.pi * 4.5 * t))
    src = saw(f, n) * 0.8 + pulse(f, n, 0.3) * 0.4
    body = filt(src, "bp", 450, 3.0, 128) + filt(src, "bp", 800, 4.0, 128) * 0.5
    whistle = filt(src, "bp", kk * f0, 28.0, 64) * 7.0
    y = body * drone_env * 0.5 + whistle * filt(amp, "lp", 20, 0.7)
    return drive(static(y, "lp", 3500), 1.2)


def frog(rng):
    n = int(rng.uniform(0.18, 0.35) * SR)
    t = secs(n)
    x = pulse(rng.uniform(28, 45), n, 0.12)
    y = filt(x, "bp", rng.uniform(380, 650), 4.0) * np.clip(np.sin(np.pi * t / t[-1]), 0, 1) ** 0.7
    return fade_edges(y * 2.0)


def earth_bed(n, rng, level):
    """Low wind + earth rumble bed, level: per-sample array."""
    t = secs(n)
    k = n // 4410 + 2
    walk = np.cumsum(rng.normal(0, 0.08, k))
    walk = (walk - walk.min()) / (np.ptp(walk) + 1e-9)
    fc = 160 * 2 ** (2.2 * np.interp(np.arange(n), np.linspace(0, n, k), walk))
    L = filt(noise(n, rng), "bp", fc, 1.3, 512)
    R = filt(noise(n, rng), "bp", fc * 1.07, 1.3, 512)
    rum = static(noise(n, rng), "lp", 55, order=4) * 3.0
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * t / 11.0)
    return np.stack([(L * swell + rum) * level, (R * (1.6 - swell) * 0.8 + rum) * level], axis=1)
