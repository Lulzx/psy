"""'Mycelium' — an earthy psychedelic ceremony in eight chapters.

Inspired by the jungle-tribal full-on of Astrix (tight rolling bass, ethnic flutes,
tribal drums) and the dramatic, guitar-laced melodic writing of Infected Mushroom,
built on the Journey engine: one energy curve, one motif developed throughout,
a new orchestration every 2 bars. Earthy palette only: hand drums in Middle-Eastern
rhythms, udu, log drums, oud, throat singing, ney, didgeridoo, tanpura, wind and earth.
Tempo grows 132 -> 145 BPM and settles back.
"""
import numpy as np
from . import dsp, theory as th, instruments as ins
from .dsp import SR
from .song import place
from .journey import Journey

ROOT = 28  # E1 — deep, earthy home key

CHAPTERS = [
    dict(name="spores", bars=10, mode="phrygian_dominant", tonic=0, e=[(0, 0.0), (1, 0.2)], bpm=(132, 133),
         chords=[0, 0, 1, 0, 0], follow=False, carriers=["throat", "ney"], melt=0.35, nature=1.0),
    dict(name="mycelium", bars=16, mode="phrygian_dominant", tonic=0, e=[(0, 0.2), (1, 0.45)], bpm=(133, 138),
         chords=[0, 6, 0, 1, 0, 6, 1, 0], follow=False, carriers=["ney", "oud", "ney"], melt=0.2, nature=0.5,
         logs=True),
    dict(name="breathing walls", bars=16, mode="double_harmonic", tonic=0, e=[(0, 0.45), (0.5, 0.5), (1, 0.58)],
         bpm=(138, 141), chords=[0, 1, 0, 4, 3, 1, 0, 0], follow=False, carriers=["oud", "chant", "ney"],
         melt=1.0, nature=0.4, reverse=True),
    dict(name="deep jungle", bars=24, mode="dorian", tonic=0, e=[(0, 0.6), (0.5, 0.7), (1, 0.8)],
         bpm=(142, 144), chords=[0, 3, 0, 6, 0, 3, 4, 6, 3, 0, 6, 0], follow=False,
         carriers=["oud", "ney", "duet", "lead"], melt=0.25, nature=0.2, logs=True),
    dict(name="dissolution", bars=24, mode="phrygian_dominant", tonic=1, e=[(0, 0.82), (0.55, 1.0), (1, 0.86)],
         bpm=(145, 145), chords=[0, 1, 6, 0, 5, 1, 6, 0, 1, 0, 6, 0], follow=True,
         carriers=["lead", "duet", "oud", "lead"], melt=0.55, nature=0.0, choir=True, reverse=True),
    dict(name="afterglow", bars=16, mode="dorian", tonic=-2, e=[(0, 0.6), (0.5, 0.45), (1, 0.52)],
         bpm=(145, 142), chords=[2, 0, 3, 0, 6, 3, 1, 1], follow=True, carriers=["ney", "oud", "chant", "duet"],
         melt=0.5, nature=0.5),
    dict(name="grounding", bars=20, mode="phrygian_dominant", tonic=0, e=[(0, 0.55), (0.55, 0.85), (1, 0.6)],
         bpm=(143, 145), chords=[0, 5, 6, 0, 1, 0, 6, 0, 1, 0], follow=False,
         carriers=["oud", "lead", "ney", "duet"], melt=0.2, nature=0.1, logs=True),
    dict(name="return to soil", bars=14, mode="phrygian_dominant", tonic=0, e=[(0, 0.5), (0.5, 0.2), (1, 0.0)],
         bpm=(144, 134), chords=[0, 1, 0, 6, 0, 1, 0], follow=False, carriers=["throat", "ney"], melt=0.45,
         nature=1.0),
]

# Earthy seed motif: E F G# B G# — the hijaz colour, rising like something growing
MOTIF = [(0, 1.5, 0), (1.5, 0.5, 1), (2, 1, 2), (3, 0.5, 4), (3.5, 0.5, 2)]

