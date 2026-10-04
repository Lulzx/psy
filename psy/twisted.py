"""A single through-composed twisted full-on track, Mandragora-inspired.

147 BPM, F# phrygian dominant, ~3:45. A composed signature hook opens the track and
returns developed (answered, ornamented, sequenced, harmonised), never looped. The
bass phrase, hats, fills, acid line, riff synth and FX are re-decided every 4-8 bars,
and the climax modulates up a semitone. Registers stay low/mid: no bells, no
FM plucks, melodies capped around C#5.
"""
import numpy as np
from . import dsp, theory as th, instruments as ins
from .dsp import SR
from .song import place

BPM = 147
SCALE = th.SCALES["phrygian_dominant"]  # degrees: 0=1 1=b2 2=3 3=4 4=5 5=b6 6=b7 7=8

# name, bars, levels. Values: float | (a, b) ramp | [(from_bar, value|ramp), ...]
SECTIONS = [
    ("open", 4, dict(pad=1, pad_cut=(0.25, 0.6), lead=0.8, lead_cut=(0.3, 0.6), voice=1, reese=0.7, fx=0.3)),
    ("intro", 8, dict(kick=1, bass=1, bass_cut=(0.2, 0.9), tom=0.5,
                      fx=0.7, voice=[(0, 0)])),
    ("groove", 8, dict(kick=1, bass=1, riff=0.8,
                       acid=[(0, 0), (4, 0.7)], acid_cut=[(0, 0.1), (4, (0.1, 0.45))], fx=0.8)),
    ("drop1", 24, dict(kick=1, bass=1, lead=1, acid=0.7,
                       acid_cut=(0.3, 0.75), riff=[(0, 0), (16, 0.8)], fx=1)),
    ("twist", 12, dict(kick=1, bass=1, acid=1, acid_cut=(0.25, 1.0),
                       riff=1, fx=1.2)),
    ("tribal", 12, dict(tom=1, pad=1, pad_cut=(0.2, 0.6), reese=0.8, voice=1,
                        lead=[(0, 0), (4, 0.6)], lead_cut=[(4, (0.2, 0.55))],
                        kick=[(0, 0), (8, 1)], bass=[(0, 0), (8, 1)], bass_cut=[(8, (0.2, 0.85))], fx=0.6)),
    ("drop2", 24, dict(kick=1, bass=1, lead=1, acid=0.7, acid_cut=(0.3, 0.8),
                       riff=[(0, 0.7), (12, 0)], pad=0.35, fx=1, tom=[(16, 0.5)])),
    ("breakdown", 12, dict(pad=1, reese=0.8, voice=[(0, 1), (8, 0)], lead=0.7,
                           lead_cut=[(0, 0.4), (8, (0.35, 0.8))], acid=[(8, 1)], acid_cut=[(8, (0.1, 0.8))],
                           kick=[(8, 1)], fx=0.6)),
    ("climax", 24, dict(kick=1, bass=1, lead=1, acid=0.65,
                        acid_cut=(0.4, 1.0), riff=[(8, 0.7)], pad=0.4, fx=1)),
    ("outro", 8, dict(kick=1, bass=1, bass_cut=[(0, 1), (4, (1, 0.2))],
                      tom=0.6, acid=[(0, 0.5), (4, 0)], acid_cut=(0.6, 0.1), fx=0.6, voice=[(4, 1)])),
]
# The spiritual layer: ney flute + tanpura drone run through the whole track,
# up front in the breaks, quieter behind the drops; extra chant lines at the back.
SPIRIT = dict(
    open=dict(ney=1, drone=0.9), intro=dict(ney=0.6, drone=0.5), groove=dict(ney=0.45, drone=0.4),
    drop1=dict(ney=0.4, drone=0.35), twist=dict(ney=[(0, 0.3), (8, 0)], drone=0.3),
    tribal=dict(ney=[(0, 0), (4, 1)], drone=1), drop2=dict(ney=0.45, drone=0.4, voice=[(0, 0), (8, 0.35)]),
    breakdown=dict(ney=1, drone=1), climax=dict(ney=0.45, drone=0.4, voice=[(0, 0), (16, 0.35)]),
    outro=dict(ney=1, drone=0.9),
)
for _name, _n, _lv in SECTIONS:
    _lv.update(SPIRIT.get(_name, {}))

DROPS = ("drop1", "drop2", "climax")
PRE_DROP = dict(groove=dict(gap=3.0, roll=1, riser=8, sweep=2), tribal=dict(gap=2.0, roll=4, riser=8, sweep=2),
                breakdown=dict(gap=2.0, roll=4, riser=8, sweep=2), open=dict(gap=4.0, roll=0, riser=4, sweep=0))

# chord per 2 bars (scale degrees)
HARMONY = dict(open=[0, 1], intro=[0], groove=[0], drop1=[0, 1, 0, 6], twist=[0], tribal=[0, 0, 1, 0],
               drop2=[0, 1, 5, 6], breakdown=[0, 5, 1, 0, 3, 1], climax=[0, 1, 0, 6, 5, 1, 0, 0], outro=[0])

