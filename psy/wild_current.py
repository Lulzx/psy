"""Wild Current: original 160 BPM organic psytrance, G minor / G dorian.

A new flute call, plucked answers, forward hand percussion and didgeridoo over
sixteenth-note bass. Reference measurements inform tempo, dynamics and weight;
no reference audio or transcribed melody is used in the render.
"""
import numpy as np
from . import dsp, instruments as ins, theory as th
from .journey import Journey
from .mycelium import Mycelium
from .song import place


def chapter(name, bars, energy, carriers, mode="aeolian", chords=(0, 0, 3, 0), **kw):
    return dict(name=name, bars=bars, mode=mode, tonic=0,
                e=energy, bpm=(160, 160), chords=list(chords)*(bars//2),
                follow=False, carriers=carriers, melt=0.06, **kw)


class WildCurrent(Mycelium):
    CHAPTERS = [
        chapter("a spark in the dark", 8, [(0,0.10),(1,0.26)], ["ney"]),
        chapter("feet find the current", 8, [(0,0.26),(1,0.76)], ["ney","oud"]),
        chapter("wild current", 24, [(0,0.80),(0.65,0.91),(1,0.82)], ["ney","duet"]),
        chapter("wood and breath", 16, [(0,0.78),(0.25,0.25),(1,0.38)], ["ney","oud"]),
        chapter("the circle gathers", 16, [(0,0.38),(1,0.93)], ["ney","oud","duet"], mode="dorian"),
        chapter("running with fire", 24, [(0,0.94),(0.6,1.0),(1,0.88)], ["duet","ney"], mode="dorian"),
        chapter("under the surface", 24, [(0,0.86),(0.35,0.29),(0.75,0.36),(1,0.85)], ["ney","oud"]),
        chapter("one more sunrise", 24, [(0,0.94),(0.6,1.0),(1,0.78)], ["ney","duet"], mode="dorian"),
        chapter("embers on the water", 16, [(0,0.76),(0.4,0.45),(1,0.0)], ["ney","oud"]),
    ]
    RISES = {"feet find the current": 4, "the circle gathers": 4, "under the surface": 4}
    SWELL_AT = ("wild current", "running with fire", "one more sunrise")
    FALLS = ()
    LAYERS = ("r_kick", "r_bass", "r_hand_drums", "r_didge", "r_melody", "r_fx")
    MASTER_RMS = -10.8
    MASTER_LUFS = -10.3
    DYN_DB, DYN_FULL = -12.0, 0.82
    # Beat positions leave the downbeat for the drums and have an offbeat pickup.
    MOTIF = [(0.5,0.5,0),(1.25,0.5,2),(2.0,0.75,4),(3.0,0.5,3),(3.5,0.5,2)]

    def __init__(self, seed=23, root=31):
        super().__init__(seed=seed, root=root)

    def describe(self):
        return "Wild Current — original organic psytrance\n" + Journey.describe(self)

    def _compose(self):
        """An eight-bar call/answer: return the hook, vary the ending, then breathe."""
        self.melody, self.counter = [], []
        answers = [
            [(0.0,1.0,4),(1.5,0.5,2),(2.25,0.75,1),(3.25,0.5,0)],
            [(0.5,0.75,2),(1.5,0.5,3),(2.25,0.5,2),(3.0,0.75,0)],
            [(0.0,0.75,4),(1.0,0.5,5),(1.75,0.75,4),(3.0,0.75,2)],
        ]
        for bar in range(self.bars):
            local = self.rows[bar]["i"]
            phase, arc = local % 8, local // 8
            carrier = self.unit(bar)["carrier"]
            if phase in (0,4):
                cell = self.MOTIF
                carrier = "ney" if phase == 0 else carrier
            elif phase in (1,5):
                cell = answers[(arc + (phase==5)) % len(answers)]
            elif phase in (2,6):
                # The flute and pluck trade short rhythmic answers.
                cell = [(0.75,0.5,2),(1.5,0.5,0),(2.5,0.75,4)]
                if phase == 6:
                    cell = [(t,ln,d-1) for t,ln,d in cell]
            else:
                cell = [(0.0,1.5,0)]  # audible breath before the next call
            if self.E[bar] < 0.3:
                cell = [(t,ln,d) for t,ln,d in cell if ln >= 0.75 or t==0.5]
                carrier = "ney"
            self.melody.extend((bar,t,ln,d,False,carrier) for t,ln,d in cell)
            if phase in (3,7):
                self.counter.extend((bar,t,0.4,d,"oud")
                                    for t,d in [(1.75,0),(2.5,4),(3.25,2)])

    def r_bass(self):
        """Centered short K-B-B-B roll with deliberate gallop/triplet answers."""
        buf, cache = self.track(), {}
        levels = self.lvl(0.30,0.24)
        sound = dict(wave="saw",base=120,peak=2000,env_decay=0.028,res=1.25,
                     sub_lvl=0.78,drive=1.75,amp_decay=0.06,sustain=0.48,growl=0.16)
        for bar in range(self.bars):
            if levels[bar] <= 0:
                continue
            local = self.rows[bar]["i"]
            for beat in range(4):
                triplet = self.ch(bar)["name"]=="running with fire" and local%8 in (6,7)
                steps = (1/3,2/3) if triplet else (0.25,0.5,0.75)
                if local%8==7 and beat==3:
                    steps = (0.25,0.75)
                for j, offset in enumerate(steps):
                    semi = 7 if local%8==7 and beat==3 and j==len(steps)-1 else 0
                    m = self.root + semi
                    duration = self.bl(bar)*(0.24 if triplet else 0.20)
                    variant = (local//4)%3
                    key = (m,triplet,variant)
                    if key not in cache:
                        p = dict(sound,peak=sound["peak"]*(0.8+0.18*variant))
                        cache[key] = ins.rich_bass(dsp.midi_hz(m),duration,p)
                    velocity = (0.78,1.0,0.88)[j]
                    place(buf,cache[key],self.pos(bar,beat+offset),levels[bar]*velocity)
        self.add(buf,0.69,lp=3500)

    def r_hand_drums(self):
        """Dry 3-3-2 accent groups with independent low and rim voices."""
        buf, cache = self.track(), {}
        for bar in range(self.bars):
            e = self.E[bar]
            local = self.rows[bar]["i"]
            patterns = [
                [(0,"doum",0.9),(0.75,"tek",0.7),(1.5,"slap",0.7),(2,"doum",0.8),(2.75,"tek",0.65),(3.5,"tek",0.8)],
                [(0,"doum",0.9),(0.5,"ghost",0.4),(1.25,"tek",0.7),(2,"doum",0.8),(2.75,"slap",0.7),(3.25,"tek",0.65)],
            ]
            pattern = patterns[(local//2)%2]
            if local%8==7 and e>0.5:
                pattern = pattern[:4]+[(3+j/4,"tek" if j%2 else "doum",0.55+0.07*j) for j in range(4)]
            for beat,kind,strength in pattern:
                if e<0.2 and kind not in ("doum","tek"):
                    continue
                variant = int(self.rng.integers(4))
                key = (kind,round(strength,2),variant)
                if key not in cache:
                    cache[key] = ins.hand_drum(kind,110,self.rng,strength=strength)
                gain = (0.3+0.7*e)*strength
                place(buf,cache[key],self.human_pos(bar,beat),gain,
                      -0.28 if kind=="doum" else 0.32)
        self.add(buf,0.37,rev=0.12,dly=0.035,hp=75,lp=5200)

    def r_didge(self):
        """Vowel-shaped drone answers the flute, including during the drops."""
        buf, cache = self.track(), {}
        for bar in range(self.bars):
            local = self.rows[bar]["i"]
            variant = local%4
            accents = [((0.75,0.7),(1.5,1.0),(2.75,0.7),(3.5,0.9)),
                       ((0.5,0.8),(1.75,0.7),(2.5,0.9),(3.25,0.6)),
                       ((1.0,0.6),(2.25,1.0),(3.5,0.7)),
                       ((0.5,0.7),(1.25,0.8),(2.5,0.9),(3.25,1.0))][variant]
            if variant not in cache:
                cache[variant] = ins.didgeridoo(self.root+12,4*self.bl(bar),accents,self.rng)
            gain = 0.55+0.45*self.E[bar]
            if local%8 in (0,4):
                gain *= 0.65  # the flute call gets the foreground
            place(buf,cache[variant],self.pos(bar),gain,-0.04)
        self.add(buf,0.22,rev=0.20,dly=0.06,sc=0.35,hp=100,lp=2400)
