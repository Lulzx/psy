"""Arranges a style into a full track and mixes it down."""
import numpy as np
from . import dsp, theory as th, instruments as ins
from .dsp import SR
from .styles import STYLES, ARRANGEMENTS


def place(buf, sig, pos, gain=1.0, pan=0.0):
    n = len(buf)
    if pos >= n or gain == 0:
        return
    if sig.ndim == 1:
        sig = dsp.pan(sig, pan)
    e = min(pos + len(sig), n)
    buf[pos:e] += sig[: e - pos] * gain


# Gain staging: brings each synth's raw output to a sensible level so the
# per-style gains in styles.py stay relative (kick and bass ~0 dB).
TRIM = dict(acid=0.4, pad=4.0, arp=2.0, tex=1.5,
            chh=4.0, ohat=4.0, ride=4.0, clap=3.0, perc=2.5)
LEAD_TRIM = dict(supersaw=4.0, reso=0.65, alien=1.1, fm=2.0)


def mixdown(*sigs):
    out = np.zeros(max(len(s) for s in sigs))
    for s in sigs:
        out[: len(s)] += s
    return out


class Song:
    def __init__(self, style, seed=1, length=1.0, root=None):
        self.key = style
        self.st = STYLES[style]
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.bpm = self.st["bpm"]
        self.beat = 60.0 / self.bpm
        self.bar = 4 * self.beat
        self.scale = th.SCALES[self.st["scale"]]
        self.root = root if root is not None else int(self.rng.choice(self.st["roots"]))
        self._arrange(length)
        self.n = int((self.bars * self.bar + 4.0) * SR)

    # ------------------------------------------------------------ structure
    def _arrange(self, length):
        tmpl = ARRANGEMENTS[self.st["arrangement"]]
        self.sections, bar = [], 0
        for name, bars, elems, flags in tmpl:
            b = max(4, int(round(bars * length / 4)) * 4)
            self.sections.append((name, bar, b, elems, flags))
            bar += b
        self.bars = bar
        self.lv = {}
        for name, start, b, elems, flags in self.sections:
            for k, v in elems.items():
                if k not in self.lv:
                    self.lv[k] = np.ones(self.bars) if k.endswith("_cut") else np.zeros(self.bars)
                self.lv[k][start:start + b] = np.linspace(v[0], v[1], b) if isinstance(v, tuple) else v
        self.gap_bars = {s + b - 1 for _, s, b, _, f in self.sections if "gap" in f}

    def level(self, k, bar):
        a = self.lv.get(k)
        return 0.0 if a is None else float(a[bar])

    def pos(self, bar, beats=0.0):
        return int((bar * self.bar + beats * self.beat) * SR)

    def bar_curve(self, k, default=1.0):
        """Per-sample automation from per-bar values (linear between bar starts)."""
        a = self.lv.get(k)
        if a is None:
            return None
        xs = (np.arange(self.bars + 1) * self.bar * SR)
        ys = np.append(a, a[-1])
        return np.interp(np.arange(self.n), xs, ys)

    def chord_deg(self, bar):
        c = self.st["chords"]
        return c["prog"][(bar // c["bars"]) % len(c["prog"])]

    # ------------------------------------------------------------ mixing
    def add(self, buf, gain=1.0, rev=0.0, dly=0.0, sc=0.0, cut=None, hp=None):
        if cut is not None:
            c = self.bar_curve(cut)
            if c is not None and c.min() < 0.999:
                fc = 120.0 * 2 ** (c * 7.3)
                buf = np.stack([dsp.filt(buf[:, i], "lp", fc, 0.9, 256) for i in range(2)], axis=1)
        if hp:
            buf = dsp.static(buf, "hp", hp)
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

    # ------------------------------------------------------------ elements
    def r_kick(self):
        st = self.st
        k = st["kick"]
        p = dict(k, len=k["len_steps"] * self.beat / 4)
        smp = ins.kick(dsp.midi_hz(self.root), p, self.rng)
        pat = th.parse(st["drums"].get("kick", "x..." * 4))
        buf, hits = self.track(), []
        for bar in range(self.bars):
            lv = self.level("kick", bar)
            if not lv:
                continue
            for s, v in enumerate(pat):
                if v and not (bar in self.gap_bars and s >= 12):
                    p0 = self.pos(bar, s / 4)
                    place(buf, smp, p0, lv * v)
                    hits.append(p0)
        self.sc_env = dsp.sidechain_env(self.n, hits, 1.0, self.beat * 0.75)
        self.add(buf, st["mix"]["kick"])

    def r_bass(self):
        cfg = self.st["bass"]
        sub = cfg["sub"]
        phrases = th.bass_phrases(cfg, self.scale, self.rng)
        order = [0, 1, 0, 2] if len(phrases) >= 3 else [0]
        step = self.beat / sub
        dur = step * cfg["len_frac"]
        cache = {}
        buf = self.track()
        for bar in range(self.bars):
            lv = self.level("bass", bar)
            if not lv:
                continue
            ph = phrases[order[(bar // 4) % len(order)]]
            off = th.deg(self.scale, self.chord_deg(bar)) if cfg.get("motion") == "chord" else 0
            for s, semi, vel in ph[bar % 4]:
                if bar in self.gap_bars and s >= 3 * sub:
                    continue
                m = self.root + semi + off
                if m not in cache:
                    cache[m] = ins.bass_note(dsp.midi_hz(m), dur, cfg)
                place(buf, cache[m], self.pos(bar, s / sub), lv * vel)
        self.add(buf, cfg["gain"], cut="bass_cut", sc=0.15 if sub == 4 and cfg["len_frac"] > 1 else 0)

    def r_drums(self):
        st, mix, rng = self.st, self.st["mix"], self.rng
        kits = {
            "chh": [ins.hat(rng, 0.022) for _ in range(4)],
            "ohat": [ins.hat(rng, 0.09, hp=7000, metal=0.45) for _ in range(3)],
            "ride": [ins.ride(rng) for _ in range(2)],
            "clap": [mixdown(ins.clap(rng, 1300) * 0.6, ins.snare(rng, 1.0) * 0.4) for _ in range(2)],
            "perc": [ins.perc(rng, dsp.midi_hz(self.root + 36), 0.05, "tom"),
                     ins.perc(rng, dsp.midi_hz(self.root + 48), 0.04, "click"),
                     ins.perc(rng, dsp.midi_hz(self.root + 43), 0.06, "fm")],
        }
        pans = dict(chh=0.2, ohat=-0.1, ride=0.3, clap=0.0, perc=-0.35)
        for name, smps in kits.items():
            pat = st["drums"].get(name)
            if not pat:
                continue
            pat = th.parse(pat)
            buf = self.track()
            for bar in range(self.bars):
                lv = self.level(name, bar)
                if not lv:
                    continue
                for s, v in enumerate(pat):
                    if v:
                        smp = smps[(s + bar) % len(smps)]
                        g = lv * v * rng.uniform(0.88, 1.0)
                        pn = pans[name] + (0.25 * (s % 3 - 1) if name == "perc" else 0)
                        place(buf, smp, self.pos(bar, s / 4), g, pn)
            self.add(buf, mix[name] * TRIM[name], rev=0.15 if name in ("clap", "perc") else 0.04,
                     dly=0.15 if name == "perc" else 0, hp=200 if name == "perc" else None)
        self.r_rolls()

    def r_rolls(self):
        buf = self.track()
        for name, start, b, _, flags in self.sections:
            if "roll" not in flags:
                continue
            first = start + b - 2
            for i in range(32):  # 2 bars: 8ths, then 16ths, then 32nds
                if i < 8:
                    t = i * 0.5
                elif i < 16:
                    t = 4 + (i - 8) * 0.25
                else:
                    t = 6 + (i - 16) * 0.125
                x = i / 31
                place(buf, ins.snare(self.rng, 1.0 + 0.6 * x, 0.05), self.pos(first, t), 0.25 + 0.75 * x)
        self.add(buf, 0.22, rev=0.25, hp=150)

    def r_acid(self):
        cfg = self.st["acid"]
        if not cfg or "acid" not in self.lv:
            return
        sub = cfg.get("sub", 4)
        step = self.beat / sub
        base = th.acid_seq(cfg, self.scale, self.rng)
        seqs = [base, th.mutate(base, self.scale, self.rng, 2), base, th.mutate(base, self.scale, self.rng, 4)]
        L = len(base)
        steps_per_block = sub * 4 * 8
        cut = self.bar_curve("acid_cut")
        t = np.arange(self.n) / SR
        lfo = 0.22 * np.sin(2 * np.pi * t / (cfg["lfo_bars"] * self.bar))
        cn = np.clip(cut + lfo, 0, 1)
        fc = cfg["cut_min"] * (cfg["cut_max"] / cfg["cut_min"]) ** cn
        lvl = self.lv["acid"]
        buf = self.track()
        b = 0
        while b < self.bars:  # render each contiguous active region
            if not lvl[b]:
                b += 1
                continue
            e = b
            while e < self.bars and lvl[e]:
                e += 1
            s0 = self.pos(b)
            n = self.pos(e) - s0 + int(0.2 * SR)
            i0 = int(round(b * self.bar / step))

            def steps(i, i0=i0):
                gi = i0 + i
                return seqs[(gi // steps_per_block) % 4][gi % L]

            y = ins.acid_line(steps, n, step * SR, self.root + cfg["octave"], fc[s0:s0 + n], cfg, self.rng)
            g = np.interp(np.arange(n), (np.arange(e - b + 1) * self.bar * SR),
                          np.append(lvl[b:e], 0))
            pn = 0.15 * np.sin(2 * np.pi * np.arange(n) / SR / (self.bar * 2))
            place(buf, np.stack([y * g * (1 - pn), y * g * (1 + pn)], axis=1), s0)
            b = e
        self.add(buf, cfg["gain"] * TRIM["acid"], rev=cfg["rev"], dly=cfg["dly"], sc=self.st["sidechain"] * 0.5, hp=90)

    def r_lead(self):
        cfg = self.st["lead"]
        if not cfg or "lead" not in self.lv:
            return
        buf = self.track()
        rng = self.rng
        if cfg["kind"] == "alien":
            for bar in range(self.bars):
                lv = self.level("lead", bar)
                if not lv:
                    continue
                for _ in range(int(rng.integers(1, 3))):
                    d = float(rng.choice([0.5, 0.75, 1.0, 1.5])) * self.beat
                    place(buf, ins.alien(d, rng, base=dsp.midi_hz(self.root + 24)),
                          self.pos(bar, int(rng.integers(0, 7)) * 0.5), lv, rng.uniform(-0.6, 0.6))
        else:
            phrases = [th.lead_phrase(cfg, self.scale, rng), th.lead_phrase(cfg, self.scale, rng)]
            synth = dict(supersaw=ins.supersaw, reso=ins.reso_lead, fm=ins.fm_pluck)[cfg["kind"]]
            step = self.beat / 4
            cache = {}
            for bar in range(self.bars):
                lv = self.level("lead", bar)
                if not lv:
                    continue
                ph = phrases[(bar // 8) % 2]
                b4 = bar % 4
                oct_ = int(self.level("lead_oct", bar))
                for s, ln, semi, vel in ph:
                    if b4 * 16 <= s < (b4 + 1) * 16:
                        m = self.root + cfg["octave"] + semi + oct_
                        key = (m, ln)
                        if key not in cache:
                            cache[key] = synth(m, ln * step * 0.92, cfg, rng)
                        place(buf, cache[key], self.pos(bar, (s - b4 * 16) / 4), lv * vel)
        self.add(buf, cfg["gain"] * LEAD_TRIM[cfg["kind"]], rev=cfg["rev"], dly=cfg["dly"], sc=self.st["sidechain"],
                 cut="lead_cut", hp=200)

    def r_pad(self):
        cfg = self.st["pad"]
        if not cfg or "pad" not in self.lv:
            return
        cb = self.st["chords"]["bars"]
        buf = self.track()
        cache = {}
        for bar in range(0, self.bars, cb):
            lv = self.level("pad", bar)
            if not lv:
                continue
            d = self.chord_deg(bar)
            if d not in cache:
                notes = [self.root + cfg["octave"] + x for x in th.chord(self.scale, d, 4)]
                cache[d] = ins.pad_chord(notes, cb * self.bar, cfg, self.rng)
            place(buf, cache[d], self.pos(bar), lv)
        self.add(buf, cfg["gain"] * TRIM["pad"], rev=0.5, sc=self.st["sidechain"], cut="pad_cut", hp=180)

    def r_arp(self):
        cfg = self.st["arp"]
        if not cfg or "arp" not in self.lv:
            return
        sub = cfg.get("sub", 4)
        seq = th.arp_seq(cfg, self.scale, self.rng, sub)
        buf = self.track()
        cache = {}
        for bar in range(self.bars):
            lv = self.level("arp", bar)
            if not lv:
                continue
            cd = self.chord_deg(bar)
            for s in range(sub * 4):
                gi = bar * sub * 4 + s
                v = seq[gi % len(seq)]
                if v is None:
                    continue
                m = self.root + cfg["octave"] + th.deg(self.scale, cd + v)
                if m not in cache:
                    cache[m] = ins.fm_pluck(m, 0.05, cfg, self.rng)
                place(buf, cache[m], self.pos(bar, s / sub), lv * (1.0 if s % 2 == 0 else 0.7),
                      0.35 if gi % 2 else -0.35)
        self.add(buf, cfg["gain"] * TRIM["arp"], rev=0.3, dly=cfg["dly"], sc=self.st["sidechain"] * 0.7,
                 cut="arp_cut", hp=250)

    def r_tex(self):
        st, rng = self.st, self.rng
        buf = self.track()
        for bar in range(self.bars):
            lv = self.level("tex", bar)
            if not lv or rng.random() > st["tex_prob"]:
                continue
            name = str(rng.choice(st["fx"]))
            if name == "stutter":
                x = ins.stutter(rng, self.beat / 8)
                place(buf, x, self.pos(bar, 3.0), lv * 0.7, rng.uniform(-0.3, 0.3))
            else:
                x = ins.FX[name](rng)
                x = x / (np.abs(x).max() + 1e-9)
                place(buf, x, self.pos(bar, int(rng.integers(0, 8)) * 0.5), lv, rng.uniform(-0.75, 0.75))
        self.add(buf, st["mix"]["tex"] * TRIM["tex"], rev=0.35, dly=0.45, sc=0.3, hp=150)

    def r_events(self):
        buf = self.track()
        rng = self.rng
        for name, start, b, _, flags in self.sections:
            if "impact" in flags:
                place(buf, ins.impact(rng), self.pos(start), 0.55)
                place(buf, ins.downlifter(2 * self.bar, rng), self.pos(start), 0.2)
            if "downlifter" in flags:
                place(buf, ins.downlifter(4 * self.bar, rng), self.pos(start), 0.3)
            for f in flags:
                if f.startswith("riser"):
                    nb = min(int(f[5:]), b)
                    place(buf, ins.riser(nb * self.bar, rng), self.pos(start + b - nb), 0.28)
        self.add(buf, 1.0, rev=0.4)

    # ------------------------------------------------------------ render
    def render(self, log=print):
        self.mix = self.track()
        self.rev = self.track()
        self.dly = self.track()
        for fn in (self.r_kick, self.r_bass, self.r_drums, self.r_acid, self.r_lead,
                   self.r_pad, self.r_arp, self.r_tex, self.r_events):
            log(f"  · {fn.__name__[2:]}")
            fn()
        log("  · fx returns")
        wet_d = dsp.pingpong(self.dly, self.st["delay_beats"] * self.beat, fb=0.45)
        self.rev += wet_d * 0.3
        ir = dsp.make_ir(self.st["rev_size"], np.random.default_rng(self.seed))
        wet_r = dsp.reverb(dsp.static(self.rev, "hp", 250), ir)
        out = self.mix + wet_d * 0.55 + wet_r * 0.32
        log("  · master")
        return dsp.master(out)

    def describe(self):
        lines = [f"{self.st['name']} — {self.bpm} BPM — {th.note_name(self.root)} {self.st['scale']}"
                 f" — {self.bars} bars ({self.bars * self.bar / 60:.1f} min)"]
        for name, start, b, elems, flags in self.sections:
            t = start * self.bar
            lines.append(f"  {int(t // 60)}:{int(t % 60):02d}  {name:<8} {b:>3} bars  "
                         + " ".join(k for k in elems if not k.endswith(("_cut", "_oct"))))
        return "\n".join(lines)
