# How-to

## Render

```
python3 make_song.py                          # Mycelium, seed 5
python3 make_song.py --piece journey --seed 3
python3 make_song.py --piece twisted
python3 make_song.py --root 30                # Mycelium in F# instead of E
python3 make_song.py --out /tmp/test.wav      # custom path, the MP3 goes next to it
python3 render.py fullon darkpsy --seed 2 --length 0.5 --no-mp3
```

`--seed` changes every melodic, rhythmic and orchestration decision but keeps chapters, keys, tempo and energy. To audition variations, render several seeds and compare.

## Check a render

Score checks run in about a second and render no audio:

```
python3 tools/check_score.py mycelium         # unique phrases, hand-offs, orchestration changes
```

Audio checks render the piece (about 30 s) and write `out/<piece>_check.png`, a spectrogram with chapter markers above a loudness and energy plot:

```
python3 tools/check_journey.py mycelium [seed]
python3 tools/check_song.py [seed]            # Twisted
python3 tools/analyze.py fullon 0.5           # style-engine preset, length multiplier
```

`check_journey.py` prints:

- RMS per layer while it plays. Compare with the targets in [sound-guide.md](sound-guide.md#mix-levels).
- NaN check and peak. The peak should be 0.93, the limiter ceiling.
- Energy share per frequency band. Above 3 kHz should stay under about 1%.
- Loudness jumps over 4 dB between consecutive seconds. Only the final fade should appear, plus sparse grooves at low energy.
- 5-second window similarity. Treat this one with care: it reacts to loudness as much as to musical content.

## Write a new piece

Subclass `Journey` and replace its class attributes. This is a complete, working example:

```python
# psy/dawn.py
from .journey import Journey

class Dawn(Journey):
    CHAPTERS = [
        dict(name="night", bars=12, mode="aeolian", tonic=0, e=[(0, 0.0), (1, 0.3)], bpm=(136, 138),
             chords=[0, 5, 0, 6, 0, 0], follow=False, carriers=["ney", "chant"]),
        dict(name="first light", bars=16, mode="dorian", tonic=0, e=[(0, 0.3), (1, 0.8)], bpm=(138, 143),
             chords=[0, 3, 6, 0, 3, 4, 6, 0], follow=True, carriers=["ney", "lead", "duet"], acid=True),
        dict(name="sunrise", bars=20, mode="phrygian_dominant", tonic=1, e=[(0, 0.9), (1, 0.0)],
             bpm=(143, 136), chords=[0, 1, 6, 0, 5, 1, 0, 6, 1, 0], follow=True,
             carriers=["duet", "lead", "ney"], choir=True),
    ]
    RISES = {"first light": 4}
    SWELL_AT = ("sunrise",)
    FALLS = ("sunrise",)
    MOTIF = [(0, 1, 0), (1, 1, 2), (2, 0.5, 4), (2.5, 0.5, 5), (3, 1, 4)]

    def __init__(self, seed=1, root=29):
        super().__init__(seed=seed, root=root)
```

Then render it:

```python
from psy.dawn import Dawn
from psy.dsp import SR, to_int16
from scipy.io import wavfile
song = Dawn()
print(song.describe())
wavfile.write("out/dawn.wav", SR, to_int16(song.render()))
```

Or register it in `make_song.py` by adding it to the `choices` list and the `dict(...)` that picks the class.

Guidelines for chapters:

- Keep `bars` even, since chords and orchestration run in 2-bar units.
- Make each chapter's last chord a pivot into the next chapter's key ([composition.md](composition.md#key-changes-that-flow)).
- Let neighbouring chapters' energy points meet (end of one about equal to the start of the next) unless you want an audible shift.
- `RISES`, `SWELL_AT` and `FALLS` must name chapters of the piece. A subclass inherits Journey's values otherwise, and those name Journey's chapters.
- Repeat a name in `carriers` to weight it. `["ney", "ney", "lead"]` gives the ney two thirds of the choices.

## Change the sound of a piece

| Goal | Where |
|---|---|
| Layer volume | The `gain` argument of that layer's `self.add(...)` call |
| Layer reverb, delay, ducking, filtering | The `rev`, `dly`, `sc`, `hp`, `lp`, `chorus` arguments of the same call |
| Which layers play | `LAYERS` on the class. Remove a name to drop a layer. |
| When a layer enters | Its `self.lvl(lo, width)` call: the energy where it starts and how fast it reaches full level |
| How quiet the quiet parts are | `DYN_DB` (gain at zero energy) and `DYN_FULL` (energy where full level is reached) |
| Overall loudness | `MASTER_RMS` (default -11.5 dB) |
| Bass tone | The `warm`, `normal`/`tight` and `dark` dicts in `r_bass` |
| Melody register | `note()` arguments `base`, `lo`, `hi` |

## Add an instrument

1. Write the synth function in `psy/instruments.py` and follow the checklist at the end of [instruments.md](instruments.md#writing-a-new-instrument).
2. Smoke-test it alone:

   ```
   python3 -c "import sys; sys.path.insert(0, '.'); import numpy as np; from psy import instruments as i; \
   x = i.udu(160, np.random.default_rng(0)); print(np.isnan(x).any(), abs(x).max())"
   ```

3. Add a layer method `r_<name>(self)` that builds `buf = self.track()`, places notes with `place(buf, sig, self.pos(bar, beat), gain, pan)`, and ends with `self.add(buf, ...)`.
4. Add the method name to `LAYERS`.
5. Run `tools/check_journey.py` and adjust the gain until the layer's RMS sits where you want it.

## Fix common problems

| Symptom | Cause and fix |
|---|---|
| The whole render is silent or the analysis prints `nan` | One NaN anywhere poisons the master. Run each layer alone on a fresh instance to find it: set `s.mix, s.rev, s.dly = s.track(), s.track(), s.track()`, then call `s.r_kick()`, then the suspect layer, and check `np.isnan(s.mix).any()`. A known cause is a fractional power of a value that can go slightly negative, such as `np.sin(...) ** 0.7` at the end of an envelope. Clip first. |
| A filter blows up | Biquad coefficients must be normalized by `a0`, including `a[0]` itself. `dsp._biquad` does this. Keep it if you add a filter type. |
| Notes drift off the beat in a long layer | That layer used one step length across a tempo change. Render in 4-bar chunks as `r_acid` does, or place every note with `self.pos()`. |
| A layer clicks | Notes need an envelope that reaches zero (`fade_edges`). Time-varying filters need `block` small enough for the sweep speed. |
| Everything sounds equally loud | The master normalizes loudness. Contrast has to come from `DYN_DB` and `DYN_FULL`, not from layer gains. |
| A render takes much longer than 30 s | A layer is probably rendering identical notes repeatedly. Add a cache keyed by the note's parameters. |
| `SyntaxError: keyword argument repeated` in a style dict | Two meanings share one key. The bass dicts use `sub` for the grid and `sub_lvl` for the sine level for this reason. |
