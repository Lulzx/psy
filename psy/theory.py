"""Scales, chords and pattern generators."""
import numpy as np

SCALES = {
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "phrygian_dominant": [0, 1, 4, 5, 7, 8, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "hungarian_minor": [0, 2, 3, 6, 7, 8, 11],
    "double_harmonic": [0, 1, 4, 5, 7, 8, 11],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
}
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_name(m):
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}"


def deg(scale, d):
    o, i = divmod(int(d), len(scale))
    return scale[i] + 12 * o


def chord(scale, d, size=3):
    return [deg(scale, d + 2 * k) for k in range(size)]


def parse(pat):
    """'x.o.' -> velocities [1, 0, .5, 0]."""
    return [{"x": 1.0, "o": 0.55, ".": 0.0, "-": 0.0}.get(c, 0.0) for c in pat]


# ---------------------------------------------------------------- bass

def bass_phrases(cfg, scale, rng, n_variants=3):
    """Returns a list of 4-bar phrases; each bar is a list of (step, semis, vel)."""
    steps = parse(cfg["rhythm"])
    motion = cfg.get("motion", "phrase")
    alts = cfg.get("alts", [12, 1, -2, 3, 5, 7])
    phrases = []
    for v in range(n_variants):
        bars = []
        if motion == "riff":  # goa: a melodic 2-bar riff
            riff = []
            for s, vel in enumerate(steps * 2):
                if not vel:
                    continue
                r = rng.random()
                if r < 0.62:
                    semi = 0
                elif r < 0.75:
                    semi = 12
                else:
                    semi = deg(scale, int(rng.choice([1, 2, 4, 5, 6, -1])))
                riff.append((s, semi, vel))
            L = len(steps)
            two = [[(s, m, vl) for s, m, vl in riff if s < L],
                   [(s - L, m, vl) for s, m, vl in riff if s >= L]]
            bars = [two[0], two[1], two[0], two[1]]
        elif motion == "chord":  # psybient: follows the chord root, octave/fifth pops
            for b in range(4):
                bars.append([(s, 0 if rng.random() < 0.7 else int(rng.choice([12, 7, -5])), vel)
                             for s, vel in enumerate(steps) if vel])
        else:
            alt = int(rng.choice(alts))
            for b in range(4):
                bar = []
                for s, vel in enumerate(steps):
                    if not vel:
                        continue
                    semi = 0
                    beat_frac = s / len(steps)
                    if motion == "phrase" and b == 3 and beat_frac >= 0.5:
                        semi = alt
                    elif motion == "phrase" and v == 2 and b == 1 and beat_frac >= 0.75:
                        semi = 12
                    elif motion == "static" and b == 3 and s == max(i for i, q in enumerate(steps) if q):
                        semi = 12
                    bar.append((s, semi, vel))
                bars.append(bar)
        phrases.append(bars)
    return phrases


# ---------------------------------------------------------------- acid (303-ish)

def acid_seq(cfg, scale, rng):
    n = cfg.get("steps", 16)
    seq = []
    weights = np.array([6, 2, 2, 2, 2, 1, 1, 4, 2, 1])
    degs = np.array([0, 1, 2, 3, 4, 5, 6, 7, 9, -1])
    for i in range(n):
        if i > 0 and rng.random() < cfg.get("rest_p", 0.2):
            seq.append(None)
            continue
        d = int(rng.choice(degs, p=weights / weights.sum()))
        seq.append(dict(semi=deg(scale, d), accent=rng.random() < cfg.get("accent_p", 0.3),
                        slide=rng.random() < cfg.get("slide_p", 0.2)))
    return seq


def mutate(seq, scale, rng, k=2):
    seq = [None if s is None else dict(s) for s in seq]
    for _ in range(k):
        i = int(rng.integers(1, len(seq)))
        if seq[i] is None:
            seq[i] = dict(semi=deg(scale, int(rng.integers(0, 8))), accent=bool(rng.random() < 0.4), slide=False)
        else:
            seq[i]["semi"] = deg(scale, int(rng.integers(-1, 9)))
            seq[i]["slide"] = bool(rng.random() < 0.3)
    return seq


# ---------------------------------------------------------------- lead

def lead_phrase(cfg, scale, rng, bars=4, sub=4):
    """Returns list of (start_step, len_steps, semis, vel) spanning `bars` bars."""
    spb = sub * 4
    if cfg.get("mode") == "gated":
        gate = parse(cfg.get("gate", "x.xx.xx.x.xx.x.x"))
        prog = [0, 0, int(rng.choice([1, 5, 6])), int(rng.choice([2, 3, 4]))]
        out = []
        for b in range(bars):
            tones = chord(scale, prog[b % 4], 3) + [chord(scale, prog[b % 4], 3)[0] + 12]
            for s, v in enumerate(gate):
                if v:
                    out.append((b * spb + s, 1, tones[(s * 3 + b) % len(tones)], v))
        return out

    def motif(length):
        notes, s = [], 0
        d = int(rng.choice([0, 2, 4, 7]))
        lo, hi = cfg.get("range", (-2, 9))
        while s < length:
            if rng.random() > cfg.get("density", 0.75):
                s += int(rng.integers(1, 3))
                continue
            ln = int(rng.choice([1, 1, 1, 2, 2, 3, 4][: cfg.get("max_len", 3) + 3]))
            ln = min(ln, length - s)
            notes.append([s, ln, d])
            s += ln
            step = int(rng.choice([1, -1, 1, -1, 2, -2])) if rng.random() > cfg.get("leap", 0.2) else int(rng.choice([3, 4, -3, -4, 7, -7]))
            d = int(np.clip(d + step, lo, hi))
        return notes

    a = motif(spb * 2)
    # answer phrase: same first bar, new second bar
    b = [n[:] for n in a if n[0] < spb] + [[s + spb, ln, d] for s, ln, d in motif(spb)]
    out = []
    for off, part in ((0, a), (2 * spb, b)):
        for s, ln, d in part:
            out.append((off + s, ln, deg(scale, d), 1.0))
    return out


# ---------------------------------------------------------------- arp

def arp_seq(cfg, scale, rng, sub=4):
    length = cfg.get("length", 8)
    pool = [0, 2, 4, 7, 9, 11]
    seq = []
    for i in range(length):
        if rng.random() < cfg.get("rest_p", 0.15) and i:
            seq.append(None)
        else:
            seq.append(int(rng.choice(pool)))
    return seq
