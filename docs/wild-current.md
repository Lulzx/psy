# Wild Current

An original 4:07.5 instrumental: 160 BPM, G minor with G dorian passages.

```sh
python3 make_song.py --piece wild_current
python3 make_song.py --piece wild_current --out out/wild_current_guitar.wav
python3 make_song.py --piece wild_current --seed 29 --out out/wild_current_29.wav
```

The new score is in `psy/wild_current.py`. It uses the current Mycelium acoustic scene and synthesized instruments, with an original eight-bar flute call/answer, new hand-drum patterns, short rolling bass, triplet answers, and a didgeridoo that stays present during the drops. Guitar now replaces the oud responses and adds palm-muted offbeat strums during drops, with open chord voicings in quieter passages. `psy/guitar.py` synthesizes picked steel strings with fractional tuning, pick-position coloration, muting and staggered strum attacks. No reference samples or transcribed melody are included.

| Time | Chapter |
|---|---|
| 0:00 | A spark in the dark |
| 0:12 | Feet find the current |
| 0:24 | Wild current |
| 1:00 | Wood and breath |
| 1:24 | The circle gathers |
| 1:48 | Running with fire |
| 2:24 | Under the surface |
| 3:00 | One more sunrise |
| 3:36 | Embers on the water |

The user-supplied reference is "You See Me [Making Of]": https://youtu.be/7mpiU85qMZg.
The linked upload was downloaded and measured before rendering. Its estimated 160.55 BPM pulse, marked changes in energy and centered low end informed this composition. The new arrangement, tonality, melodic theme and rhythms are original. Instrument choices use the project's existing palette; automated reference analysis does not establish exact source instrumentation.

Reference audio, report, chart, beat candidates and loudness receipts are under `out/reference/`. Reproduce the analysis with `python3 tools/analyze_reference.py out/reference/7mpiU85qMZg.wav` (requires librosa, soundfile and matplotlib in addition to numpy/scipy).

The original render checks are in `out/wild_current.validation.json`. The guitar version is saved separately as `out/wild_current_guitar.wav` and `.mp3`, with its checks in `out/wild_current_guitar.validation.json`. Validation checks the float signal before and after mastering for finite values, output duration, level and peak headroom, and the synthesized G3 string's pitch. These are signal checks, not a subjective listening assessment or a claim of matching the reference master.
