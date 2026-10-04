"""'Follower' — a night walk through a forest, and something that walks behind you.

The fear comes from space and imitation, not from high or harsh sounds:

- Your flute calls, and the dark answers with your own phrase. At first it is a
  far echo off the hills. Then the answer comes back a little flat, then bent,
  then a tritone low, closer every chapter, until it breathes beside you.
- Footsteps behind you walk out of step, a little slower than the beat, and
  drift until they land exactly on it. Once they are in step, they become the kick.
- At low energy the kick is a heartbeat (lub-dub) heard from inside, muffled.
  Tempo follows a fear response: 126 BPM at rest, 150 at the peak.
- An endless Shepard-Risset glissando made of howling wind bands: it falls
  forever while you hide and rises forever before the drops, and never arrives.
- Roughness (fast 40-70 Hz amplitude flutter, the acoustic cue that makes
  screams alarming) is applied to low voices and breath instead of any shriek.

Everything stays in the low and middle register (see docs/sound-guide.md).
"""
import numpy as np
from . import dsp, theory as th, instruments as ins
from .dsp import SR, secs, noise, filt, static
from .song import place
from .journey import Journey
from .mycelium import Mycelium

ROOT = 27  # D#1 / Eb1


def chapter(name, bars, mode, e, bpm, chords, carriers, tonic=0, **kw):
    return dict(name=name, bars=bars, mode=mode, tonic=tonic, e=e, bpm=bpm, chords=chords,
                follow=kw.pop("follow", False), carriers=carriers, **kw)


# answer: how the dark replies to the flute. dist 0 (beside you) .. 1 (across the valley);
# wrong 0 = exact echo, 1 = flat with a falling bend, 2 = flat and a tritone off; oct = octave shift.
CHAPTERS = [
    chapter("lantern", 12, "phrygian", [(0, 0.0), (1, 0.22)], (126, 127), [0, 0, 1, 0, 6, 0],
            ["ney"], melt=0.2, nature=1.0, owls=True,
            answer=dict(dist=1.0, wrong=0, oct=0)),
    chapter("footsteps behind", 16, "phrygian", [(0, 0.22), (1, 0.5)], (127, 133), [0, 1, 0, 6, 0, 1, 4, 0],
            ["ney", "ney", "throat"], melt=0.25, nature=0.6, steps=True, owls=True,
            answer=dict(dist=0.85, wrong=0, oct=0)),
    chapter("it answers", 20, "phrygian", [(0, 0.5), (0.6, 0.66), (1, 0.8)], (133, 140),
            [0, 1, 0, 4, 0, 1, 6, 1, 0, 0], ["ney", "chant", "ney", "duet"], melt=0.45, nature=0.25,
            reverse=True, answer=dict(dist=0.65, wrong=1, oct=0)),
    chapter("run", 24, "hungarian_minor", [(0, 0.82), (0.55, 1.0), (1, 0.9)], (141, 148),
            [0, 1, 0, 4, 0, 1, 5, 4, 1, 0, 4, 0], ["duet", "ney", "lead", "duet"], melt=0.2,
            answer=dict(dist=0.45, wrong=1, oct=-12, rough=0.3)),
    chapter("hold your breath", 16, "locrian", [(0, 0.86), (0.3, 0.2), (0.75, 0.22), (1, 0.4)], (147, 138),
            [0, 0, 1, 0, 4, 1, 0, 1], ["ney"], melt=0.8, nature=0.3, reverse=True, breath=1.0, moan=True,
            answer=dict(dist=0.08, wrong=1, oct=0, voice="whisper")),
    chapter("it is here", 28, "phrygian_dominant", [(0, 0.42), (0.35, 0.95), (0.7, 1.0), (1, 0.84)], (139, 150),
            [0, 1, 0, 6, 0, 1, 5, 6, 1, 0, 6, 0, 1, 0], ["lead", "duet", "ney", "duet"], tonic=1, follow=True,
            melt=0.35, choir=True, reverse=True, breath=0.45, moan=True,
            answer=dict(dist=0.28, wrong=2, oct=-12, rough=0.6)),
    chapter("first light?", 14, "phrygian", [(0, 0.8), (0.45, 0.3), (1, 0.0)], (148, 128), [1, 0, 1, 0, 6, 0, 0],
            ["ney", "throat", "ney"], melt=0.4, nature=1.0, owls=True,
            answer=dict(dist=0.55, wrong=0, oct=0)),
]

