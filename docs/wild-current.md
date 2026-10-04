# Wild Current

An original 4:07.5 instrumental: 160 BPM, G minor with G dorian passages.

```sh
python3 make_song.py --piece wild_current
python3 make_song.py --piece wild_current --seed 29 --out out/wild_current_29.wav
```

The new score is in `psy/wild_current.py`. It uses the current Mycelium acoustic scene and synthesized instruments, with an original eight-bar flute call/answer, new hand-drum patterns, short rolling bass, triplet answers, and a didgeridoo that stays present during the drops. Quiet passages leave room for breath and plucked responses. No reference samples or transcribed melody are included.

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

Render checks are in `out/wild_current.validation.json`: stereo 44.1 kHz, 247.5 seconds, finite PCM, peak 0.930, whole-file RMS -13.16 dBFS. Representative dense passages are near -11.2 dBFS RMS; quiet middle passages near -25 dBFS. These are signal checks, not a subjective listening assessment or a claim of matching the reference master.