BASS_SOUND = dict(
    normal=dict(wave="saw", base=140, peak=2600, env_decay=0.04, res=1.6, sub_lvl=0.7, drive=2.0,
                amp_decay=0.13, sustain=0.55, growl=0.25),
    dark=dict(wave="saw", base=110, peak=3600, env_decay=0.03, res=3.0, sub_lvl=0.7, drive=2.8,
              amp_decay=0.11, sustain=0.5, growl=0.4),
    bright=dict(wave="pulse", base=170, peak=3000, env_decay=0.045, res=1.8, sub_lvl=0.7, drive=2.2,
                amp_decay=0.14, sustain=0.55, growl=0.3),
)
SECTION_BASS = dict(intro="normal", groove="normal", drop1="normal", twist="dark", tribal="dark",
                    drop2="bright", breakdown="normal", climax="normal", outro="dark")

ACID = dict(
    groove=dict(steps=15, wave="saw", res=3.6, cut_min=160, cut_max=1500, envmod=2.0, decay=0.12, drive=2.0),
    drop1=dict(steps=13, wave="square", res=3.6, cut_min=180, cut_max=2000, envmod=2.0, decay=0.1, drive=2.6),
    twist=dict(steps=14, wave="saw", res=3.6, cut_min=140, cut_max=2800, envmod=2.5, decay=0.08, drive=3.4),
    drop2=dict(steps=12, wave="saw", res=3.6, cut_min=180, cut_max=2200, envmod=2.1, decay=0.1, drive=2.8),
    breakdown=dict(steps=16, wave="saw", res=3.6, cut_min=170, cut_max=2200, envmod=2.0, decay=0.13, drive=2.2),
    climax=dict(steps=24, wave="square", res=3.6, cut_min=200, cut_max=2600, envmod=2.2, decay=0.09, drive=3.0),
    outro=dict(steps=11, wave="saw", res=3.6, cut_min=160, cut_max=1400, envmod=1.7, decay=0.12, drive=2.0),
)
for _a in ACID.values():
    _a.update(rest_p=0.2, slide_p=0.28, accent_p=0.25, accent_mod=0.6)

# The signature hook: (step16, length, degree). 4 bars, AA'AB shape.
HOOK_A = []
for _bar, _notes in enumerate([
    [(2, 4), (1, 5), (1, 4), (2, 2), (1, 1), (1, 0), (4, 1), (2, -1), (2, 0)],
    [(2, 7), (1, 6), (1, 5), (2, 4), (2, 5), (1, 4), (1, 2), (2, 1), (2, 2), (2, 0)],
    [(2, 4), (1, 5), (1, 4), (2, 2), (1, 1), (1, 0), (4, 1), (2, -1), (2, 0)],
    [(1, 4), (1, 4), (2, 5), (2, 7), (2, 8), (1, 7), (1, 5), (2, 4), (2, 1), (2, 0)],
]):
    _s = _bar * 16
    for _ln, _d in _notes:
        HOOK_A.append([_s, _ln, _d, 1.0])
        _s += _ln
# Soaring counter-theme for drop 2 / climax
HOOK_B = []
for _bar, _notes in enumerate([
    [(4, 7), (2, 8), (2, 7), (4, 5), (4, 4)],
    [(2, 5), (2, 4), (2, 2), (2, 1), (4, 2), (4, 0)],
    [(4, 7), (2, 8), (2, 9), (4, 8), (4, 7)],
    [(3, 5), (3, 4), (2, 2), (4, 1), (4, 0)],
]):
    _s = _bar * 16
    for _ln, _d in _notes:
        HOOK_B.append([_s, _ln, _d, 1.0])
        _s += _ln