# The call: root, minor third, fifth, then a tritone fall onto the flat second.
MOTIF = [(0, 1, 0), (1, 0.5, 2), (1.5, 1.5, 4), (3, 1, 1)]

# Endless glissandi: (chapter, start fraction, end fraction, direction, octaves per second, level)
SHEPARD = [
    ("it answers", 0.65, 1.0, +1, 0.22, 0.9),
    ("hold your breath", 0.12, 0.78, -1, 0.07, 1.0),
    ("hold your breath", 0.72, 1.0, +1, 0.2, 0.8),
    ("it is here", 0.0, 0.3, -1, 0.05, 0.55),
    ("first light?", 0.35, 1.0, -1, 0.05, 0.7),
]


# ---------------------------------------------------------------- instruments of the night

def roughness(n, rng, depth, lo=40.0, hi=70.0):
    """Fast amplitude flutter in the 30-150 Hz 'roughness' band: the cue that makes a
    scream alarming, here applied to low voices, so it frightens without any shriek."""
    rate = lo + (hi - lo) * (0.5 + 0.5 * dsp.wander(n, 0.3, rng, 1))
    ph = np.cumsum(rate) / SR
    return 1 - depth * 0.5 * (1 + np.sin(2 * np.pi * ph))


def footfall(rng, weight=1.0):
    """A heavy step on the forest floor: a low thud through soil plus a dry crunch of leaves."""
    n = int(0.45 * SR)
    t = secs(n)
    f = 52 * rng.uniform(0.9, 1.1) + 40 * np.exp(-t / 0.02)
    thud = dsp.sine(f, n) * np.exp(-t / 0.07) * np.minimum(t / 0.004, 1)
    crunch = noise(n, rng) * (np.exp(-t / 0.035) + 0.4 * np.exp(-((t - 0.04) / 0.02) ** 2))
    crunch = static(filt(crunch, "bp", rng.uniform(700, 1100), 0.9), "lp", 2200)
    return dsp.fade_edges(thud * 1.2 * weight + crunch * (0.35 + 0.25 * weight), 0.0005, 0.05)


def owl(rng):
    """Tawny-owl style 'hoo ... hoo-hoo-hoo', a soft hollow whistle around 380 Hz."""
    f0 = rng.uniform(330, 410)
    parts = [(0.0, 0.55, 1.0), (1.05, 0.12, 0.6), (1.25, 0.14, 0.7), (1.45, 0.6, 0.9)]
    n = int(2.3 * SR)
    out = np.zeros(n)
    for s, L, g in parts:
        m = int((L + 0.05) * SR)
        t = secs(m)
        hz = f0 * (1 + 0.04 * np.exp(-t / 0.05)) * (1 - 0.05 * t / (L + 0.05)) * (1 + 0.012 * np.sin(2 * np.pi * 9 * t))
        env = np.sin(np.pi * np.clip(t / (L + 0.05), 0, 1)) ** 1.5
        x = dsp.sine(hz, m) + 0.12 * dsp.sine(2 * hz, m) + filt(noise(m, rng), "bp", hz, 6.0) * 0.4
        i = int(s * SR)
        out[i:i + m] += x[: n - i] * env * g
    return dsp.fade_edges(out, 0.002, 0.05)


