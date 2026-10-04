"""'Journey' — a through-composed psytrance tone poem in nine chapters.

Nothing is looped. One continuous energy curve drives the rhythm section; one
melody, grown from a single seed motif, is developed through the whole piece and
handed between ney flute, lead, chant and duets. Every 2 bars one or two things
change (orchestration, bass rhythm, percussion, counter-lines) so the music flows
instead of switching. Tempo drifts 138 -> 150 -> 140 BPM.
"""
import numpy as np
from . import dsp, theory as th, instruments as ins
from .dsp import SR
from .song import place

ROOT = 30  # F#1

CHAPTERS = [
    dict(name="temple", bars=12, mode="phrygian_dominant", tonic=0, e=[(0, 0.03), (1, 0.24)], bpm=(138, 139),
         chords=[0, 0, 1, 0, 6, 0], follow=False, carriers=["ney", "ney", "chant"]),
    dict(name="path", bars=16, mode="phrygian_dominant", tonic=0, e=[(0, 0.25), (1, 0.5)], bpm=(139, 143),
         chords=[0, 6, 0, 1, 0, 6, 1, 0], follow=False, carriers=["ney", "ney", "lead"]),
    dict(name="forest", bars=20, mode="aeolian", tonic=0, e=[(0, 0.5), (0.5, 0.62), (1, 0.72)], bpm=(143, 146),
         chords=[0, 5, 6, 0, 3, 5, 2, 6, 4, 0], follow=False, carriers=["lead", "ney", "duet"], acid=True),
    dict(name="ascent", bars=16, mode="aeolian", tonic=5, e=[(0, 0.72), (1, 0.9)], bpm=(146, 147),
         chords=[0, 5, 3, 6, 0, 5, 6, 4], follow=True, carriers=["lead", "duet"], acid=True),
    dict(name="storm", bars=20, mode="hungarian_minor", tonic=0, e=[(0, 0.88), (0.45, 1.0), (1, 0.62)],
         bpm=(147, 150), chords=[0, 1, 0, 4, 0, 1, 5, 4, 1, 0], follow=False, carriers=["lead", "ney", "duet"],
         acid=True, triplets=True),
    dict(name="clearing", bars=16, mode="dorian", tonic=-2, e=[(0, 0.6), (0.5, 0.4), (1, 0.46)], bpm=(149, 146),
         chords=[0, 3, 6, 0, 3, 4, 0, 1], follow=True, carriers=["ney", "chant", "duet"]),
    dict(name="ritual", bars=20, mode="phrygian_dominant", tonic=0, e=[(0, 0.46), (1, 1.0)], bpm=(146, 149),
         chords=[0, 0, 1, 0, 6, 0, 5, 6, 1, 1], follow=False, carriers=["ney", "lead", "duet"], acid=True),
    dict(name="revelation", bars=20, mode="phrygian_dominant", tonic=1, e=[(0, 1.0), (0.6, 0.95), (1, 0.78)],
         bpm=(149, 149), chords=[0, 1, 6, 0, 5, 6, 1, 0, 6, 0], follow=True, carriers=["duet", "lead", "duet"],
         acid=True, choir=True),
    dict(name="return", bars=16, mode="phrygian_dominant", tonic=0, e=[(0, 0.74), (0.6, 0.3), (1, 0.0)],
         bpm=(148, 140), chords=[0, 1, 0, 6, 0, 1, 0, 0], follow=False, carriers=["ney", "ney", "chant"]),
]
# smooth swells / impacts / tom rolls at the turning points of the story
RISES = dict(forest=4, ascent=4, ritual=8)  # riser + tom roll over the last N bars of these chapters
SWELL_AT = ("ascent", "storm", "revelation")  # soft impact at chapter start
FALLS = ("clearing", "return")  # long downlifter at chapter start

MOTIF = [(0, 1, 4), (1, 0.5, 5), (1.5, 0.5, 4), (2, 1, 2), (3, 0.5, 1), (3.5, 0.5, 0)]  # beat, len, degree
MID_RHYTHMS = [[1, 1, 1, 1], [1.5, 0.5, 1, 1], [0.5, 0.5, 1, 2], [1, 0.5, 0.5, 2], [2, 1, 1],
               [0.75, 0.75, 0.5, 2], [1, 1, 2], [0.5, 0.5, 0.5, 0.5, 2]]


