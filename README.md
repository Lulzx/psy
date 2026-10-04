# psy

Psytrance written and synthesized entirely in Python. It uses no samples, DAW or plugins: numpy and scipy compute every kick, flute breath and drum stroke, and code chooses every note.

```
python3 make_song.py                       # Mycelium -> out/mycelium.wav + out/mycelium.mp3
python3 make_song.py --piece journey       # Journey  -> out/journey.wav + .mp3
python3 make_song.py --piece twisted       # Twisted  -> out/twisted.wav + .mp3
python3 make_song.py --piece follower      # Follower -> out/follower.wav + .mp3
python3 make_song.py --seed 9              # same story, every melodic and rhythmic decision rewritten
python3 make_song.py --air 0               # old fully dark top end, for A/B
python3 make_song.py --out out/mycelium_improved.wav  # keep an older render for comparison
python3 render.py --list                   # the 8-subgenre style engine
```

A full piece renders in roughly 15 to 35 seconds on a laptop.

Journey and Mycelium place every instrument on a stage: direction with interaural
time and level cues, distance, early reflections of a modelled space, and a
modulated FDN reverb. Kick and bass stay centred and dry. Notes are never
repeated as identical copies, and the master is loudness-matched (LUFS).
`--air 0` renders the old fully dark top end for comparison. A full Mycelium
render takes about 50 seconds. Compare two renders with
`python3 tools/compare.py out/mycelium_before.wav out/mycelium.wav`.
Run `python3 -m unittest discover -s tools -p 'test_*.py'` for focused audio checks.
Use `python3 tools/compare_audio.py out/mycelium.wav out/mycelium_improved.wav`
to measure existing renders and make equal-RMS listening previews.

## Requirements

- Python 3.10 or newer (developed on 3.14)
- numpy and scipy
- ffmpeg, optional, for the MP3 copy
- matplotlib, optional, for the analysis tools in `tools/`

There is nothing to install beyond that. Run the scripts from the repository root.

## The pieces

| Piece | Length | Tempo | Character |
|---|---|---|---|
| **Follower** (`psy/follower.py`) | 3:53 | 126 → 150 → 128 BPM | Scary night-forest piece. Your flute is answered from the dark, closer and more wrong each time. Heartbeat kick, phasing footsteps, endless Shepard wind. See [docs/follower.md](docs/follower.md). |
| **Mycelium** (`psy/mycelium.py`, default) | 4:00 | 132 → 145 → 134 BPM | Earthy psychedelic ceremony in 8 chapters, after Astrix's jungle-tribal full-on and Infected Mushroom's melodic writing. Hand drums in Middle-Eastern rhythms, oud, throat singing, ney flute, didgeridoo, "melting" pads. |
| **Journey** (`psy/journey.py`) | 4:25 | 138 → 150 → 140 BPM | A through-composed psytrance tone poem in 9 chapters, temple to revelation and back. Ney flute, chant, tanpura, warm lead, rolling bass. |
| **Twisted** (`psy/twisted.py`) | 3:48 | 147 BPM | Mandragora-inspired twisted full-on in a conventional section/drop structure, with a composed hook and a key change. |
| Style engine (`render.py`) | any | 96 to 185 BPM | Pattern-based generator with presets for goa, full-on, progressive, dark psy, forest, hi-tech, zenonesque and psybient. |

Chapter-by-chapter descriptions are in [docs/pieces.md](docs/pieces.md).

## Documentation

| Document | Contents |
|---|---|
| [docs/pieces.md](docs/pieces.md) | Every piece: chapters, timestamps, keys, instruments, what to listen for |
| [docs/architecture.md](docs/architecture.md) | How a render works: timeline, composition, layers, buses, mastering |
| [docs/composition.md](docs/composition.md) | The Journey engine: energy curve, orchestration, motif development, harmony, tempo |
| [docs/instruments.md](docs/instruments.md) | Every synthesized instrument, its parameters and register |
| [docs/dsp.md](docs/dsp.md) | The DSP library: oscillators, filters, effects, mastering |
| [docs/sound-guide.md](docs/sound-guide.md) | The palette rules (what is banned and why) and mix targets |
| [docs/howto.md](docs/howto.md) | Write a new piece, add an instrument, analyze a render, fix common problems |
| [docs/history.md](docs/history.md) | How the project evolved from listener feedback |

## Layout

```
make_song.py          render Mycelium, Journey or Twisted
render.py             render style-engine presets
psy/
  dsp.py              oscillators, filters, delay, reverb, chorus, melt, phaser, limiter
  instruments.py      every synthesized instrument
  theory.py           scales, chords, pattern generators (style engine)
  journey.py          the through-composed engine + the Journey piece
  mycelium.py         Mycelium (subclass of Journey)
  twisted.py          Twisted (standalone sectional engine)
  song.py, styles.py  the style engine and its 8 presets
tools/
  check_score.py      unique phrases and orchestration changes, no rendering
  check_journey.py    levels, flow, novelty and spectrogram for Journey/Mycelium
  check_song.py       the same for Twisted
  analyze.py          per-stem levels for style-engine presets
out/                  renders and analysis images
```