def breath_cycle(rng, growl=0.5, inhale=1.6, exhale=2.3):
    """One slow breath of something large: hollow inhale, then a lower, rough exhale."""
    n = int((inhale + exhale + 0.3) * SR)
    t = secs(n)
    ni = int(inhale * SR)
    src = noise(n, rng)
    shape = np.zeros(n)
    shape[:ni] = np.sin(np.pi * np.arange(ni) / ni) ** 2 * 0.55
    ne = n - ni
    te = np.arange(ne) / ne
    shape[ni:] = np.minimum(te / 0.08, 1) * (1 - te) ** 1.4
    f1 = np.where(t < inhale, 600 + 250 * t / inhale, 420)
    f2 = np.where(t < inhale, 1300 + 300 * t / inhale, 950)
    y = filt(src, "bp", f1, 3.5, 128) + filt(src, "bp", f2, 4.0, 128) * 0.55 + static(src, "lp", 300) * 0.4
    rough = np.ones(n)
    rough[ni:] = roughness(ne, rng, growl, 38, 58)
    y = static(y * shape * rough, "lp", 2400)
    return dsp.fade_edges(y, 0.01, 0.05)


def whisper_phrase(notes, n, rng):
    """A pitched whisper: breath through narrow resonances that follow the melody, no voiced tone.
    notes: [(start_sample, len_samples, midi, grace)]"""
    hz = np.full(n, np.nan)
    amp = np.zeros(n)
    for s, L, m, _ in notes:
        e = min(s + L, n)
        if s >= n:
            break
        hz[s:e] = dsp.midi_hz(m)
        tt = np.arange(e - s) / SR
        amp[s:e] = np.maximum(amp[s:e], np.minimum(tt / 0.12, 1) * np.clip((L / SR - tt) / 0.2, 0, 1))
    valid = ~np.isnan(hz)
    if not valid.any():
        return np.zeros(n)
    idx = np.maximum.accumulate(np.where(valid, np.arange(n), 0))
    idx[: np.argmax(valid)] = np.argmax(valid)
    f = filt(hz[idx], "lp", 15, 0.7)
    src = noise(n, rng)
    y = filt(src, "bp", f, 22.0, 64) * 3.0 + filt(src, "bp", f * 2, 18.0, 64) * 1.4
    y += filt(src, "bp", 700, 2.5) * 0.25 + filt(src, "bp", 1300, 3.0) * 0.12
    return static(y * filt(amp, "lp", 25, 0.7), "lp", 2600)


def shepard_wind(n, direction, rate, rng, bands=5, lo=55.0, center=220.0, sigma=0.9, q=16.0):
    """Shepard-Risset glissando built from narrow wind bands an octave apart. Each band
    glides forever; its level follows a bell over log-frequency, so a band fades out at
    one end while a new one fades in at the other. Heard: a howl that never stops falling
    (or rising). Stereo, the two channels slightly offset."""
    t = secs(n)
    phase = direction * rate * t
    mid = np.log2(center / lo)
    out = np.zeros((n, 2))
    for ch, off in enumerate((0.0, 0.07)):
        src = noise(n, rng)
        for k in range(bands):
            x = (k + phase + off) % bands
            w = np.exp(-0.5 * ((x - mid) / sigma) ** 2)
            out[:, ch] += filt(src, "bp", lo * 2 ** x, q, 64) * w
    return out