class Twisted:
    def __init__(self, seed=11, root=30):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.beat = 60.0 / BPM
        self.bar = 4 * self.beat
        self.base_root = root
        self.sections, b = [], 0
        for name, n, lv in SECTIONS:
            self.sections.append((name, b, n, lv))
            b += n
        self.bars = b
        self.n = int((self.bars * self.bar + 6.0) * SR)
        self.sec_of = []
        for name, s, n, _ in self.sections:
            self.sec_of += [(name, i, n) for i in range(n)]
        self._levels()
        self._structure()

    # ------------------------------------------------------------------ helpers
    def _levels(self):
        self.lv = {}
        for name, s, n, lv in self.sections:
            for k, v in lv.items():
                if k not in self.lv:
                    self.lv[k] = np.ones(self.bars) if k.endswith("_cut") else np.zeros(self.bars)
                segs = v if isinstance(v, list) else [(0, v)]
                for j, (fr, val) in enumerate(segs):
                    to = segs[j + 1][0] if j + 1 < len(segs) else n
                    self.lv[k][s + fr:s + to] = np.linspace(val[0], val[1], to - fr) if isinstance(val, tuple) else val

    def L(self, k, bar):
        a = self.lv.get(k)
        return 0.0 if a is None or bar >= self.bars else float(a[bar])

    def pos(self, bar, beats=0.0):
        return int((bar * self.bar + beats * self.beat) * SR)

    def curve(self, k):
        a = self.lv.get(k)
        if a is None:
            return None
        xs = np.arange(self.bars + 1) * self.bar * SR
        return np.interp(np.arange(self.n), xs, np.append(a, a[-1]))

    def start_of(self, name):
        return next(s for nm, s, n, _ in self.sections if nm == name)

    def root_at(self, bar):
        return self.base_root + (1 if bar >= self.mod_bar else 0)

    def chord_at(self, bar):
        name, i, n = self.sec_of[bar]
        prog = HARMONY[name]
        return prog[(i // 2) % len(prog)]

    def cap(self, m, bar, hi=43, lo=26):
        """Keep melodic notes in the low/mid register (max ~C#5)."""
        r = self.root_at(bar)
        while m > r + hi:
            m -= 12
        while m < r + lo:
            m += 12
        return m

    def _structure(self):
        rng = self.rng
        self.mod_bar = self.start_of("climax") + 12
        self.gaps = {}  # bar -> beat after which kick/bass/hats are silent
        for name, s, n, _ in self.sections:
            if name in PRE_DROP:
                self.gaps[s + n - 1] = PRE_DROP[name]["gap"]
            if name == "twist":
                self.gaps[s + n - 1] = 2.0
            if name in DROPS + ("outro",):
                for ph in range(8, n, 8):
                    if rng.random() < 0.5:
                        self.gaps[s + ph - 1] = float(rng.choice([3.0, 3.5]))
        self.fill_bars = {s + i for name, s, n, _ in self.sections for i in range(3, n, 4) if (i + 1) % 8 == 0 or rng.random() < 0.3}

    # ------------------------------------------------------------------ mix plumbing
    def add(self, buf, gain=1.0, rev=0.0, dly=0.0, sc=0.0, cut=None, hp=None, lp=None, chorus=False):
        if cut is not None:
            c = self.curve(cut)
            if c is not None and c.min() < 0.999:
                fc = 120.0 * 2 ** (c * 7.3)
                buf = np.stack([dsp.filt(buf[:, i], "lp", fc, 0.9, 256) for i in range(2)], axis=1)
        if hp:
            buf = dsp.static(buf, "hp", hp)
        if lp:
            buf = dsp.static(buf, "lp", lp)
        if chorus:
            buf = dsp.chorus(buf)
        if sc:
            buf = buf * (1 - sc * (1 - self.sc_env))[:, None]
        buf = buf * gain
        self.mix += buf
        if rev:
            self.rev += buf * rev
        if dly:
            self.dly += buf * dly

    def track(self):
        return np.zeros((self.n, 2))

    # ------------------------------------------------------------------ kick
    def r_kick(self):
        p = dict(len=1.1 * self.beat / 4, f0=210, pdecay=0.022, click=0.35, drive=2.2, tail=0.38)
        kicks = {r: ins.kick(dsp.midi_hz(r), p, self.rng) for r in (self.base_root, self.base_root + 1)}
        buf, hits = self.track(), []
        for bar in range(self.bars):
            lv = self.L("kick", bar)
            if not lv:
                continue
            beats = [0.0, 1.0, 2.0, 3.0]
            if bar in self.fill_bars and bar not in self.gaps and self.rng.random() < 0.35:
                beats.append(3.75)
            g = self.gaps.get(bar, 9)
            for bt in beats:
                if bt < g:
                    p0 = self.pos(bar, bt)
                    place(buf, kicks[self.root_at(bar)], p0, lv * (0.8 if bt == 3.75 else 1.0))
                    hits.append(p0)
        self.sc_env = dsp.sidechain_env(self.n, hits, 1.0, self.beat * 0.7)
        self.add(buf, 1.0)

    # ------------------------------------------------------------------ drums
    def r_drums(self):
        """Phrase-end fills and build-up rolls, all on warm pitched toms (no noisy claps/snares)."""
        buf = self.track()
        for bar in range(self.bars):
            if bar in self.fill_bars and bar not in self.gaps and self.L("kick", bar):
                self._fill(buf, bar)
        for name, s, n, _ in self.sections:  # build-up rolls into drops
            k = PRE_DROP.get(name, {}).get("roll", 0)
            if k:
                self._roll(buf, s + n - k, k)
        self.add(buf, 0.6, rev=0.2, dly=0.06, hp=55, lp=8000)

    def tom_hz(self, bar, step):
        return dsp.midi_hz(self.root_at(bar) + 24 + step)

    def _fill(self, buf, bar):
        rng = self.rng
        kind = ["down", "up", "gallop", "call"][int(rng.integers(4))]
        if kind in ("down", "up"):
            for j, s in enumerate((12, 13, 14, 15)):
                k = j if kind == "up" else 3 - j
                place(buf, ins.tom(self.tom_hz(bar, 3 * k), 0.14, rng), self.pos(bar, s / 4), 0.75, 0.5 - 0.33 * j)
        elif kind == "gallop":
            for j, t in enumerate((3.0, 3.33, 3.67)):
                place(buf, ins.tom(self.tom_hz(bar, 7 - 2 * j), 0.13, rng), self.pos(bar, t), 0.7, 0.3 - 0.3 * j)
        else:  # call and answer between two toms
            for j, s in enumerate((10, 11, 14, 15)):
                place(buf, ins.tom(self.tom_hz(bar, 5 if j < 2 else 0), 0.15, rng), self.pos(bar, s / 4), 0.7,
                      -0.4 if j < 2 else 0.4)

    def _roll(self, buf, first, bars):
        """Tom roll that accelerates and rises in pitch into the drop."""
        rng = self.rng
        times = []
        for b in range(bars):
            left = bars - b
            div = 8 if bars == 1 else (2 if left > 2 else (4 if left == 2 else 8))
            times += [b * 4 + k / div for k in range(4 * div)]
        T = bars * 4
        cache = {}
        for t in times:
            x = t / T
            step = int(round(x * 12))
            if step not in cache:
                cache[step] = ins.tom(self.tom_hz(first, step), 0.1, rng)
            place(buf, cache[step], self.pos(first, t), 0.15 + 0.6 * x ** 1.6, 0.3 * np.sin(t * 3))

    def r_tribal(self):
        rng = self.rng
        buf = self.track()
        pat = None
        for bar in range(self.bars):
            lv = self.L("tom", bar)
            if not lv:
                continue
            name, i, n = self.sec_of[bar]
            if i % 4 == 0 or pat is None:  # new 2-bar tribal pattern every 4 bars
                pat = []
                for s in range(32):
                    r = rng.random()
                    if s % 8 == 0 or (r < 0.32 and s % 2 == 0) or r < 0.1:
                        pat.append((s, int(rng.choice([0, 0, 1, 2])), rng.uniform(0.6, 1.0)))
            root = self.root_at(bar)
            toms = [dsp.midi_hz(root + 24), dsp.midi_hz(root + 29), dsp.midi_hz(root + 34)]
            g = self.gaps.get(bar, 9)
            for s, which, v in pat:
                if (s >= 16) != (i % 2 == 1) or (s % 16) / 4 >= g:
                    continue
                place(buf, ins.tom(toms[which], 0.18 - which * 0.03, rng), self.pos(bar, (s % 16) / 4),
                      lv * v, [-0.35, 0.3, 0.55][which])
        self.add(buf, 0.6, rev=0.22, dly=0.06, hp=55, lp=9000)

    # ------------------------------------------------------------------ bass
    def _bass_bar(self, kind, alt, bar_in_phrase, fill, motif):
        """-> list of (beat_pos, semis, vel, dur_beats)."""
        notes = []
        for b in range(4):
            if kind == "triplet":
                notes += [(b + k / 3, 0, 1.0, 0.25) for k in (1, 2)]
                continue
            steps = {"roll": (1, 2, 3), "gallop": (2, 3), "push": (1, 2, 3), "oct": (1, 2, 3),
                     "acid": (1, 2, 3), "offroll": (1, 3)}[kind]
            for s in steps:
                semi = 0
                if kind == "oct" and s == 3 and b % 2 == 1:
                    semi = 12
                if kind == "acid":
                    semi = motif[(b * 3 + s) % len(motif)]
                vel = 0.8 if kind == "push" and s == 1 else 1.0
                notes.append((b + s / 4, semi, vel, 0.24 if kind in ("gallop", "offroll") else 0.2))
        if bar_in_phrase == 3:
            notes = [(t, alt if t >= 2 else sm, v, d) for t, sm, v, d in notes]
            if fill == "up32":
                notes = [x for x in notes if x[0] < 3] + [(3 + k / 8, k * 2, 0.9, 0.1) for k in range(1, 8)]
            elif fill == "drop":
                notes = [x for x in notes if x[0] < 3.5]
        return notes

    def r_bass(self):
        rng = self.rng
        kinds_for = dict(intro=["roll"], groove=["roll", "gallop"], drop1=["roll", "oct", "push", "acid"],
                         twist=["acid", "triplet", "offroll", "roll"], tribal=["roll", "gallop"],
                         drop2=["roll", "acid", "oct", "push"], breakdown=["roll"],
                         climax=["roll", "oct", "acid", "push", "triplet"], outro=["roll", "gallop"], open=["roll"])
        alts = [1, -2, 3, 5, 12, -4, 7, 13]
        cache = {}
        buf = self.track()
        prev, phrase = None, None
        # "knob ride": slow aperiodic walk on the bass filter, quantised so notes can be cached
        walk = np.cumsum(rng.normal(0, 0.35, self.bars))
        walk -= np.convolve(walk, np.ones(15) / 15, "same")
        morphs = np.array([0.55, 0.75, 1.0, 1.3, 1.7])
        morph_at = morphs[np.clip(np.round(walk + 2), 0, 4).astype(int)]
        for bar in range(self.bars):
            name, i, n = self.sec_of[bar]
            if i % 4 == 0 or phrase is None:
                for _ in range(20):
                    cand = (str(rng.choice(kinds_for[name])), int(rng.choice(alts)),
                            str(rng.choice(["none", "up32", "drop", "none"])))
                    if cand != prev and (prev is None or cand[1] != prev[1]):
                        break
                motif = [int(rng.choice([0, 0, 0, 1, 12, -2, 7, 0])) for _ in range(12)]
                phrase, prev = (cand, motif), cand
            lv = self.L("bass", bar)
            if not lv:
                continue
            (kind, alt, fill), motif = phrase
            if name == "intro" and i < 4:
                fill = "none"
            snd = SECTION_BASS.get(name, "normal")
            mo = float(morph_at[bar])
            g = self.gaps.get(bar, 9)
            notes = self._bass_bar(kind, alt, i % 4, fill, motif)
            if i % 4 in (1, 2) and rng.random() < 0.6:  # one-off pitch blip so no two bars match
                j = int(rng.integers(len(notes)))
                t, _, v, d = notes[j]
                notes[j] = (t, int(rng.choice([12, 1, 7, -2, 13])), v, d)
            for t, semi, vel, d in notes:
                if t >= g:
                    continue
                m = self.root_at(bar) + semi
                key = (m, round(d, 3), snd, mo)
                if key not in cache:
                    p = dict(BASS_SOUND[snd], peak=BASS_SOUND[snd]["peak"] * mo,
                             env_decay=BASS_SOUND[snd]["env_decay"] * (0.75 + 0.25 * mo))
                    cache[key] = ins.rich_bass(dsp.midi_hz(m), d * self.beat, p)
                place(buf, cache[key], self.pos(bar, t), lv * vel)
        self.add(buf, 0.72, cut="bass_cut")

    def r_reese(self):
        """Sustained sub/reese under the breaks so the low end never disappears."""
        buf = self.track()
        bar = 0
        while bar < self.bars:
            lv = self.L("reese", bar)
            if not lv:
                bar += 1
                continue
            d = self.chord_at(bar)
            e = bar + 1
            while e < self.bars and self.L("reese", e) and self.chord_at(e) == d and e - bar < 4 \
                    and self.sec_of[e][0] == self.sec_of[bar][0]:
                e += 1
            m = self.root_at(bar) + 12 + th.deg(SCALE, d)
            if m > self.root_at(bar) + 19:
                m -= 12
            place(buf, ins.reese(m, (e - bar) * self.bar, self.rng), self.pos(bar), lv)
            bar = e
        self.add(buf, 0.55, rev=0.08)

    # ------------------------------------------------------------------ acid
    def r_acid(self):
        rng = self.rng
        buf = self.track()
        cut = self.curve("acid_cut")
        k = self.bars * 2 + 2  # aperiodic random-walk wobble on top of the automation
        walk = np.cumsum(rng.normal(0, 0.09, k))
        walk = (walk - np.convolve(walk, np.ones(9) / 9, "same")) * 1.4
        cn = np.clip(cut + np.interp(np.arange(self.n), np.linspace(0, self.n, k), walk), 0, 1)
        lvl = self.lv["acid"]
        step = self.beat / 4
        for name, s, n, _ in self.sections:
            act = [b for b in range(s, s + n) if lvl[b] > 0]
            if not act:
                continue
            cfg = ACID[name]
            b0, b1 = act[0], act[-1] + 1
            seq = th.acid_seq(cfg, SCALE, rng)
            versions = [seq]
            for _ in range((b1 - b0) // 2 + 1):  # cumulative mutation every 2 bars
                versions.append(th.mutate(versions[-1], SCALE, rng, int(rng.integers(1, 3))))
            s0 = self.pos(b0)
            nn = self.pos(b1) - s0 + int(0.25 * SR)
            fc = cfg["cut_min"] * (cfg["cut_max"] / cfg["cut_min"]) ** cn[s0:s0 + nn]
            L = len(seq)

            def steps(i, b0=b0, versions=versions, L=L):
                bar = b0 + i // 16
                if bar in self.gaps and (i % 16) / 4 >= self.gaps[bar]:
                    return None
                st = versions[min(i // 32, len(versions) - 1)][i % L]  # polymeter: L may be 12/14/24
                if st is None:
                    return None
                return dict(st, semi=st["semi"] + self.root_at(bar) - self.base_root)

            y = ins.acid_line(steps, nn, step * SR, self.base_root + 12, fc, cfg, rng)
            gl = np.interp(np.arange(nn), np.arange(b1 - b0 + 1) * self.bar * SR, np.append(lvl[b0:b1], 0))
            pn = 0.2 * np.sin(2 * np.pi * np.arange(nn) / SR / (self.bar * 3.3))
            place(buf, np.stack([y * gl * (1 - pn), y * gl * (1 + pn)], axis=1), s0)
        self.add(buf, 0.17, rev=0.1, dly=0.18, sc=0.3, hp=100, lp=7000)

    # ------------------------------------------------------------------ hook / leads
    def _develop(self, theme, op):
        rng = self.rng
        t = [n[:] for n in theme]
        if op == "answer":  # keep bars 1-2, improvise a new ending that resolves home
            out = [n for n in t if n[0] < 32]
            s, d = 32, int(rng.choice([2, 4, 5]))
            rhythms = [[2, 2, 1, 1, 2, 4, 2, 2], [3, 3, 2, 2, 2, 4], [1, 1, 1, 1, 2, 2, 4, 2, 2], [2, 1, 1, 2, 2, 4, 4]]
            for b in range(2):
                for ln in rhythms[int(rng.integers(len(rhythms)))]:
                    out.append([s, ln, d, 1.0])
                    s += ln
                    d = int(np.clip(d + rng.choice([1, -1, -1, 2, -2]), -1, 8))
            out[-1][2] = 0
            t = out
        elif op == "shift":  # diatonic sequence of the first half
            k = int(rng.choice([1, 2, -1]))
            t = [n for n in t if n[0] < 32] + [[s + 32, ln, d + k, v] for s, ln, d, v in t if s < 32]
        elif op == "invert":
            t = [[s, ln, int(np.clip(8 - d, -1, 9)), v] for s, ln, d, v in t]
        elif op == "trill":  # eastern ornament on held notes
            out = []
            for s, ln, d, v in t:
                if ln >= 3:
                    out += [[s, 1, d, v], [s + 1, 1, d + 1, v * 0.8], [s + 2, ln - 2, d, v]]
                else:
                    out.append([s, ln, d, v])
            t = out
        elif op == "harmony":  # add a diatonic third below
            t = t + [[s, ln, d - 2, v * 0.45] for s, ln, d, v in t]
        elif op == "sparse":
            t = [n for n in t if n[1] >= 2]
        elif op == "halftime":
            t = [[s * 2, ln * 2, d, v] for s, ln, d, v in t if s < 32]
        elif op == "rhythmic":  # same pitches, displaced by an 8th: syncopated restatement
            t = [[s + 2, ln, d, v] for s, ln, d, v in t if s + 2 < 64]
        return t

    def r_leads(self):
        rng = self.rng
        # per section: list of (theme, ops) per 4-bar block; first block of each drop states the hook plainly
        sched = dict(
            open=[(HOOK_A, ["sparse"])],
            tribal=[(HOOK_A, ["halftime"]), (HOOK_A, ["halftime", "sparse"]), (HOOK_A, ["sparse", "trill"])],
            breakdown=[(HOOK_B, ["halftime"]), (HOOK_B, ["halftime", "trill"]), (HOOK_A, ["sparse"])],
        )
        pools = dict(drop1=(HOOK_A, ["answer", "trill", "shift", "rhythmic", "invert"]),
                     drop2=(None, ["answer", "trill", "harmony", "shift", "rhythmic"]),
                     climax=(None, ["harmony", "answer", "trill", "shift", "invert"]))
        for name, (theme, pool) in pools.items():
            n = next(nn for nm, s, nn, _ in self.sections if nm == name)
            blocks, last = [], None
            for j in range(n // 4):
                th_ = theme or (HOOK_A if j % 3 != 1 else HOOK_B)
                if j == 0:
                    blocks.append((HOOK_A if name != "drop2" else HOOK_B, ["harmony"] if name == "climax" else []))
                    continue
                op = str(rng.choice([o for o in pool if o != last]))
                ops = [op] + (["harmony"] if name == "climax" and op != "harmony" and rng.random() < 0.5 else [])
                blocks.append((th_, ops))
                last = op
            sched[name] = blocks
        plan = {}
        for name, s, n, _ in self.sections:
            for j, (theme, ops) in enumerate(sched.get(name, [])):
                notes = theme
                for op in ops:
                    notes = self._develop(notes, op)
                for k in range(4):
                    if j * 4 + k < n:
                        plan[s + j * 4 + k] = (notes, k)
        cache = {}
        lead = self.track()
        step = self.beat / 4
        for bar, (notes, k) in plan.items():
            lv = self.L("lead", bar)
            if not lv:
                continue
            for s, ln, d, v in notes:
                if not (k * 16 <= s < (k + 1) * 16):
                    continue
                m = self.cap(self.root_at(bar) + 36 + th.deg(SCALE, d), bar)
                key = (m, ln)
                if key not in cache:
                    cache[key] = ins.warm_lead(m, ln * step * 0.92, rng)
                place(lead, cache[key], self.pos(bar, (s - k * 16) / 4), lv * v)
        self.add(lead, 0.36, rev=0.28, dly=0.25, sc=0.5, cut="lead_cut", hp=180, lp=6500, chorus=True)

    def r_riff(self):
        """Rhythmic didgeridoo: earthy groove layer, accent rhythm re-written every 8 bars,
        with a call / answer / varied-call / new-answer shape inside each 4 bars."""
        rng = self.rng
        buf = self.track()
        pat, cache = None, {}
        for bar in range(self.bars):
            name, i, n = self.sec_of[bar]
            if i % 8 == 0 or pat is None:
                dens = rng.uniform(0.3, 0.5)

                def mk():
                    return tuple((s / 4, round(float(rng.uniform(0.5, 1.0)), 1)) for s in range(16)
                                 if (s % 4 != 0 and rng.random() < dens) or s % 8 == 6)
                a = mk()
                a2 = tuple(x for x in a if rng.random() < 0.8) + ((3.5, 1.0),)
                pat = (a, mk(), a2, mk())
            lv = self.L("riff", bar)
            if not lv:
                continue
            g = self.gaps.get(bar, 9)
            acc = tuple(x for x in pat[i % 4] if x[0] < g)
            key = (self.root_at(bar), acc)
            if key not in cache:
                cache[key] = ins.didgeridoo(self.root_at(bar) + 12, self.bar, acc, rng)
            y = cache[key]
            if g < 4:  # stop with the gap
                y = y.copy()
                e = int(g * self.beat * SR)
                y[e:] *= np.exp(-np.arange(len(y) - e) / (0.03 * SR))
            place(buf, y, self.pos(bar), lv, 0.1 * np.sin(bar))
        self.add(buf, 0.5, rev=0.15, dly=0.08, sc=0.4, hp=70)

    def r_pad(self):
        rng = self.rng
        pad = self.track()
        cache = {}
        bar = 0
        while bar < self.bars:
            lv = self.L("pad", bar)
            d = self.chord_at(bar)
            e = bar + 1
            while e < self.bars and self.chord_at(e) == d and self.L("pad", e) and e - bar < 8 \
                    and self.root_at(e) == self.root_at(bar) and self.sec_of[e][0] == self.sec_of[bar][0]:
                e += 1
            if lv:
                key = (d, e - bar, self.root_at(bar))
                if key not in cache:
                    r = self.root_at(bar)
                    notes = [r + 24 + x for x in th.chord(SCALE, d, 4)] + [r + 12 + th.deg(SCALE, d)]
                    cache[key] = ins.pad_chord(notes, (e - bar) * self.bar,
                                               dict(fc=1200, att=1.4, voices=5, lfo=9.0, rel=2.0), rng)
                place(pad, cache[key], self.pos(bar), lv)
            bar = e
        self.add(pad, 1.1, rev=0.45, sc=0.55, cut="pad_cut", hp=110, lp=5000, chorus=True)

    def _slow_line(self, nbeats, sparse=False, runs=True):
        """Slow, improvised-feeling modal line: long held notes, ornamental runs,
        breaths, sometimes quoting the hook. -> [(beat, len_beats, degree, grace)]"""
        rng = self.rng
        out, t = [], float(rng.choice([0, 0.5, 1, 2]))
        d = int(rng.choice([4, 0, 2, 5]))
        if rng.random() < 0.3:  # slow quote of the hook's opening
            for ln, dd in ((1, 4), (0.5, 5), (0.5, 4), (1, 2), (1, 1), (3, 0)):
                out.append((t, ln, dd, False))
                t += ln
            t += 1
            d = 0
        rest_p = 0.3 if sparse else 0.12
        while t < nbeats - 2:
            r = rng.random()
            if r < rest_p:
                t += float(rng.choice([1, 2, 3] if sparse else [1, 1.5, 2]))
                continue
            if runs and r < rest_p + 0.22:  # ornamental turn of 8ths / triplets
                k = int(rng.choice([3, 4]))
                step = float(rng.choice([0.5, 1 / 3]))
                direction = int(rng.choice([1, -1]))
                for j in range(k):
                    out.append((t, step, d, False))
                    t += step
                    d = int(np.clip(d + direction, -3, 8))
            ln = float(rng.choice([2, 3, 4, 4, 6] if not sparse else [3, 4, 6, 8]))
            ln = min(ln, nbeats - t)
            if ln <= 0.5:
                break
            out.append((t, ln, d, bool(rng.random() < 0.35)))
            t += ln
            if rng.random() < 0.25:
                t += 0.5  # a breath
            d = int(np.clip(d + rng.choice([1, -1, 1, -1, 2, -2, 3]), -3, 8))
            if rng.random() < 0.15:
                d = int(rng.choice([0, 4, 1]))
        if out:  # resolve the phrase home
            b, ln, _, g = out[-1]
            out[-1] = (b, ln, int(rng.choice([0, 4])), g)
        return out

    def r_ney(self):
        rng = self.rng
        buf = self.track()
        for name, s, n, _ in self.sections:
            for blk in range(0, n, 8):
                bars = [b for b in range(s + blk, min(s + blk + 8, s + n)) if self.L("ney", b)]
                if not bars:
                    continue
                b0, nb = bars[0], bars[-1] - bars[0] + 1
                line = self._slow_line(nb * 4, sparse=name in DROPS or name == "twist")
                notes = []
                for bt, ln, d, grace in line:
                    bar = b0 + int(bt // 4)
                    m = self.cap(self.root_at(bar) + 36 + th.deg(SCALE, d), bar, hi=44, lo=29)
                    st = self.pos(b0, bt) - self.pos(b0)
                    notes.append((st, int(ln * self.beat * SR * 0.97), m, grace))
                y = ins.ney_phrase(notes, int((nb * self.bar + 2.0) * SR), rng)
                pn = rng.uniform(-0.3, 0.3)
                place(buf, y, self.pos(b0), self.L("ney", b0), pn)
        self.add(buf, 0.42, rev=0.5, dly=0.3, sc=0.25, hp=200)

    def r_drone(self):
        """Tanpura: Pa - Sa' - Sa' - Sa, one pluck every two beats, under almost everything."""
        rng = self.rng
        buf = self.track()
        cache = {}
        for bar in range(self.bars):
            lv = self.L("drone", bar)
            if not lv:
                continue
            r = self.root_at(bar)
            for j, bt in enumerate((0.0, 2.0)):
                m = [r + 19, r + 24, r + 24, r + 12][(bar % 2) * 2 + j]
                if m not in cache:
                    cache[m] = ins.tanpura(m, 5.0, rng)
                place(buf, cache[m], self.pos(bar, bt), lv, [-0.4, 0.2, 0.4, -0.1][(bar % 2) * 2 + j])
        self.add(buf, 0.45, rev=0.35, sc=0.35, hp=90, lp=5000)

    def r_voice(self):
        """Eastern formant chant: opens the track, carries the tribal break, bookends the outro."""
        rng = self.rng
        buf = self.track()
        vow_sets = [["a", "o"], ["o", "u", "a"], ["e", "a"], ["a", "a", "o"], ["u", "o", "a"]]
        line = [(0, 6, 4), (6, 2, 5), (8, 8, 4), (16, 4, 1), (20, 4, 2), (24, 8, 0)]  # beat, len, degree
        run = None
        for bar in range(self.bars):
            lv = self.L("voice", bar)
            if not lv:
                run = None
                continue
            if run is None:
                run = bar
            if (bar - run) % 8:
                continue
            signature = bar == 0 or self.sec_of[bar][0] == "outro"
            this = line if signature else [(b, ln, d) for b, ln, d, _ in
                                           self._slow_line(32, sparse=True, runs=False)]
            shift = 0 if signature else int(rng.choice([0, 2, -1]))
            for b, ln, d in this:
                if bar + b / 4 >= self.bars:
                    break
                m = self.cap(self.root_at(bar) + 36 + th.deg(SCALE, d + shift), bar, hi=40, lo=30)
                x = ins.voice(m, ln * self.beat * 0.95, vow_sets[int(rng.integers(len(vow_sets)))], rng)
                place(buf, x, self.pos(bar, b), lv, rng.uniform(-0.25, 0.25))
        for name, s, n, _ in self.sections:  # chant shout in the silent beat(s) before each drop
            if name in PRE_DROP:
                g = PRE_DROP[name]["gap"]
                bar = s + n - 1
                m = self.root_at(bar) + 36 + th.deg(SCALE, 4)
                x = ins.voice(m, (4 - g) * self.beat * 0.85 if g < 4 else self.beat, ["a", "e"], rng)
                place(buf, x, self.pos(bar, g if g < 4 else 3.0), 1.1)
        self.add(buf, 0.22, rev=0.55, dly=0.3, sc=0.25, hp=140, lp=6000)

    # ------------------------------------------------------------------ fx & events
    def r_fx(self):
        rng = self.rng
        buf = self.track()
        names = ["gurgle"]
        for bar in range(self.bars):
            lv = self.L("fx", bar)
            if not lv:
                continue
            name, i, n = self.sec_of[bar]
            prob = 0.15 * lv + (0.15 if i % 4 == 3 else 0)
            for _ in range(2):
                if rng.random() < prob:
                    nm = str(rng.choice(names))
                    x = ins.FX[nm](rng)
                    x = x / (np.abs(x).max() + 1e-9)
                    place(buf, x, self.pos(bar, int(rng.integers(0, 8)) * 0.5), min(lv, 1.0), rng.uniform(-0.8, 0.8))
        self.add(buf, 0.18, rev=0.3, dly=0.4, sc=0.35, hp=150, lp=6000)

        ev = self.track()
        for name, s, n, _ in self.sections:
            if name in DROPS + ("twist", "intro"):
                place(ev, ins.impact(rng), self.pos(s), 0.55)
                place(ev, ins.downlifter(2 * self.bar, rng), self.pos(s), 0.15)
            if name in PRE_DROP:
                nb = min(PRE_DROP[name]["riser"], n)
                place(ev, ins.riser(nb * self.bar, rng), self.pos(s + n - nb), 0.25)
            if name in ("tribal", "outro", "breakdown"):
                place(ev, ins.downlifter(4 * self.bar, rng), self.pos(s), 0.25)
        self.add(ev, 1.0, rev=0.3, lp=9000)

    def post(self, mix):
        """Mix-level moves: HP sweeps into drops, tape-stop out of the twist."""
        for name, s, n, _ in self.sections:
            sw = PRE_DROP.get(name, {}).get("sweep", 0)
            if sw:
                a, b = self.pos(s + n - sw), self.pos(s + n)
                fc = np.geomspace(20, 700, b - a)
                for c in range(2):
                    mix[a:b, c] = dsp.filt(mix[a:b, c], "hp", fc, 0.8, 128)
            if name == "twist":
                a, b = self.pos(s + n - 1, 0.0), self.pos(s + n - 1, 2.0)
                T = b - a
                p = a + np.cumsum((1 - np.arange(T) / T) ** 1.6)
                for c in range(2):
                    mix[a:b, c] = np.interp(p, np.arange(len(mix)), mix[:, c]) * np.linspace(1, 0, T) ** 0.5
        return mix

    # ------------------------------------------------------------------ render
    def render(self, log=print):
        self.mix, self.rev, self.dly = self.track(), self.track(), self.track()
        for fn in (self.r_kick, self.r_bass, self.r_reese, self.r_drums, self.r_tribal, self.r_acid,
                   self.r_leads, self.r_riff, self.r_pad, self.r_voice, self.r_ney, self.r_drone, self.r_fx):
            log(f"  · {fn.__name__[2:]}")
            fn()
        log("  · fx returns + master")
        wet_d = dsp.pingpong(self.dly, 0.75 * self.beat, fb=0.42, damp=2800)
        self.rev += wet_d * 0.3
        wet_r = dsp.reverb(dsp.static(self.rev, "hp", 250), dsp.make_ir(3.0, np.random.default_rng(self.seed),
                                                                         bright=4500, dark=1500))
        out = self.mix + wet_d * 0.5 + wet_r * 0.3
        out = self.post(out)
        fade = int(6 * SR)
        out[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
        return dsp.master(out, target_rms_db=-11.0)

    def describe(self):
        lines = [f"Twisted full-on (Mandragora-inspired) — {BPM} BPM — {th.note_name(self.base_root)} phrygian "
                 f"dominant → {th.note_name(self.base_root + 1)} at bar {self.mod_bar} — {self.bars} bars "
                 f"({self.bars * self.bar / 60:.1f} min)"]
        for name, s, n, _ in self.sections:
            t = s * self.bar
            lines.append(f"  {int(t // 60)}:{int(t % 60):02d}  {name:<10} {n:>3} bars")
        return "\n".join(lines)
