# Composition: the Journey engine

`psy/journey.py` writes a piece as a story rather than a loop. The design goals came from listener feedback: no tune repeating throughout, change every few seconds without hard breaks, building up and down, and one musical idea carried through the whole piece the way a classical composition develops a theme.

Four mechanisms deliver that:

1. A continuous **energy curve** drives the rhythm section and the dynamics.
2. **Chapters** set key, mode, chords, tempo and allowed voices.
3. An **orchestration state machine** changes one or two things every 2 bars.
4. **One melody**, grown from a seed motif, is developed through every chapter.

## Chapters

A piece is a list of chapter dicts in `CHAPTERS`:

```python
dict(name="storm", bars=20, mode="hungarian_minor", tonic=0,
     e=[(0, 0.88), (0.45, 1.0), (1, 0.62)], bpm=(147, 150),
     chords=[0, 1, 0, 4, 0, 1, 5, 4, 1, 0], follow=False,
     carriers=["lead", "ney", "duet"], acid=True, triplets=True)
```

| Key | Meaning |
|---|---|
| `name` | Chapter id, used by `RISES`, `SWELL_AT` and `describe()` |
| `bars` | Length in bars |
| `mode` | A scale name from `theory.SCALES` |
| `tonic` | Semitones above the piece's root. The kick, bass, drone and every melody note follow it. |
| `e` | Energy points `(position 0..1 within the chapter, energy 0..1)`, interpolated linearly |
| `bpm` | Tempo at the chapter's start and end, interpolated linearly per bar |
| `chords` | Scale degrees, one per 2 bars. The last entry holds if the list is short. |
| `follow` | If true, the bass plays the chord root instead of a tonic pedal |
| `carriers` | Voices allowed to carry the melody in this chapter. Repeats weight the random choice. |
| Flags | Journey reads `acid`, `triplets`, `choir`. Mycelium also reads `melt`, `nature`, `logs`, `reverse`. |

Three class attributes mark turning points:

- `RISES = {chapter: n}` puts a riser and an accelerating drum roll over the last `n` bars of that chapter.
- `SWELL_AT = (chapter, ...)` places a soft low impact at the start of those chapters.
- `FALLS = (chapter, ...)` places a long downlifter at the start of those chapters, where the music settles. Mycelium replaces this layer and does not use it.

### Key changes that flow

The chord lists are written so each chapter ends on a pivot into the next key. Examples from Journey:

- ritual (F# phrygian dominant) ends on degree 1, G major, the bII chord. Revelation starts in G phrygian dominant, so that G becomes the new tonic.
- revelation (G) ends on G, and return starts on F#. G to F# is bII to I, the characteristic cadence of phrygian dominant.
- clearing (E dorian) ends on degree 1, F# minor, which leads home to F#.

Mycelium does the same: dissolution (F hijaz) ends on F, and afterglow (D dorian) opens on degree 2, which is F major.

### Modes

| Mode | Steps | Used for |
|---|---|---|
| phrygian dominant (hijaz) | 0 1 4 5 7 8 10 | Mystical home key of all three pieces |
| aeolian | 0 2 3 5 7 8 10 | Wistful, melancholy (Journey forest, ascent) |
| dorian | 0 2 3 5 7 9 10 | Warm, hopeful, earthy (clearing, deep jungle, afterglow) |
| hungarian minor | 0 2 3 6 7 8 11 | Dark tension (storm) |
| double harmonic | 0 1 4 5 7 8 11 | The most exotic colour (breathing walls) |
| phrygian, locrian, harmonic minor | | Style engine presets |

Degrees are scale-step indices: degree 0 is the tonic, 4 the fifth, 7 the octave. `theory.deg(scale, d)` converts a degree to semitones and handles negative and multi-octave degrees.

## The energy curve

`_timeline()` builds `self.E`, one value per bar:

1. Interpolate each chapter's `e` points.
2. Add a gentle 8-bar breathing wave (amplitude 0.035).
3. Smooth with a 3-tap filter so energy does not jump at chapter seams.

Layers derive their levels from `E` through `lvl(lo, width)`, a ramp from 0 at `E = lo` to 1 at `E = lo + width`. In Journey:

| Element | Driven by E |
|---|---|
| Kick | Enters from E 0.16. Below 0.3 it plays a half-time heartbeat (beats 1 and 3). A lowpass opens with E, so the beat seems to approach from far away. |
| Bass | Enters from E 0.27. Rhythm pool, filter brightness ("morph") and sound (warm, normal, dark) all follow E. |
| Toms | Density `0.05 + 0.33 E` per 16th. Below 0.2, a lub-dub heartbeat. Phrase-end fills above 0.45. |
| Didgeridoo | Loudest at E 0.55, silent below 0.25 and above 0.85 |
| Acid | Chapters with `acid`, from E 0.52. Cutoff 170 to 2400 Hz with E. |
| Pads | `1.15 - 1.2 E`, more pad when the music is quiet |
| Tanpura | `0.45 + 0.55 (1 - E)` |
| Reese | Fills in when the rolling bass is absent |
| Overall gain | The macro dynamics curve (see [architecture.md](architecture.md#mastering)) |

Because everything follows one curve, a build-up is many small changes arriving together, and a calm passage keeps its beat but thins out.

## Orchestration: something changes every 2 bars

`_orchestrate()` walks the piece in 2-bar units (about 3.3 s at 145 BPM). Each unit holds a state:

```python
dict(carrier="ney", counter="none", bassvar=0, tomgen=0, didgevar=0)
```

At each unit boundary the engine picks one or two dimensions to change, or three at a chapter start:

- `carrier`: who plays the melody. It can only change on 4-bar boundaries, so phrases have room to breathe, and it always changes when a chapter starts.
- `counter`: `none`, `choir` (sustained chord tones sung by the formant voice), `ney` (a slow second flute line under a lead or chant), and in Mycelium `oudarp` (finger-picked broken chords).
- `bassvar`, `tomgen`, `didgevar`: counters. Incrementing one re-seeds that layer's pattern choice.

Changing one or two dimensions at a time keeps the music flowing while it evolves. With the default seeds, every unit boundary changes at least one dimension: 77 of 77 in Journey and 69 of 69 in Mycelium.

Carriers in Journey: `ney`, `lead`, `duet` (lead plus ney an octave below), `chant`. Mycelium adds `oud` and `throat`, and its duet is oud plus ney.

## The melody

`_compose()` writes one continuous line, 2 bars at a time, into `self.melody` as `(bar, beat, length, degree, grace, carrier)` events. Counter-lines go to `self.counter`.

### Seed motif

Each piece has one `MOTIF` of `(beat, length, degree)` tuples spanning a bar:

- Journey: degrees 4 5 4 2 1 0, the fifth falling to the tonic through the flat second. This is the first bar of the Twisted hook.
- Mycelium: degrees 0 1 2 4 2 (E F G# B G#), a rising hijaz shape "like something growing".

At the start of most chapters the motif is restated: augmented to 2 bars in slow style, or placed on the current chord in mid style. Since degrees are read in the chapter's mode, the same motif sounds different in aeolian, dorian or hungarian minor. That is theme transformation in the classical sense.

### Three styles

The style of each unit depends on the carrier and the energy:

| Style | When | Character |
|---|---|---|
| slow | Slow carriers (ney, chant, throat) below E 0.62. Throat and chant always (`ALWAYS_SLOW`). | Long held notes (1 to 4 beats), ornamental turns in 8ths or triplets, grace notes on 40% of long notes, a rest now and then. Long notes snap to chord tones. |
| mid | Slow carriers above 0.62. Other carriers below 0.8. | First bar: a transformation of the previous bar's cell. Second bar: a stepwise walk using one of 8 rhythm cells, ending on a chord tone of the next chord. |
| drive | Lead, oud and duet above 0.8 | 16th-note bars from five figures: `turn` (neighbour-note turns), `arp` (chord-tone arpeggio), `pedal` (alternating with the chord root, the classic psy lead figure), `motif` (the seed motif at double speed, twice, sequenced), `run` (scale up then down). 25% of note pairs merge into 8ths for groove. |

### Development operators

The mid style transforms the previous bar's cell with one of:

| Operator | Effect |
|---|---|
| `seq` | Diatonic sequence: every degree shifted by ±1 or ±2 |
| `inv` | Inversion around the first note |
| `retro` | Same rhythm, pitches in reverse order |
| `frag` | The first half, then the first half again shifted |
| `rhythm` | Long notes split in two with a neighbour note |

Strong beats (beat 1 and 3) snap to the nearest chord tone with `_snap()`, so transformations stay in harmony with whatever chord is under them.

The result for the default seeds: 77 of 78 two-bar phrases unique in Journey, 68 of 70 in Mycelium. The repeats are deliberate restatements of the motif.

### Register

`note(bar, degree)` maps a degree to MIDI: piece root + chapter tonic + 36 + scale step, then folds by octaves into the range root+29 to root+44. For Journey (root F#1) that is B3 to C#5, about 247 to 554 Hz. No melody goes into the high register (see [sound-guide.md](sound-guide.md)).

## Rhythm section details

### Bass

Each 2-bar unit picks a bass pattern from a pool chosen by energy and chapter:

| Pattern | Notes per beat (16ths after the kick) | Character |
|---|---|---|
| `gallop` | 3rd and 4th 16th | K-BB, open and groovy |
| `offroll` | 2nd and 4th | Sparse, bouncy |
| `roll` | 2nd, 3rd, 4th | The classic K-B-B-B full-on roll |
| `push` | Roll with a softer first note | Forward lean |
| `oct` | Roll with octave jumps on the last 16th of beats 2 and 4 | Lift |
| `walk` | Roll whose last note per beat follows a melodic motif | Movement |
| `acid` | Every note from a 12-step pitch motif | Busy, twisted |
| `triplet` | 2 notes on the 2nd and 3rd triplet | Dark gallop (storm) |
| `dub` (Mycelium only) | Syncopated 2-bar line of long notes | Psydub feel at low energy |

On top of the pattern: the second bar of a unit can end with a fill (`up`, a 32nd-note run up an octave, or `turn`, a jump to the fifth on beat 4). About half the units also get a one-off pitch blip on one note, and a slow random walk moves the filter brightness, so consecutive bars rarely match exactly.

### Drums

Journey uses pitched tribal toms. A unit's pattern keeps about 65% of the previous hits and draws new ones at the current density, so the pattern evolves rather than switches.

Mycelium uses a darbuka with traditional rhythms on an 8th grid, changing every 4 bars:

| Rhythm | Pattern (D doum, T tek) |
|---|---|
| maqsum | `D T . T D . T .` |
| baladi | `D D . T D . T .` |
| saidi | `D T . D D . T .` |
| malfuf | `D . . T . . T .` |
| ayoub | `D . T D T . D .` |
| wahda | `D . . . T . T .` |

16th ghost notes fill in with probability `0.15 + 0.55 E`, teks turn into slaps as energy rises, and every 4 bars a 6-stroke flourish can close the phrase.

Rolls before turning points (`RISES`) accelerate from 8ths to 16ths to 32nds (or sextuplets) and rise in pitch.

## Mycelium additions

`Mycelium` subclasses `Journey` and overrides class attributes and layer methods:

- `LAYERS` replaces toms and acid with `r_hand_drums`, `r_logs` and `r_nature`.
- `r_bass` adds the dub style below E 0.48 and uses a "tight" Astrix-style sound above it.
- `r_kick` plays a dubby half-time pattern (beats 1 and 3-and) below E 0.42.
- `r_melody` handles oud (with tremolo picking on notes of 1.5 beats or more), throat singing (rendered as continuous phrases whose whistle follows the melody), ney and chant.
- `r_pad` adds reverse swells before chord changes in chapters flagged `reverse`, plus the melt and phaser effects.
- The `melt` chapter value scales a pitch-wobble effect on the ney (up to 1.6 ms of delay modulation) and pads (up to 3.5 ms).
- `r_nature` adds the wind and earth bed (level `nature × (1 - E)`), frog choruses and udu water drops.

## The Twisted engine

`psy/twisted.py` came first. It keeps a conventional psytrance layout with fixed sections:

- `SECTIONS` holds per-element levels. Values are a float, a `(start, end)` ramp, or a list of `(from_bar, value)` segments.
- Two composed hooks (`HOOK_A`, `HOOK_B`) are developed with operators `answer`, `shift`, `invert`, `trill`, `harmony`, `sparse`, `halftime` and `rhythmic`. Each drop states the hook plainly first.
- `PRE_DROP` gives each build a silence gap, a drum roll, a riser and a highpass sweep.
- `post()` applies mix-level moves: the highpass sweeps into drops and a tape-stop at the end of the twist section.
- The climax modulates up a semitone at its 13th bar.

## The style engine

`psy/song.py` renders presets from `psy/styles.py`:

- A style dict sets bpm, scale, kick, bass, drums, acid, lead, pad, arp, chords, FX and mix.
- Drum and bass patterns are strings, one character per grid step: `x` hit, `o` ghost, `.` rest.
- `ARRANGEMENTS` has three templates (`standard`, `progressive`, `psybient`). Each is a list of `(section, bars, {element: level or ramp}, flags)`. Flags are `gap`, `impact`, `riser4`/`riser8`, `roll` and `downlifter`.
- `TRIM` and `LEAD_TRIM` in `song.py` bring each synth's raw output to a common level, so the per-style gains stay relative.
- `--length` scales every section, rounded to multiples of 4 bars.