# Darbuka rhythms on an 8th grid: D = doum, T = tek, S = slap, . = rest
RHYTHMS = dict(maqsum="DT.TD.T.", baladi="DD.TD.T.", saidi="DT.DD.T.", malfuf="D..T..T.",
               ayoub="D.TDT.D.", wahda="D...T.T.")


class Mycelium(Journey):
    CHAPTERS = CHAPTERS
    RISES = {"breathing walls": 4, "deep jungle": 8, "afterglow": 4}
    SWELL_AT = ("deep jungle", "dissolution", "grounding")
    MOTIF = MOTIF
    SLOW_CARRIERS = ("ney", "chant", "throat")
    ALWAYS_SLOW = ("throat", "chant")
    NEY_COUNTER_WITH = ("oud", "lead", "chant", "throat")
    LAYERS = ("r_kick", "r_bass", "r_low_drones", "r_hand_drums", "r_logs", "r_didge", "r_melody",
              "r_pad", "r_nature", "r_fx")
    MASTER_RMS = -11.5
    MASTER_LUFS = -10.6
    # A rock hollow at the edge of the forest: stone walls, earth floor, open sky.
    ROOM = dict(room=(20.0, 16.0, 9.0), absorb=(0.4, 0.3, 1.0))
    STAGE = dict(hand=dict(az=-8, dist=0.15), logs=dict(az=34, dist=0.45, width=0.8),
                 didge=dict(az=-40, dist=0.6, width=0.6, move=25), lead=dict(az=0, dist=0.35, width=1.2),
                 oud=dict(az=22, dist=0.25, width=0.9), ney=dict(az=-14, dist=0.1, move=20),
                 throat=dict(az=10, dist=0.7, width=0.8), chant=dict(az=0, dist=0.55, width=1.4),
                 tanpura=dict(az=-5, dist=0.4, width=1.3), pad=dict(dist=0.65, width=1.3),
                 frogs=dict(az=-20, dist=0.85, width=1.3), drops=dict(az=15, dist=0.5, width=1.2),
                 fx=dict(dist=0.5, width=1.2))
    REVERB = dict(rt60=3.0, hf_ratio=0.45, size=1.0)
    DYN_DB, DYN_FULL = -15.0, 0.85  # deeper valleys: full level only near the peaks

    def __init__(self, seed=5, root=ROOT):
        super().__init__(seed=seed, root=root)

    def _compose(self):
        """Eight-bar question/answer arcs, with a recognizable returning theme."""
        super()._compose()
        developed = []
        for bar in range(self.bars):
            local = self.rows[bar]["i"]
            carrier = self.unit(bar)["carrier"]
            # Theme returns at the beginning and midpoint of each eight-bar arc.
            if local % 8 in (0, 4):
                answering = local % 8 == 4
                for b, ln, d in self.MOTIF:
                    if answering and b >= 2:
                        d = {2: 1, 4: 0}.get(d, d)
                    d = self._snap(d, self.chord(bar)) if b in (0, 2) else d
                    developed.append((bar, b, ln, d, False, carrier))
            else:
                for ev in self.melody:
                    if ev[0] != bar:
                        continue
                    if local % 8 == 7:
                        # Space to inhale before the next question; preserve tails.
                        if ev[1] >= 2.5:
                            continue
                        ev = (ev[0], ev[1], min(ev[2], 2.5 - ev[1]), *ev[3:])
                    developed.append(ev)
        self.melody = developed

    def render(self, log=print):
        # Slow foreground activity envelope: backgrounds yield, never hard mute.
        activity = np.zeros(self.bars)
        for bar, b, ln, d, g, carrier in self.melody:
            if carrier in ("ney", "duet", "oud", "lead"):
                activity[bar] += ln / 4
        for bar, b, ln, d, kind in self.counter:
            if kind == "ney":
                activity[bar] += 0.4 * ln / 4
        activity = np.clip(activity, 0, 1)
        self.foreground = self.curve(activity)
        audio = super().render(log)
        del self.foreground
        return audio

    def add(self, buf, gain=1.0, rev=0.0, dly=0.0, **kw):
        layer = getattr(self, "active_layer", "")
        if layer in ("r_pad", "r_low_drones", "r_didge"):
            buf = buf * (1 - 0.26 * self.foreground)[:, None]
            gain *= 0.83 if layer == "r_low_drones" else 0.9
        super().add(buf, gain, rev=rev, dly=dly, **kw)

    def effect_returns(self):
        echoes = dsp.tempo_echo(self.dly, self.t0)
        self.rev += echoes * 0.18
        ambience = dsp.fdn_reverb(dsp.static(self.rev, "hp", 300), seed=self.seed + 92, **self.REVERB)
        ambience = dsp.eq(dsp.static(ambience, "lp", 9000), "hs", 3500, 5.0 * self.AIR)
        return self.mix + ambience * 0.42 + echoes * 0.38

    def human_pos(self, bar, beat, lane="drum"):
        """A consistent laid-back player groove plus small stroke deviations."""
        offbeat = int(round(beat * 4)) % 2
        offset = (0.005 + 0.004 * offbeat if lane == "drum" else 0.003)
        offset += self.rng.normal(0, 0.0025 if lane == "drum" else 0.0015)
        return max(0, self.pos(bar, beat) + int(offset * SR))

    def chap_curve(self, key):
        return np.array([self.ch(b).get(key, 0.0) for b in range(self.bars)], dtype=float)

    def _counter_opts(self, st, ch):
        opts = super()._counter_opts(st, ch)
        if st["carrier"] in ("ney", "lead", "throat", "chant"):
            opts += ["oudarp", "oudarp"]
        return opts

    def _counter_events(self, u, bar, c0, c1):
        if u["counter"] != "oudarp":
            return super()._counter_events(u, bar, c0, c1)
        rng = self.rng
        shape = [[0, 2, 4, 2], [0, 4, 7, 4, 2, 4], [0, 2, 4, 7], [4, 2, 0, 2]][int(rng.integers(4))]
        out = []
        for k in range(2):  # finger-picked broken chords in 8ths
            if bar + k >= self.bars:
                break
            c = self.chord(bar + k)
            for j in range(8):
                if rng.random() < 0.85:
                    out.append((bar + k, j * 0.5, 0.5, c + shape[(j + k) % len(shape)] - 7, "oud"))
        return out

    # ------------------------------------------------------------------ rhythm
    def r_kick(self):
        cache = {}
        buf, hits = self.track(), []
        kl = self.lvl(0.3, 0.15)
        for bar in range(self.bars):
            if kl[bar] <= 0:
                continue
            key = (self.tonic(bar), round(self.bl(bar), 3))
            if key not in cache:
                t_ = self.tonic(bar)
                p = dict(len=1.12 * self.bl(bar) / 4, f0=190, pdecay=0.026, click=0.2, drive=1.9, tail=0.42)
                cache[key] = [ins.kick(dsp.midi_hz(t_ if 27 <= t_ <= 33 else self.root), self.vary(p), self.rng)
                              for _ in range(4)]
            e = self.E[bar]
            beats = (0.0, 2.5) if e < 0.42 else (0.0, 1.0, 2.0, 3.0)  # dubby half-time -> four on the floor
            for bt in beats:
                p0 = self.pos(bar, bt)
                place(buf, cache[key][int(self.rng.integers(4))], p0, kl[bar])
                if kl[bar] > 0.3:
                    hits.append(p0)
        self.sc_env = dsp.sidechain_env(self.n, hits, 1.0, 0.3)
        self.add(buf, 0.86, cut=self.curve(np.clip((self.E - 0.25) / 0.3, 0.3, 1)))

    def r_bass(self):
        """Dub bass at low energy, Astrix-style tight rolling bass once the jungle opens."""
        rng = self.rng
        buf = self.track()
        cache = {}
        bl_ = self.lvl(0.2, 0.15)
        warm = dict(wave="saw", base=110, peak=1200, env_decay=0.06, res=1.2, sub_lvl=0.68, drive=1.5,
                    amp_decay=0.3, sustain=0.7, growl=0.12)
        tight = dict(wave="saw", base=130, peak=2400, env_decay=0.038, res=1.7, sub_lvl=0.58, drive=2.1,
                     amp_decay=0.12, sustain=0.55, growl=0.28)
        walk = np.cumsum(rng.normal(0, 0.12, self.bars))
        walk -= np.convolve(walk, np.ones(9) / 9, "same")
        plan = None
        for bar in range(self.bars):
            e = self.E[bar]
            u = self.unit(bar)
            if bar % 2 == 0:
                r2 = np.random.default_rng(self.seed * 1000 + u["bassvar"] * 7 + bar // 8)
                if e < 0.48:
                    # dub line: syncopated, long, melodic over two bars
                    slots = [(0.0, 1.5), (1.75, 0.5), (2.5, 1.0), (3.5, 0.5), (4.0, 1.0), (5.25, 0.75),
                             (6.0, 1.25), (7.5, 0.5)]
                    line = [(t, ln, int(r2.choice([0, 0, 0, 7, 12, -2, 3, 5]))) for t, ln in slots if r2.random() < 0.8]
                    plan = ("dub", line)
                else:
                    pool = ["roll", "roll", "gallop", "walk"] if e < 0.75 else ["roll", "oct", "push", "walk", "roll"]
                    kind = str(r2.choice(pool))
                    motif = [int(r2.choice([0, 0, 0, 1, 12, -2, 7, 0, 3])) for _ in range(12)]
                    fill = str(rng.choice(["none", "none", "up", "turn"])) if e > 0.6 else "none"
                    plan = (kind, motif, fill)
            if bl_[bar] <= 0:
                continue
            base = self.tonic(bar)
            if self.ch(bar)["follow"]:
                base += th.deg(self.scale(bar), self.chord(bar))
            while base > self.root + 9:
                base -= 12
            while base < self.root - 2:
                base += 12
            if plan[0] == "dub":
                notes = [(t - 4 * (bar % 2), semi, 1.0, ln) for t, ln, semi in plan[1] if 4 * (bar % 2) <= t < 4 * (bar % 2) + 4]
                snd = "warm"
            else:
                kind, motif, fill = plan
                notes = self._bass_bar(kind, motif, fill if bar % 2 == 1 else "none")
                snd = "tight"
                if bar % 2 == 0 and rng.random() < 0.45:
                    j = int(rng.integers(len(notes)))
                    t, _, v, d = notes[j]
                    notes[j] = (t, int(rng.choice([12, 7, 1, -2])), v, d)
            morph = round(float(np.clip(0.5 + 1.0 * e + walk[bar], 0.45, 1.6)) * 4) / 4
            for t, semi, vel, d in notes:
                m = base + semi
                dur = d * self.bl(bar)
                key = (m, round(dur, 3), snd, morph, int(rng.integers(3)))
                if key not in cache:
                    p0 = warm if snd == "warm" else tight
                    p = dict(p0, peak=p0["peak"] * morph, env_decay=p0["env_decay"] * (0.75 + 0.25 * morph))
                    cache[key] = ins.rich_bass(dsp.midi_hz(m), dur, self.vary(p, 0.5))
                place(buf, cache[key], self.pos(bar, t), bl_[bar] * vel)
        self.add(buf, 0.60, cut=self.curve(np.clip((self.E - 0.12) / 0.45, 0.25, 1)))

    def r_hand_drums(self):
        """Darbuka/djembe in maqsum, baladi, saidi... ghost notes and slaps grow with energy.
        The rhythm changes every few bars; heartbeat doums at the edges of the piece."""
        rng = self.rng
        buf = self.track()
        cache = {}

        def stroke(kind, bar, strength=0.8):
            hz = dsp.midi_hz(self.tonic(bar) + 12)
            strength = round(float(np.clip(strength, 0.2, 1.0)) * 4) / 4
            key = (kind, round(hz, 1), strength)
            if key not in cache:
                cache[key] = [ins.hand_drum(kind, hz, rng, strength=strength) for _ in range(8)]
            return cache[key][int(rng.integers(8))]

        roll_bars = set()
        for name, nb in self.RISES.items():
            end = self.chap_start[name] + next(c["bars"] for c in self.CHAPTERS if c["name"] == name)
            roll_bars |= set(range(end - nb, end))
        names = list(RHYTHMS)
        rhythm = "maqsum"
        for bar in range(self.bars):
            e = self.E[bar]
            u = self.unit(bar)
            if bar % 4 == 0:
                r2 = np.random.default_rng(self.seed * 31 + u["tomgen"])
                rhythm = str(r2.choice([n for n in names if n != rhythm]))
            if bar in roll_bars:
                continue
            lv = 0.55 + 0.45 * min(1.0, e * 1.6)
            if e < 0.12:  # heartbeat
                for bt, v in ((0.0, 1.0), (0.75, 0.6)):
                    place(buf, stroke("doum", bar), self.pos(bar, bt), 0.8 * v)
                continue
            for j, ch in enumerate(RHYTHMS[rhythm]):  # one 8th-note cycle per bar
                if ch == ".":
                    continue
                kind = {"D": "doum", "T": "tek", "S": "slap"}[ch]
                if kind == "tek" and rng.random() < 0.25 * e:
                    kind = "slap"
                place(buf, stroke(kind, bar, lv), self.human_pos(bar, j * 0.5), lv * rng.uniform(0.85, 1.0),
                      -0.25 if kind == "doum" else 0.3)
            # 16th ghost notes fill in as the energy rises
            for s in range(16):
                if s % 2 == 1 and rng.random() < 0.15 + 0.55 * e:
                    place(buf, stroke("ghost", bar, 0.3), self.human_pos(bar, s / 4), lv * rng.uniform(0.5, 0.9),
                          0.45 if s % 4 == 1 else 0.15)
            if bar % 4 == 3 and e > 0.4 and rng.random() < 0.7:  # flourish at the phrase end
                for k in range(6):
                    place(buf, stroke("tek" if k % 2 else "slap", bar, 0.5 + k / 12), self.human_pos(bar, 3.0 + k / 6), lv * (0.5 + k / 12), 0.4 - 0.15 * k)
        for name, nb in self.RISES.items():  # accelerating doum/tek rolls into turning points
            end = self.chap_start[name] + next(c["bars"] for c in self.CHAPTERS if c["name"] == name)
            first = end - nb
            for b in range(nb):
                left = nb - b
                div = 2 if left > 2 else (4 if left == 2 else 6)
                for k in range(4 * div):
                    x = (b * 4 + k / div) / (nb * 4)
                    kind = "doum" if k % div == 0 else "tek"
                    place(buf, stroke(kind, first + b, 0.3 + 0.7 * x), self.human_pos(first + b, k / div), 0.25 + 0.65 * x ** 1.5,
                          0.3 * np.sin(k))
        self.add(buf, 0.63, rev=0.18, dly=0.04, hp=50, lp=self.air(6000), src="hand")

    def r_logs(self):
        """Pitched wooden log-drum ostinato; mutates every 2 bars, grows denser with energy."""
        rng = self.rng
        buf = self.track()
        lv = np.array([1.0 if self.ch(b).get("logs") else 0.0 for b in range(self.bars)])
        lv = np.convolve(np.pad(lv, 2, mode="edge"), np.ones(5) / 5, "valid") * np.clip(self.E / 0.5, 0.3, 1)
        cache = {}
        pat = []
        for bar in range(self.bars):
            if bar % 2 == 0:
                pat = [x for x in pat if rng.random() < 0.6]
                have = {x[0] for x in pat}
                for s in range(16):
                    if s not in have and rng.random() < 0.12 + 0.18 * self.E[bar] and s % 4 != 0:
                        pat.append((s, int(rng.choice([0, 2, 4, 7, 4]))))
            if lv[bar] < 0.03:
                continue
            c = self.chord(bar)
            for s, d in pat:
                m = self.tonic(bar) + 24 + th.deg(self.scale(bar), c + d)
                while m > self.root + 31:
                    m -= 12
                if m not in cache:
                    cache[m] = [ins.log_drum(dsp.midi_hz(m), rng) for _ in range(3)]
                place(buf, cache[m][int(rng.integers(3))], self.human_pos(bar, s / 4), lv[bar] * rng.uniform(0.75, 1.0), 0.45 * np.sin(s * 0.9))
        self.add(buf, 0.58, rev=0.2, dly=0.15, sc=0.3, hp=120, lp=5000, src="logs")

    # ------------------------------------------------------------------ melody
    def r_melody(self):
        rng = self.rng
        lead, oud, chant = self.track(), self.track(), self.track()
        ney_events, throat_events = [], []
        lcache, ocache = {}, {}

        def pluck(m, dur, bar, b, vel, pan_):
            variant = int(rng.integers(4))
            stroke = 1 if int(round(b * 4)) % 2 == 0 else -1
            strength = round(float(np.clip(vel, 0.25, 1.0)) * 4) / 4
            key = (m, round(min(dur, 1.2), 2), variant, stroke, strength)
            if key not in ocache:
                ocache[key] = ins.oud(m, min(dur, 1.2), rng, strength=strength, stroke=stroke)
            place(oud, ocache[key], self.human_pos(bar, b, "oud"), vel * rng.uniform(0.92, 1.0), pan_)

        for bar, b, ln, d, g, carrier in self.melody:
            m = self.note(bar, d)
            dur = ln * self.bl(bar)
            if carrier == "lead":
                key = (m, round(dur, 2), int(rng.integers(2)))
                if key not in lcache:
                    lcache[key] = ins.warm_lead(m, dur * 0.92, rng)
                place(lead, lcache[key], self.pos(bar, b), 1.0)
            if carrier in ("oud", "duet"):
                if ln >= 1.5:  # tremolo picking on long notes
                    k = int(ln * 4)
                    for j in range(k):
                        pluck(m, 0.25 * self.bl(bar), bar, b + j * 0.25, 0.88 if j % 2 == 0 else 0.72, 0.15)
                else:
                    pluck(m, dur, bar, b, 1.0, 0.15)
            if carrier in ("ney", "duet"):
                mm = m if carrier == "ney" else (m - 12 if m - 12 >= self.root + 29 else m)
                if carrier == "ney" or ln >= 0.5:
                    ney_events.append((bar, b, ln, mm, g))
            if carrier == "throat":
                throat_events.append((bar, b, ln, m))
            if carrier == "chant" and ln >= 1:
                x = ins.voice(m, dur * 0.95, [["a", "o"], ["o", "u", "a"], ["u", "a"]][int(rng.integers(3))], rng)
                place(chant, x, self.pos(bar, b), 1.0, rng.uniform(-0.2, 0.2))
        for bar, b, ln, d, kind in self.counter:
            if kind == "ney":
                ney_events.append((bar, b, ln, self.note(bar, d, lo=27), False))
            elif kind == "oud":
                pluck(self.note(bar, d, base=36, lo=22, hi=36), ln * self.bl(bar), bar, b, 0.55, -0.35)
            else:
                m = self.note(bar, d, base=36, lo=27, hi=40)
                x = ins.voice(m, ln * self.bl(bar) * 0.97, ["a", "o"] if d % 2 else ["o", "a"], rng)
                place(chant, x, self.pos(bar, b), 0.45, (d % 3 - 1) * 0.35)
        ney = self._phrases(ney_events, lambda notes, n: ins.ney_phrase(notes, n, rng, air_amt=self.AIR))
        throat = self._phrases([(br, b, ln, m, False) for br, b, ln, m in throat_events],
                               lambda notes, n: ins.throat_phrase([(s, L, dsp.midi_hz(m)) for s, L, m, _ in notes], n,
                                                                  dsp.midi_hz(self.root + 12), rng), tail=2.5)
        meltc = self.curve(self.chap_curve("melt"))
        ney = dsp.melt(ney, 1.6 * meltc, seed=self.seed)
        self.add(lead, 0.39, rev=0.28, dly=0.25, sc=0.5, hp=180, lp=6000, chorus=True, src="lead")
        self.add(oud, 0.38, rev=0.16, dly=0.12, sc=0.2, hp=120, lp=self.air(5000), src="oud")
        # Echoes bloom in rests rather than doubling every syllable.
        for br, b, ln, m, g in ney_events:
            if ln < 0.75:
                continue
            start = self.pos(br, b)
            length = int(ln * self.bl(br) * SR)
            s = start + int(length * 0.6)
            e = min(start + length, self.n)
            if e > s:
                self.dly[s:e] += ney[s:e] * np.linspace(0, 0.13, e - s)[:, None]
        self.add(ney, 0.49, rev=0.4, dly=0.04, sc=0.12, hp=170, lp=self.air(5200), src="ney")
        self.add(throat, 0.32, rev=0.45, dly=0.15, sc=0.2, hp=60, src="throat")
        self.add(chant, 0.24, rev=0.55, dly=0.25, sc=0.25, hp=140, lp=self.air(6000), src="chant")

    def _phrases(self, events, synth, tail=1.5):
        """Render monophonic events as connected phrases (one breath per run)."""
        rng = self.rng
        buf = self.track()
        events = sorted(events, key=lambda x: (x[0], x[1]))
        run, prev_end = [], None

        def flush(run):
            if not run:
                return
            s0 = self.pos(run[0][0], run[0][1])
            end = self.pos(run[-1][0], run[-1][1]) + int(run[-1][2] * self.bl(run[-1][0]) * SR) + int(tail * SR)
            notes = [(self.pos(br, b) - s0, int(ln * self.bl(br) * SR * 0.97), m, g) for br, b, ln, m, g in run]
            place(buf, synth(notes, end - s0), s0, 1.0, -0.13)

        for ev in events:
            st = self.pos(ev[0], ev[1])
            if prev_end is not None and (st - prev_end > int(0.35 * SR) or st - self.pos(run[0][0], run[0][1]) > int(7 * SR)):
                flush(run)
                run = []
            run.append(ev)
            prev_end = st + int(ev[2] * self.bl(ev[0]) * SR)
        flush(run)
        return buf

    def r_pad(self):
        rng = self.rng
        buf = self.track()
        lv = np.clip(1.1 - 1.15 * self.E, 0.15, 0.9)
        for b in range(self.bars):
            if self.ch(b).get("choir"):
                lv[b] = max(lv[b], 0.45)
        cache = {}
        rev_buf = self.track()
        for bar in range(0, self.bars, 2):
            c = self.chord(bar)
            r = self.tonic(bar)
            dur = 2 * 4 * self.bl(bar)
            key = (r, self.ch(bar)["mode"], c, round(dur, 2))
            if key not in cache:
                sc = self.scale(bar)
                notes = [r + 24 + x for x in th.chord(sc, c, 4)] + [r + 12 + th.deg(sc, c)]
                notes = [n - 12 if n > self.root + 43 else n for n in notes]
                cache[key] = ins.pad_chord(notes, dur, dict(fc=1000, att=1.3, voices=5, lfo=9.0, rel=2.2), rng)
            place(buf, cache[key], self.pos(bar), lv[bar])
            # reverse swell sucking into the next chord in the trippy chapters
            nxt = bar + 2
            if self.ch(bar).get("reverse") and nxt < self.bars and rng.random() < 0.6:
                x = cache[key][: int(1.4 * SR)][::-1] * np.linspace(0, 1, int(1.4 * SR))[:, None] ** 2
                place(rev_buf, x, self.pos(nxt) - len(x), 0.8)
        meltc = self.curve(self.chap_curve("melt"))
        buf = dsp.phaser(dsp.melt(buf + rev_buf, 3.5 * meltc, seed=self.seed + 1), rate=0.07, mix=0.5)
        self.add(buf, 1.08, rev=0.55, sc=0.35, hp=170, lp=4500, chorus=True, src="pad",
                 cut=self.curve(np.clip(0.35 + 0.5 * self.E, 0, 1)))

    # ------------------------------------------------------------------ nature & fx
    def r_nature(self):
        rng = self.rng
        lvl = self.curve(self.chap_curve("nature") * np.clip(1.0 - self.E, 0.15, 1))
        bed = ins.earth_bed(self.n, rng, lvl)
        frogs, drops = self.track(), self.track()
        for bar in range(self.bars):
            nat = self.ch(bar).get("nature", 0)
            if nat > 0.3 and rng.random() < 0.55 * nat:
                t = float(rng.uniform(0, 3))
                pn = rng.uniform(-0.8, 0.8)
                for k in range(int(rng.integers(2, 6))):
                    place(frogs, ins.frog(rng), self.pos(bar, t + k * rng.uniform(0.35, 0.6)), rng.uniform(0.5, 1), pn)
            if 0.25 < self.E[bar] < 0.75 and rng.random() < 0.35:
                hz = dsp.midi_hz(self.tonic(bar) + 36 + th.deg(self.scale(bar), int(rng.choice([0, 2, 4]))))
                place(drops, ins.udu(hz, rng), self.pos(bar, int(rng.integers(0, 8)) * 0.5), rng.uniform(0.6, 1),
                      rng.uniform(-0.7, 0.7))
        self.add(bed, 0.6, rev=0.2, hp=40)
        self.add(frogs, 0.14, rev=0.4, dly=0.1, hp=150, lp=2500, src="frogs")
        self.add(drops, 0.25, rev=0.35, dly=0.3, sc=0.3, hp=100, src="drops")

    def r_fx(self):
        rng = self.rng
        buf = self.track()
        for name, nb in self.RISES.items():  # earthy riser: wind swelling upward, no hiss
            end = self.chap_start[name] + next(c["bars"] for c in self.CHAPTERS if c["name"] == name)
            dur = self.t0[end] - self.t0[end - nb]
            n = int(dur * SR)
            x = np.arange(n) / n
            fc = 150 * 2 ** (x * 3.3)
            L = dsp.filt(dsp.noise(n, rng), "bp", fc, 1.6, 128)
            R = dsp.filt(dsp.noise(n, rng), "bp", fc * 1.06, 1.6, 128)
            tone = dsp.filt(dsp.saw(dsp.midi_hz(self.tonic(end - 1) + 12) * 2 ** (x * 1.0), n), "lp", fc * 1.5, 1.5, 128) * 0.25
            place(buf, np.stack([L + tone, R + tone], axis=1) * (x ** 2)[:, None] * 1.8, self.pos(end - nb))
        for name in self.SWELL_AT:
            s = self.chap_start[name]
            place(buf, ins.impact(rng), self.pos(s), 1.6)
        self.add(buf, 0.3, rev=0.35, dly=0.15, lp=3000, src="fx")

    def describe(self):
        lines = [f"Mycelium — {self.bars} bars, {self.t0[-1] / 60:.1f} min, {self.bpm.min():.0f}-{self.bpm.max():.0f} BPM"]
        for ch in self.CHAPTERS:
            s = self.chap_start[ch["name"]]
            t = self.t0[s]
            lines.append(f"  {int(t // 60)}:{int(t % 60):02d}  {ch['name']:<16} "
                         f"{th.note_name(self.root + ch['tonic'] + 24)[:-1]:<3} {ch['mode']:<18} "
                         f"energy {self.E[s]:.2f}→{self.E[s + ch['bars'] - 1]:.2f}")
        return "\n".join(lines)