class Journey:
    CHAPTERS, RISES, SWELL_AT, FALLS, MOTIF = CHAPTERS, RISES, SWELL_AT, FALLS, MOTIF
    SLOW_CARRIERS = ("ney", "chant")   # carriers that play slow/mid lines
    ALWAYS_SLOW = ()                   # carriers that only ever play slow lines
    NEY_COUNTER_WITH = ("lead", "chant")
    LAYERS = ("r_kick", "r_bass", "r_low_drones", "r_toms", "r_didge", "r_acid", "r_melody", "r_pad", "r_fx")
    MASTER_RMS = -11.5
    DYN_DB, DYN_FULL = -10.0, 0.65  # macro dynamics: gain at E=0, energy where full level is reached

    def __init__(self, seed=7, root=ROOT):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.root = root
        self._timeline()
        self._orchestrate()
        self._compose()

    # ================================================================== timeline
    def _timeline(self):
        rows = []
        for ci, ch in enumerate(self.CHAPTERS):
            for i in range(ch["bars"]):
                f = i / max(ch["bars"] - 1, 1)
                xs, ys = zip(*ch["e"])
                rows.append(dict(ch=ci, i=i, f=f, e=float(np.interp(f, xs, ys)),
                                 bpm=ch["bpm"][0] + (ch["bpm"][1] - ch["bpm"][0]) * f,
                                 chord=ch["chords"][min(i // 2, len(ch["chords"]) - 1)]))
        self.rows = rows
        self.bars = len(rows)
        E = np.array([r["e"] for r in rows])
        E = E + 0.035 * np.sin(2 * np.pi * np.arange(self.bars) / 8)  # breathing
        E = np.convolve(np.pad(E, 1, mode="edge"), [0.25, 0.5, 0.25], "valid")
        self.E = np.clip(E, 0, 1)
        self.bpm = np.array([r["bpm"] for r in rows])
        self.t0 = np.concatenate([[0.0], np.cumsum(240.0 / self.bpm)])
        self.n = int((self.t0[-1] + 8.0) * SR)
        self.chap_start = {}
        for b, r in enumerate(rows):
            self.chap_start.setdefault(self.CHAPTERS[r["ch"]]["name"], b)

    def ch(self, bar):
        return self.CHAPTERS[self.rows[min(bar, self.bars - 1)]["ch"]]

    def scale(self, bar):
        return th.SCALES[self.ch(bar)["mode"]]

    def tonic(self, bar):
        return self.root + self.ch(bar)["tonic"]

    def chord(self, bar):
        return self.rows[min(bar, self.bars - 1)]["chord"]

    def bl(self, bar):
        return 60.0 / self.bpm[min(bar, self.bars - 1)]

    def pos(self, bar, beats=0.0):
        while beats >= 4:
            bar, beats = bar + 1, beats - 4
        if bar >= self.bars:
            t = self.t0[-1] + (bar - self.bars) * 4 * self.bl(self.bars - 1) + beats * self.bl(self.bars - 1)
        else:
            t = self.t0[bar] + beats * self.bl(bar)
        return int(t * SR)

    def curve(self, per_bar):
        xs = np.append(self.t0[:-1], self.t0[-1]) * SR
        return np.interp(np.arange(self.n), xs, np.append(per_bar, per_bar[-1]))

    def note(self, bar, d, base=36, lo=29, hi=44):
        m = self.tonic(bar) + base + th.deg(self.scale(bar), d)
        while m > self.root + hi:
            m -= 12
        while m < self.root + lo:
            m += 12
        return m

    # ================================================================== orchestration
    def _orchestrate(self):
        """Per 2-bar unit state; 1-2 dimensions change per unit, more at chapter starts."""
        rng = self.rng
        self.units = []
        st = dict(carrier="ney", counter="none", bassvar=0, tomgen=0, didgevar=0)
        for u in range(0, self.bars, 2):
            ch = self.ch(u)
            e = self.E[u]
            new_ch = self.rows[u]["i"] < 2
            dims = ["counter", "bassvar", "tomgen", "didgevar"]
            if u % 4 == 0:
                dims += ["carrier", "carrier"]
            k = 3 if new_ch else int(rng.choice([1, 2, 2]))
            change = set(rng.choice(dims, size=min(k, len(dims)), replace=False))
            if new_ch:
                change.add("carrier")
            if "carrier" in change:
                opts = [c for c in ch["carriers"] if c != st["carrier"]] or ch["carriers"]
                st["carrier"] = str(rng.choice(opts))
            if st["carrier"] not in ch["carriers"]:
                st["carrier"] = ch["carriers"][0]
            if "counter" in change or (st["counter"] == "ney" and st["carrier"] in ("ney", "duet")):
                st["counter"] = str(rng.choice(self._counter_opts(st, ch)))
            for d in ("bassvar", "tomgen", "didgevar"):
                if d in change:
                    st[d] += 1
            self.units.append(dict(st, e=e))

    def _counter_opts(self, st, ch):
        opts = ["none", "choir"]
        if st["carrier"] in self.NEY_COUNTER_WITH:
            opts += ["ney", "ney"]
        if ch.get("choir"):
            opts += ["choir"]
        return opts

    def _counter_events(self, u, bar, c0, c1):
        rng = self.rng
        out = []
        if u["counter"] == "ney":
            for t, ln, d, g in self._slow_unit(int(rng.choice([0, 2, -1])), c0, c1):
                br = bar + int(t // 4)
                if ln >= 1 and br < self.bars:
                    out.append((br, t % 4, ln, d - 2, "ney"))
        elif u["counter"] == "choir":
            for k in range(2):
                if bar + k < self.bars:
                    c = self.chord(bar + k)
                    out += [(bar + k, 0.0, 4.0, d, "choir") for d in (c, c + 2, c + 4)]
        return out

    def unit(self, bar):
        return self.units[min(bar // 2, len(self.units) - 1)]

    # ================================================================== melody
    def _snap(self, d, c):
        for off in (0, -1, 1, -2, 2):
            if (d + off - c) % 7 in (0, 2, 4):
                return d + off
        return d

    def _transform(self, cell, op):
        rng = self.rng
        if op == "seq":
            k = int(rng.choice([1, -1, 2, -2]))
            return [(b, ln, d + k) for b, ln, d in cell]
        if op == "inv":
            p = cell[0][2]
            return [(b, ln, 2 * p - d) for b, ln, d in cell]
        if op == "retro":
            ds = [d for _, _, d in cell][::-1]
            return [(b, ln, ds[j]) for j, (b, ln, _) in enumerate(cell)]
        if op == "frag":
            half = [x for x in cell if x[0] < 2] or cell[:2]
            k = int(rng.choice([1, -1, 2]))
            return half + [(b + 2, ln, d + k) for b, ln, d in half if b + 2 < 4]
        if op == "rhythm":
            out = []
            for b, ln, d in cell:
                if ln >= 1 and rng.random() < 0.6:
                    out += [(b, ln / 2, d), (b + ln / 2, ln / 2, d + int(rng.choice([1, -1])))]
                else:
                    out.append((b, ln, d))
            return out
        return [x for x in cell]

    def _walk_bar(self, start, c_next, rhythms):
        rng = self.rng
        rhythm = rhythms[int(rng.integers(len(rhythms)))]
        out, b, d = [], 0.0, start
        for j, ln in enumerate(rhythm):
            d = int(np.clip(d + rng.choice([1, -1, 1, -1, 2, -2]), -3, 9))
            if j == len(rhythm) - 1:
                d = self._snap(d, c_next)
            out.append((b, ln, d))
            b += ln
        return out

    def _drive_bar(self, c, start):
        rng = self.rng
        kind = str(rng.choice(["turn", "arp", "pedal", "motif", "run"]))
        out = []
        if kind == "turn":
            d = start
            for k in range(4):
                for j, off in enumerate((0, 1, 0, -1)):
                    out.append((k + j * 0.25, 0.25, d + off))
                d += int(rng.choice([1, -1, 2]))
        elif kind == "arp":
            tones = [c, c + 2, c + 4, c + 7, c + 4, c + 2]
            for j in range(16):
                out.append((j * 0.25, 0.25, tones[j % len(tones)]))
        elif kind == "pedal":
            d = c + 7
            for j in range(16):
                out.append((j * 0.25, 0.25, c if j % 2 else d))
                if j % 2:
                    d -= 1
        elif kind == "motif":
            k = int(rng.choice([1, -2, 2]))
            for rep in range(2):
                for b, ln, dd in self.MOTIF:
                    out.append((rep * 2 + b / 2, ln / 2, self._snap(c, c) + dd - 4 + rep * k))
        else:
            d = start
            for j in range(16):
                out.append((j * 0.25, 0.25 if j % 4 != 3 else 0.25, d))
                d += 1 if j < 8 else -1
        # merge some pairs into 8ths for groove
        merged, j = [], 0
        while j < len(out):
            if j + 1 < len(out) and rng.random() < 0.25 and out[j][1] == 0.25:
                merged.append((out[j][0], 0.5, out[j][2]))
                j += 2
            else:
                merged.append(out[j])
                j += 1
        return merged

    def _slow_unit(self, start, c, c_next, theme=False):
        """8 beats of slow, ornamented line."""
        rng = self.rng
        if theme:  # the seed motif in augmentation
            return [(b * 2, ln * 2, d, ln >= 1) for b, ln, d in self.MOTIF]
        out, t, d = [], float(rng.choice([0, 0, 0.5, 1])), start
        while t < 7:
            r = rng.random()
            if r < 0.12:
                t += 1
                continue
            if r < 0.32:  # ornamental turn
                step = float(rng.choice([0.5, 1 / 3]))
                direction = int(rng.choice([1, -1]))
                for _ in range(int(rng.choice([3, 4]))):
                    out.append((t, step, d, False))
                    t += step
                    d = int(np.clip(d + direction, -3, 9))
            ln = float(rng.choice([1, 1.5, 2, 3, 4]))
            ln = min(ln, 8 - t)
            if ln < 0.5:
                break
            dd = self._snap(d, c if t < 4 else c_next) if ln >= 2 else d
            out.append((t, ln, dd, bool(rng.random() < 0.4)))
            t += ln
            d = int(np.clip(dd + rng.choice([1, -1, 1, -1, 2, -2, 3]), -3, 9))
        return out

    def _compose(self):
        """The single melody line + counter-lines, as absolute events."""
        rng = self.rng
        self.melody = []   # (bar, beat, len, degree, grace, carrier)
        self.counter = []  # (bar, beat, len, degree, kind)
        cell = list(self.MOTIF)
        last = 4
        for ui, u in enumerate(self.units):
            bar = ui * 2
            if bar >= self.bars:
                break
            c0, c1 = self.chord(bar), self.chord(bar + 1)
            first = self.rows[bar]["i"] < 2
            carrier, e = u["carrier"], u["e"]
            if carrier in self.SLOW_CARRIERS:
                style = "slow" if e < 0.62 or carrier in self.ALWAYS_SLOW else "mid"
            else:
                style = "mid" if e < 0.8 else "drive"
            if style == "slow":
                notes = self._slow_unit(last, c0, c1, theme=first and ui % 3 != 2)
                evs = [(bar + int(b // 4), b % 4, ln, d, g) for b, ln, d, g in notes]
            elif style == "mid":
                if first:
                    a = [(b, ln, d - 4 + self._snap(4, c0)) for b, ln, d in self.MOTIF]
                else:
                    a = self._transform(cell, str(rng.choice(["seq", "inv", "retro", "frag", "rhythm", "seq"])))
                    a = [(b, ln, self._snap(d, c0) if b in (0, 2) else d) for b, ln, d in a]
                cell = a
                bnotes = self._walk_bar(a[-1][2], c1, MID_RHYTHMS)
                evs = [(bar, b, ln, d, ln >= 1.5 and rng.random() < 0.4) for b, ln, d in a] + \
                      [(bar + 1, b, ln, d, False) for b, ln, d in bnotes]
            else:
                a = self._drive_bar(c0, last)
                b2 = self._drive_bar(c1, a[-1][2])
                evs = [(bar, b, ln, d, False) for b, ln, d in a] + [(bar + 1, b, ln, d, False) for b, ln, d in b2]
            evs = [(br, b, ln, int(np.clip(d, -4, 10)), g) for br, b, ln, d, g in evs if br < self.bars]
            if evs:
                last = evs[-1][3]
            self.melody += [(br, b, ln, d, g, carrier) for br, b, ln, d, g in evs]
            self.counter += self._counter_events(u, bar, c0, c1)

    # ================================================================== mix plumbing
    def add(self, buf, gain=1.0, rev=0.0, dly=0.0, sc=0.0, cut=None, hp=None, lp=None, chorus=False):
        if cut is not None:
            fc = 120.0 * 2 ** (np.clip(cut, 0, 1) * 7.3)
            buf = np.stack([dsp.filt(buf[:, i], "lp", fc, 0.8, 256) for i in range(2)], axis=1)
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

    def lvl(self, lo, width):
        return np.clip((self.E - lo) / width, 0, 1)

    # ================================================================== rhythm section
    def r_kick(self):
        p = lambda b: dict(len=1.1 * self.bl(b) / 4, f0=210, pdecay=0.022, click=0.3, drive=2.2, tail=0.38)
        cache = {}
        buf, hits = self.track(), []
        kl = self.lvl(0.16, 0.14)
        for bar in range(self.bars):
            if kl[bar] <= 0:
                continue
            key = (self.tonic(bar), round(self.bl(bar), 3))
            if key not in cache:
                t_ = self.tonic(bar)
                cache[key] = ins.kick(dsp.midi_hz(t_ if 28 <= t_ <= 33 else self.root), p(bar), self.rng)
            beats = (0.0, 2.0) if self.E[bar] < 0.3 else (0.0, 1.0, 2.0, 3.0)  # heartbeat -> four on the floor
            for bt in beats:
                p0 = self.pos(bar, bt)
                place(buf, cache[key], p0, kl[bar])
                if kl[bar] > 0.3:
                    hits.append(p0)
        self.sc_env = dsp.sidechain_env(self.n, hits, 1.0, 0.29)
        self.add(buf, 1.0, cut=self.curve(np.clip((self.E - 0.12) / 0.33, 0.25, 1)))

    def _bass_bar(self, kind, motif, fill):
        notes = []
        for b in range(4):
            if kind == "triplet":
                notes += [(b + k / 3, 0, 1.0, 0.25) for k in (1, 2)]
                continue
            steps = {"roll": (1, 2, 3), "gallop": (2, 3), "push": (1, 2, 3), "oct": (1, 2, 3),
                     "acid": (1, 2, 3), "offroll": (1, 3), "walk": (1, 2, 3)}[kind]
            for s in steps:
                semi = 0
                if kind == "oct" and s == 3 and b % 2 == 1:
                    semi = 12
                if kind == "acid":
                    semi = motif[(b * 3 + s) % len(motif)]
                if kind == "walk":
                    semi = motif[b] if s == 3 else 0
                vel = 0.8 if kind == "push" and s == 1 else 1.0
                notes.append((b + s / 4, semi, vel, 0.24 if kind in ("gallop", "offroll") else 0.2))
        if fill == "up":
            notes = [x for x in notes if x[0] < 3] + [(3 + k / 8, k * 2, 0.85, 0.1) for k in range(1, 8)]
        elif fill == "turn":
            notes = [(t, (7 if t >= 3 else s), v, d) for t, s, v, d in notes]
        return notes

    def r_bass(self):
        rng = self.rng
        buf = self.track()
        cache = {}
        bl_ = self.lvl(0.27, 0.12)
        walk = np.cumsum(rng.normal(0, 0.12, self.bars))
        walk -= np.convolve(walk, np.ones(9) / 9, "same")
        sounds = dict(
            warm=dict(wave="saw", base=120, peak=1600, env_decay=0.05, res=1.3, sub_lvl=0.75, drive=1.6,
                      amp_decay=0.16, sustain=0.6, growl=0.15),
            normal=dict(wave="saw", base=140, peak=2600, env_decay=0.04, res=1.6, sub_lvl=0.7, drive=2.0,
                        amp_decay=0.13, sustain=0.55, growl=0.25),
            dark=dict(wave="saw", base=110, peak=3200, env_decay=0.03, res=2.6, sub_lvl=0.7, drive=2.6,
                      amp_decay=0.11, sustain=0.5, growl=0.35),
        )
        plan = None
        for bar in range(self.bars):
            u = self.unit(bar)
            e = self.E[bar]
            ch = self.ch(bar)
            if bar % 2 == 0:
                if ch.get("triplets") and e > 0.8:
                    pool = ["triplet", "roll", "acid", "triplet"]
                elif e < 0.42:
                    pool = ["gallop", "offroll"]
                elif e < 0.6:
                    pool = ["gallop", "roll", "walk", "offroll"]
                elif e < 0.85:
                    pool = ["roll", "oct", "push", "walk", "acid"]
                else:
                    pool = ["roll", "oct", "acid", "push"]
                r2 = np.random.default_rng(self.seed * 1000 + u["bassvar"] * 7 + bar // 8)
                kind = str(r2.choice(pool))
                motif = [int(r2.choice([0, 0, 0, 1, 12, -2, 7, 0, 3])) for _ in range(12)]
                fill = str(rng.choice(["none", "none", "up", "turn"])) if e > 0.5 else "none"
                plan = (kind, motif, fill)
            if bl_[bar] <= 0:
                continue
            kind, motif, fill = plan
            snd = "warm" if e < 0.5 else ("dark" if ch["mode"] == "hungarian_minor" else "normal")
            morph = float(np.clip(0.45 + 1.1 * e + walk[bar], 0.4, 1.8))
            morph = round(morph * 4) / 4
            base = self.tonic(bar)
            if ch["follow"]:
                base += th.deg(self.scale(bar), self.chord(bar))
            while base > self.root + 9:
                base -= 12
            while base < self.root - 3:
                base += 12
            notes = self._bass_bar(kind, motif, fill if bar % 2 == 1 else "none")
            if bar % 2 == 0 and rng.random() < 0.5:  # one-off pitch blip
                j = int(rng.integers(len(notes)))
                t, _, v, d = notes[j]
                notes[j] = (t, int(rng.choice([12, 7, 1, -2])), v, d)
            for t, semi, vel, d in notes:
                m = base + semi
                dur = d * self.bl(bar)
                key = (m, round(dur, 3), snd, morph)
                if key not in cache:
                    p = dict(sounds[snd], peak=sounds[snd]["peak"] * morph,
                             env_decay=sounds[snd]["env_decay"] * (0.75 + 0.25 * morph))
                    cache[key] = ins.rich_bass(dsp.midi_hz(m), dur, p)
                place(buf, cache[key], self.pos(bar, t), bl_[bar] * vel)
        self.add(buf, 0.72, cut=self.curve(np.clip((self.E - 0.2) / 0.4, 0.2, 1)))

    def r_low_drones(self):
        """Tanpura (always) + reese (when the rolling bass is absent)."""
        rng = self.rng
        tan, rs = self.track(), self.track()
        cache = {}
        bass_lv = self.lvl(0.27, 0.12)
        for bar in range(self.bars):
            r = self.tonic(bar)
            lv = 0.45 + 0.55 * (1 - self.E[bar])
            for j, bt in enumerate((0.0, 2.0)):
                k = (bar % 2) * 2 + j
                m = [r + 19, r + 24, r + 24, r + 12][k]
                if m not in cache:
                    cache[m] = ins.tanpura(m, 5.0, rng)
                place(tan, cache[m], self.pos(bar, bt), lv, [-0.4, 0.2, 0.4, -0.1][k])
            rl = 0.85 * (1 - bass_lv[bar]) * min(1.0, 0.35 + self.E[bar] / 0.3)
            if rl > 0.05 and bar % 2 == 0:
                c = self.chord(bar)
                m = self.tonic(bar) + 12 + th.deg(self.scale(bar), c)
                while m > self.root + 19:
                    m -= 12
                place(rs, ins.reese(m, 2 * 4 * self.bl(bar), rng), self.pos(bar), rl)
        self.add(tan, 0.45, rev=0.35, sc=0.35, hp=90, lp=5000)
        self.add(rs, 0.35, rev=0.1)

    def r_toms(self):
        """Tribal toms whose pattern evolves (keep ~65%, mutate the rest) every 2 bars;
        density follows the energy curve. Fills and rolls at turning points."""
        rng = self.rng
        buf = self.track()
        pat = []
        cache = {}

        def tom(bar, step, dec):
            key = (self.tonic(bar), step, dec)
            if key not in cache:
                cache[key] = ins.tom(dsp.midi_hz(self.tonic(bar) + 24 + step), dec, rng)
            return cache[key]

        roll_bars = set()
        for name, nb in self.RISES.items():
            s = self.chap_start[name] + next(c["bars"] for c in self.CHAPTERS if c["name"] == name)
            roll_bars |= set(range(s - nb, s))
        for bar in range(0, self.bars, 2):
            e = self.E[bar]
            dens = 0.05 + 0.33 * e
            if e < 0.2:
                pat = [(0, 0, 1.0), (3, 0, 0.6), (16, 0, 1.0), (19, 0, 0.6)]  # heartbeat: lub-dub
            else:
                pat = [x for x in pat if rng.random() < 0.65]
                have = {x[0] for x in pat}
                for s in range(32):
                    if s not in have and rng.random() < dens * (1.6 if s % 2 == 0 else 0.6):
                        pat.append((s, int(rng.choice([0, 0, 5, 10])), float(rng.uniform(0.55, 1.0))))
            lv = 0.5 + 0.5 * min(e * 2, 1)
            for s, which, v in pat:
                b = bar + s // 16
                if b >= self.bars or b in roll_bars:
                    continue
                place(buf, tom(b, which, 0.2 if which == 0 else 0.15), self.pos(b, (s % 16) / 4), lv * v,
                      {0: -0.25, 5: 0.35, 10: 0.55}[which])
            fb = bar + 1  # phrase-end fill every 4 bars once things move
            if e > 0.45 and fb % 4 == 3 and fb not in roll_bars and fb < self.bars:
                kind = int(rng.integers(3))
                for j, s in enumerate((12, 13, 14, 15)):
                    st = [9, 6, 3, 0][j] if kind == 0 else ([0, 3, 6, 9][j] if kind == 1 else [7, 0, 7, 0][j])
                    place(buf, tom(fb, st, 0.13), self.pos(fb, s / 4), 0.7, 0.5 - 0.33 * j)
        for name, nb in self.RISES.items():  # accelerating, rising tom rolls into the turning points
            end = self.chap_start[name] + next(c["bars"] for c in self.CHAPTERS if c["name"] == name)
            first = end - nb
            for b in range(nb):
                left = nb - b
                div = 2 if left > 2 else (4 if left == 2 else 8)
                for k in range(4 * div):
                    t = b * 4 + k / div
                    x = t / (nb * 4)
                    st = int(round(x * 12))
                    place(buf, tom(first + b, st, 0.1), self.pos(first + b, k / div), 0.15 + 0.6 * x ** 1.6,
                          0.3 * np.sin(t * 3))
        self.add(buf, 0.3, rev=0.2, dly=0.05, hp=55, lp=8000)

    def r_didge(self):
        rng = self.rng
        buf = self.track()
        lv = np.clip(1 - np.abs(self.E - 0.55) / 0.3, 0, 1)
        cache = {}
        acc = None
        for bar in range(self.bars):
            if bar % 2 == 0:
                u = self.unit(bar)
                r2 = np.random.default_rng(self.seed * 77 + u["didgevar"])
                dens = r2.uniform(0.3, 0.5)
                acc = [tuple((s / 4, round(float(r2.uniform(0.5, 1.0)), 1)) for s in range(16)
                             if (s % 4 != 0 and r2.random() < dens) or s % 8 == 6) for _ in range(2)]
            if lv[bar] <= 0.02:
                continue
            a = acc[bar % 2]
            key = (self.tonic(bar), a, round(self.bl(bar), 3))
            if key not in cache:
                cache[key] = ins.didgeridoo(self.tonic(bar) + 12, 4 * self.bl(bar), a, rng)
            place(buf, cache[key], self.pos(bar), lv[bar], 0.1 * np.sin(bar))
        self.add(buf, 0.45, rev=0.15, dly=0.06, sc=0.4, hp=70)

    def r_acid(self):
        rng = self.rng
        buf = self.track()
        lvl = np.array([self.lvl(0.52, 0.15)[b] if self.ch(b).get("acid") else 0.0 for b in range(self.bars)])
        lvl = np.convolve(np.pad(lvl, 2, mode="edge"), np.ones(5) / 5, "valid")
        cfg = dict(steps=13, wave="saw", res=3.6, envmod=2.0, decay=0.11, drive=2.2, rest_p=0.22, slide_p=0.3,
                   accent_p=0.25, accent_mod=0.6)
        seqs = {}
        for b0 in range(0, self.bars, 4):  # 4-bar chunks so tempo drift stays locked
            if lvl[b0:b0 + 4].max() <= 0.02:
                continue
            ch = self.ch(b0)
            key = ch["name"]
            if key not in seqs:
                seqs[key] = [th.acid_seq(dict(cfg, steps=int(rng.choice([11, 13, 14, 15]))), self.scale(b0), rng)]
            vers = seqs[key]
            vers.append(th.mutate(vers[-1], self.scale(b0), rng, int(rng.integers(1, 3))))
            nb = min(4, self.bars - b0)
            s0 = self.pos(b0)
            nn = self.pos(b0 + nb) - s0
            step = nn / (nb * 16)
            L = len(vers[0])
            gi0 = sum(c["bars"] for c in self.CHAPTERS[:self.rows[b0]["ch"]])
            e_curve = np.interp(np.arange(nn + int(0.3 * SR)), [0, nn], [self.E[b0], self.E[min(b0 + nb, self.bars - 1)]])
            fc = 170 * (2400 / 170) ** np.clip((e_curve - 0.45) / 0.55, 0, 1)

            def steps(i, vers=vers, b0=b0, gi0=gi0):
                gi = (b0 - gi0) * 16 + i
                v = vers[min(len(vers) - 1, 1 + i // 32)]
                return v[gi % L]

            y = ins.acid_line(steps, nn + int(0.3 * SR), step, self.tonic(b0) + 12, fc, cfg, rng)
            g = np.interp(np.arange(len(y)), [0, nn], [lvl[b0], lvl[min(b0 + nb, self.bars - 1)]])
            fade = np.ones(len(y))
            fade[nn:] = np.linspace(1, 0, len(y) - nn)
            fade[: int(0.004 * SR)] = np.linspace(0, 1, int(0.004 * SR))
            pn = 0.2 * np.sin(2 * np.pi * (s0 + np.arange(len(y))) / SR / 5.3)
            place(buf, np.stack([y * g * fade * (1 - pn), y * g * fade * (1 + pn)], axis=1), s0)
        self.add(buf, 0.17, rev=0.12, dly=0.18, sc=0.3, hp=100, lp=6000)

    # ================================================================== melodic voices
    def r_melody(self):
        rng = self.rng
        lead, ney_events, chant = self.track(), [], self.track()
        lcache = {}
        for bar, b, ln, d, g, carrier in self.melody:
            m = self.note(bar, d)
            dur = ln * self.bl(bar)
            if carrier in ("lead", "duet"):
                key = (m, round(dur, 2))
                if key not in lcache:
                    lcache[key] = ins.warm_lead(m, dur * 0.92, rng)
                place(lead, lcache[key], self.pos(bar, b), 1.0)
            if carrier == "ney":
                ney_events.append((bar, b, ln, m, g))
            if carrier == "duet" and ln >= 0.5:  # flute doubles an octave below
                mm = m - 12 if m - 12 >= self.root + 29 else m
                ney_events.append((bar, b, ln, mm, g))
            if carrier == "chant" and ln >= 1:
                x = ins.voice(m, dur * 0.95, [["a", "o"], ["o", "u", "a"], ["e", "a"], ["u", "a"]][int(rng.integers(4))], rng)
                place(chant, x, self.pos(bar, b), 1.0, rng.uniform(-0.2, 0.2))
        for bar, b, ln, d, kind in self.counter:
            if kind == "ney":
                ney_events.append((bar, b, ln, self.note(bar, d, lo=27), False))
            else:
                m = self.note(bar, d, base=36, lo=27, hi=40)
                x = ins.voice(m, ln * self.bl(bar) * 0.97, ["a", "o"] if d % 2 else ["o", "a"], rng)
                place(chant, x, self.pos(bar, b), 0.45, (d % 3 - 1) * 0.35)
        # ney: render contiguous runs as single breaths-connected phrases
        ney = self.track()
        ney_events.sort(key=lambda x: (x[0], x[1]))
        run = []

        def flush(run):
            if not run:
                return
            s0 = self.pos(run[0][0], run[0][1])
            end = self.pos(run[-1][0], run[-1][1]) + int(run[-1][2] * self.bl(run[-1][0]) * SR) + int(1.5 * SR)
            notes = []
            for bar, b, ln, m, g in run:
                st = self.pos(bar, b) - s0
                notes.append((st, int(ln * self.bl(bar) * SR * 0.97), m, g))
            place(ney, ins.ney_phrase(notes, end - s0, rng), s0, 1.0, rng.uniform(-0.25, 0.25))

        prev_end = None
        for ev in ney_events:
            st = self.pos(ev[0], ev[1])
            if prev_end is not None and st - prev_end > int(1.5 * SR) or (run and st < self.pos(run[-1][0], run[-1][1])):
                flush(run)
                run = []
            run.append(ev)
            prev_end = st + int(ev[2] * self.bl(ev[0]) * SR)
        flush(run)
        self.add(lead, 0.36, rev=0.28, dly=0.25, sc=0.5, hp=180, lp=6500, chorus=True)
        self.add(ney, 0.42, rev=0.5, dly=0.3, sc=0.2, hp=200)
        self.add(chant, 0.24, rev=0.55, dly=0.25, sc=0.25, hp=140, lp=6000)

    def r_pad(self):
        rng = self.rng
        buf = self.track()
        lv = np.clip(1.15 - 1.2 * self.E, 0.12, 0.9)
        for b in range(self.bars):
            if self.ch(b).get("choir"):
                lv[b] = max(lv[b], 0.5)
        cache = {}
        for bar in range(0, self.bars, 2):
            c = self.chord(bar)
            r = self.tonic(bar)
            dur = 2 * 4 * self.bl(bar)
            key = (r, self.ch(bar)["mode"], c, round(dur, 2))
            if key not in cache:
                sc = self.scale(bar)
                notes = [r + 24 + x for x in th.chord(sc, c, 4)] + [r + 12 + th.deg(sc, c)]
                notes = [n - 12 if n > self.root + 43 else n for n in notes]
                cache[key] = ins.pad_chord(notes, dur, dict(fc=1100, att=1.2, voices=5, lfo=9.0, rel=2.2), rng)
            place(buf, cache[key], self.pos(bar), lv[bar])
        self.add(buf, 1.0, rev=0.45, sc=0.5, hp=110, lp=4500, chorus=True,
                 cut=self.curve(np.clip(0.35 + 0.5 * self.E, 0, 1)))

    def r_fx(self):
        rng = self.rng
        buf = self.track()
        for bar in range(self.bars):
            e = self.E[bar]
            if 0.35 < e < 0.85 and rng.random() < 0.12:
                x = ins.gurgle(rng)
                place(buf, x / (np.abs(x).max() + 1e-9), self.pos(bar, int(rng.integers(0, 8)) * 0.5), 0.8,
                      rng.uniform(-0.7, 0.7))
        for name, nb in self.RISES.items():
            end = self.chap_start[name] + next(c["bars"] for c in self.CHAPTERS if c["name"] == name)
            dur = self.t0[end] - self.t0[end - nb]
            place(buf, ins.riser(dur, rng), self.pos(end - nb), 1.2)
        for name in self.SWELL_AT:
            s = self.chap_start[name]
            place(buf, ins.impact(rng), self.pos(s), 1.6)
            place(buf, ins.downlifter(4 * 4 * self.bl(s), rng), self.pos(s), 0.7)
        for name in self.FALLS:
            s = self.chap_start[name]
            place(buf, ins.downlifter(6 * 4 * self.bl(s), rng), self.pos(s), 0.9)
        self.add(buf, 0.3, rev=0.35, dly=0.2, lp=8000)

    # ================================================================== render
    def render(self, log=print):
        self.mix, self.rev, self.dly = self.track(), self.track(), self.track()
        for fn in (getattr(self, name) for name in self.LAYERS):
            log(f"  · {fn.__name__[2:]}")
            fn()
        log("  · fx returns + master")
        beat = 60.0 / float(np.median(self.bpm))
        wet_d = dsp.pingpong(self.dly, 0.75 * beat, fb=0.42, damp=2800)
        self.rev += wet_d * 0.3
        wet_r = dsp.reverb(dsp.static(self.rev, "hp", 250),
                           dsp.make_ir(3.4, np.random.default_rng(self.seed), bright=4500, dark=1500))
        out = self.mix + wet_d * 0.5 + wet_r * 0.32
        # macro dynamics: quiet, intimate low-energy passages; full level from E ~ 0.65 up
        g_db = self.DYN_DB * (1 - np.clip(self.E / self.DYN_FULL, 0, 1)) ** 1.3
        out *= (10 ** (self.curve(g_db)[: len(out)] / 20))[:, None]
        end = int((self.t0[-1] + 7.5) * SR)
        out = out[:end]
        fade = int(5 * SR)
        out[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
        return dsp.master(out, target_rms_db=self.MASTER_RMS)

    def describe(self):
        lines = [f"{type(self).__name__} — {self.bars} bars, {self.t0[-1] / 60:.1f} min, {self.bpm.min():.0f}-{self.bpm.max():.0f} BPM"]
        for ch in self.CHAPTERS:
            s = self.chap_start[ch["name"]]
            t = self.t0[s]
            lines.append(f"  {int(t // 60)}:{int(t % 60):02d}  {ch['name']:<11} "
                         f"{th.note_name(self.root + ch['tonic'] + 24)[:-1]:<3} {ch['mode']:<18} "
                         f"energy {self.E[s]:.2f}→{self.E[s + ch['bars'] - 1]:.2f}")
        return "\n".join(lines)