class Follower(Mycelium):
    CHAPTERS = CHAPTERS
    MOTIF = MOTIF
    RISES = {"it answers": 4, "hold your breath": 4}
    SWELL_AT = ("run", "it is here")
    FALLS = ()
    SLOW_CARRIERS = ("ney", "chant", "throat")
    ALWAYS_SLOW = ("throat", "chant")
    NEY_COUNTER_WITH = ("oud", "lead", "chant", "throat")
    LAYERS = ("r_kick", "r_bass", "r_low_drones", "r_hand_drums", "r_steps", "r_didge", "r_melody",
              "r_follower", "r_breath", "r_moan", "r_pad", "r_shepard", "r_nature", "r_fx")
    MASTER_RMS = -11.5
    MASTER_LUFS = -10.8
    # A pine forest at night: trunks scatter the sound, soft needle floor, open sky.
    ROOM = dict(room=(34.0, 30.0, 14.0), absorb=(0.55, 0.45, 1.0))
    STAGE = dict(Mycelium.STAGE, ney=dict(az=-10, dist=0.1, move=12), steps=dict(az=0, dist=0.5, width=0.4),
                 owl=dict(az=-55, dist=0.9, width=0.5), moan=dict(az=0, dist=0.75, width=1.5),
                 shepard=dict(dist=0.55, width=1.5))
    REVERB = dict(rt60=3.8, hf_ratio=0.35, size=1.25)
    DYN_DB, DYN_FULL = -16.0, 0.85

    def __init__(self, seed=13, root=ROOT):
        super().__init__(seed=seed, root=root)

    def chap_end(self, name):
        return self.chap_start[name] + next(c["bars"] for c in self.CHAPTERS if c["name"] == name)

    # ------------------------------------------------------------------ composition
    def _compose(self):
        """Mycelium's eight-bar arcs, with a hole cut after each call for the dark to answer."""
        super()._compose()
        gaps = {b for b in range(self.bars) if self.rows[b]["i"] % 8 in (3, 7) and b >= 3}
        keep = []
        for ev in self.melody:
            bar, b, ln, d, g, carrier = ev
            for gb in gaps:  # nothing may sound in a gap bar after beat 1
                start, end = bar * 4 + b, bar * 4 + b + ln
                if start >= gb * 4 + 1 and start < gb * 4 + 4:
                    break
                if start < gb * 4 + 1 < end:
                    ln = gb * 4 + 1 - start
            else:
                if ln >= 0.25:
                    keep.append((bar, b, ln, d, g, carrier))
        self.melody = keep
        self.counter = [c for c in self.counter if c[0] not in gaps]
        self.answers = []
        rng = np.random.default_rng(self.seed + 7)
        last_gap = max(gaps)
        for gb in sorted(gaps):
            call = sorted([(b, ln, d) for bar, b, ln, d, g, c in keep if bar == gb - 3])[:4]
            if not call:
                continue
            a = self.ch(gb)["answer"]
            k = self.rows[gb]["i"] // 4  # answers within a chapter drift further each time
            stretch = 0.75 - 0.04 * (k % 3)
            notes = []
            for j, (b, ln, d) in enumerate(call):
                if k % 2 == 1 and j == 1:
                    continue  # it forgets a note
                m = float(self.note(gb - 3, d)) + a["oct"]
                last = j == len(call) - 1
                if a["wrong"] >= 1:
                    m -= 0.3 + 0.15 * (a["wrong"] - 1) + 0.04 * k  # sung back a little flat
                if a["wrong"] >= 2 and last:
                    m -= 6  # and the end lands a tritone away
                notes.append((1.0 + b * stretch, ln * stretch, m))
            if a["wrong"] >= 1:  # last note sags down a semitone, like a voice losing its shape
                t, ln, m = notes[-1]
                notes[-1] = (t, ln * 0.55, m)
                notes.append((t + ln * 0.55, ln * 0.6 + 0.4, m - 1.0))
            final = gb == last_gap
            dist = 0.02 if final else float(np.clip(a["dist"] + rng.normal(0, 0.04), 0, 1))
            az = 175.0 if final else float(rng.choice([-1, 1]) * rng.uniform(25, 75))
            self.answers.append(dict(bar=gb, notes=notes, dist=dist, az=az, voice=a.get("voice", "ney"),
                                     rough=a.get("rough", 0.0)))

    # ------------------------------------------------------------------ heart and steps
    def r_kick(self):
        """Four on the floor at energy; below it a muffled lub-dub heartbeat, the same
        pulse heard from inside. The two overlap while the fear builds."""
        cache = {}
        buf, hits = self.track(), []
        kl = self.lvl(0.34, 0.12)
        hl = np.clip(1 - (self.E - 0.32) / 0.14, 0, 1)
        for bar in range(self.bars):
            key = (self.tonic(bar), round(self.bl(bar), 3))
            if key not in cache:
                t_ = self.tonic(bar)
                hz = dsp.midi_hz(t_ if 27 <= t_ <= 33 else self.root)
                p = dict(len=1.12 * self.bl(bar) / 4, f0=185, pdecay=0.026, click=0.18, drive=1.9, tail=0.42)
                lub = dict(len=0.3, f0=95, pdecay=0.04, click=0.0, drive=1.3, tail=0.6)
                dub = dict(len=0.22, f0=120, pdecay=0.03, click=0.0, drive=1.2, tail=0.6)
                cache[key] = ([ins.kick(hz, self.vary(p), self.rng) for _ in range(4)],
                              [ins.kick(hz * 1.05, self.vary(lub), self.rng) for _ in range(3)],
                              [ins.kick(hz * 1.2, self.vary(dub), self.rng) for _ in range(3)])
            kicks, lubs, dubs = cache[key]
            if kl[bar] > 0:
                for bt in (0.0, 1.0, 2.0, 3.0):
                    p0 = self.pos(bar, bt)
                    place(buf, kicks[int(self.rng.integers(4))], p0, kl[bar])
                    if kl[bar] > 0.3:
                        hits.append(p0)
            if hl[bar] > 0:
                for half in (0.0, 2.0):
                    p0 = self.pos(bar, half)
                    place(buf, lubs[int(self.rng.integers(3))], p0, 0.9 * hl[bar])
                    place(buf, dubs[int(self.rng.integers(3))], self.pos(bar, half + 0.6), 0.55 * hl[bar])
                    if kl[bar] <= 0.3:
                        hits.append(p0)
        self.sc_env = dsp.sidechain_env(self.n, hits, 0.8, 0.3)
        self.add(buf, 0.86, cut=self.curve(np.clip((self.E - 0.25) / 0.3, 0.28, 1)))

    def r_steps(self):
        """Footsteps behind you, slower than the beat, drifting until they fall in step;
        owls far off; and at the end, steps walking up to the listener and stopping."""
        rng = np.random.default_rng(self.seed + 31)
        buf, owls = self.track(), self.track()
        for ch in self.CHAPTERS:
            if not ch.get("steps"):
                continue
            s, nb = self.chap_start[ch["name"]], ch["bars"]
            N = nb * 4
            beats, x = [], float(N)
            while x > 0:  # placed backwards from the end, where they lock onto the beat
                beats.append(x)
                x -= 1 + 0.16 * (1 - x / N) ** 1.4
            for x in beats:
                bar, bt = s + int(x // 4), x % 4
                prog = x / N
                place(buf, footfall(rng, 0.6 + 0.4 * prog), self.pos(bar, bt), 0.25 + 0.75 * prog ** 0.7,
                      0.25 * np.sin(x * 0.4))
        # The last steps come up behind the listener and stop; then the final answer, right there.
        last = self.answers[-1]["bar"]
        t, stop, k = self.t0[last - 2], self.t0[last] + 0.4 * self.bl(last), 0
        while t < stop:
            place(buf, footfall(rng, 0.5 + 0.1 * k), int(t * SR), 0.35 + 0.15 * k, 0.15 * (-1) ** k)
            t += 0.66 * (1 + 0.12 * k)
            k += 1
        for bar in range(self.bars):
            if self.ch(bar).get("owls") and self.E[bar] < 0.45 and rng.random() < 0.18:
                place(owls, owl(rng), self.pos(bar, float(rng.uniform(0, 3))), rng.uniform(0.5, 0.9),
                      rng.uniform(-0.6, 0.6))
        self.add(buf, 0.7, rev=0.35, hp=30, src="steps")
        self.add(owls, 0.16, rev=0.6, dly=0.15, lp=2000, src="owl")

    # ------------------------------------------------------------------ the thing that answers
    def r_follower(self):
        rng = np.random.default_rng(self.seed + 404)
        dry, wet = self.track(), self.track()
        for a in self.answers:
            bar = a["bar"]
            s0 = self.pos(bar, a["notes"][0][0])
            notes = [(self.pos(bar, t) - s0, int(ln * self.bl(bar) * SR), m, False) for t, ln, m in a["notes"]]
            n = notes[-1][0] + notes[-1][1] + int(2.5 * SR)
            if a["voice"] == "whisper":
                mono = whisper_phrase(notes, n, rng) * 0.9
            else:
                mono = ins.ney_phrase(notes, n, rng, expression=1.8, air_amt=0.4 * self.AIR)
                mono = static(mono, "lp", 3000)
            if a["rough"]:
                mono *= roughness(n, rng, a["rough"])
            x = np.stack([mono, mono], axis=1)
            staged = dsp.stage(x, a["az"], a["dist"], 0.5, self.ROOM, er_level=1.1, seed=self.seed + bar)
            # Far answers are mostly room; close ones are dry and intimate.
            place(dry, staged, s0, 1.25 - 0.45 * a["dist"])
            place(wet, x, s0, 0.15 + 0.85 * a["dist"])
        self.mix += dry * 0.42
        self.rev += wet * 0.5
        self.dly += wet * 0.08

    def r_breath(self):
        """Something large breathing close by, free-running, never on the grid."""
        rng = np.random.default_rng(self.seed + 55)
        lv = self.chap_curve("breath") * np.clip(1.15 - self.E, 0.25, 1)
        buf = self.track()
        t = 0.0
        while t < self.t0[-1]:
            bar = int(np.searchsorted(self.t0, t, "right") - 1)
            bar = min(max(bar, 0), self.bars - 1)
            ex = rng.uniform(2.0, 2.8)
            if lv[bar] > 0.02:
                x = breath_cycle(rng, growl=0.35 + 0.4 * self.E[bar], inhale=rng.uniform(1.3, 1.9), exhale=ex)
                place(buf, x, int(t * SR), lv[bar], rng.uniform(-0.3, 0.3))
            t += 1.6 + ex + rng.uniform(0.3, 1.4)
        self.add(buf, 5.5, rev=0.12, hp=80, src="breath")

    def r_moan(self):
        """Low male voices in a semitone cluster, far off, with roughness growing in them."""
        rng = np.random.default_rng(self.seed + 77)
        buf = self.track()
        lv = self.curve(np.convolve(np.pad(self.chap_curve("moan"), 2, mode="edge"), np.ones(5) / 5, "valid"))
        for bar in range(0, self.bars, 2):
            if not self.ch(bar).get("moan"):
                continue
            r = self.tonic(bar) + 24 + th.deg(self.scale(bar), self.chord(bar)) % 12
            dur = 8 * self.bl(bar) * 1.05
            for m, g in ((r, 1.0), (r + 1, 0.7), (r - 5, 0.5)):
                x = ins.voice(m, dur, [["o", "u"], ["u", "o", "u"], ["a", "o"]][int(rng.integers(3))], rng, 3)
                x *= roughness(len(x), rng, 0.25 + 0.3 * self.E[bar])
                place(buf, x, self.pos(bar) - int(0.3 * SR), g, rng.uniform(-0.5, 0.5))
        buf *= lv[:, None]
        self.add(buf, 0.27, rev=0.55, sc=0.3, hp=90, lp=2400, src="moan")

    def r_shepard(self):
        rng = np.random.default_rng(self.seed + 9)
        buf = self.track()
        for name, f0, f1, direction, rate, lvl in SHEPARD:
            s, e = self.chap_start[name], self.chap_end(name)
            a = self.pos(s) + int(f0 * (self.pos(e) - self.pos(s)))
            b = self.pos(s) + int(f1 * (self.pos(e) - self.pos(s)))
            n = b - a
            x = shepard_wind(n, direction, rate, rng)
            fade = np.minimum(1, np.minimum(np.arange(n), n - np.arange(n)) / (2.5 * SR))
            env = np.sin(np.pi / 2 * fade) ** 2
            if direction > 0:  # rising: it swells toward the turning point
                env *= 0.45 + 0.55 * np.linspace(0, 1, n) ** 1.5
            place(buf, x * (env * lvl)[:, None], a)
        self.add(buf, 5.0, rev=0.45, sc=0.2, hp=60, lp=2500, src="shepard")

    def r_fx(self):
        rng = self.rng
        buf = self.track()
        for name in self.SWELL_AT:
            place(buf, ins.impact(rng), self.pos(self.chap_start[name]), 1.6)
        self.add(buf, 0.3, rev=0.35, dly=0.15, lp=3000, src="fx")

    def describe(self):
        return Journey.describe(self)
