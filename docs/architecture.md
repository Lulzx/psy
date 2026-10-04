# Architecture

A render has four stages: build a timeline, compose the score, render each layer into the mix and its effect sends, then process the sends and master. Nothing is streamed: each layer is a full-length stereo numpy array.

```
Journey(seed, root)
  _timeline()      per-bar table: chapter, energy E, tempo, chord   ->  t0 (bar start times)
  _orchestrate()   per 2-bar unit: melody carrier, counter-line, variation counters
  _compose()       self.melody and self.counter: (bar, beat, length, degree, ...) events
render()
  for each name in LAYERS:  r_kick, r_bass, ... -> self.add(buffer, gain, sends...)
  delay send   -> ping-pong delay  -> partly into reverb send
  reverb send  -> convolution reverb
  mix + returns -> macro dynamics -> fade -> master (HP, loudness, glue, limiter)
```

`make_song.py` writes the result as 16-bit WAV with TPDF dither and, if ffmpeg is present, a 320 kbps MP3.

## Time

`SR` is 44100 Hz everywhere (`psy/dsp.py`).

The Journey engine allows the tempo to change every bar. `self.bpm[bar]` is interpolated linearly inside each chapter, and `self.t0` holds the cumulative start time of every bar in seconds (`240 / bpm` per bar). Every placement goes through two helpers:

- `pos(bar, beats)` returns the sample index of a beat inside a bar. Beats of 4 or more roll over into the following bars, so a phrase can be written relative to its first bar.
- `bl(bar)` returns the beat length in seconds, used for note durations.

Layers that need a fixed step length across many bars, such as the acid line, render in 4-bar chunks and use the average step length of each chunk, so they stay on the grid while the tempo drifts.

`curve(per_bar)` turns a per-bar array into a per-sample automation curve by linear interpolation between bar starts. Filter sweeps, sidechain depth and the macro dynamics all use it.

Twisted and the style engine use a fixed tempo, so `pos()` there is simply `(bar * bar_len + beats * beat_len) * SR`.

## The mix bus

Every layer method builds its own stereo buffer with `track()` (zeros, shape `(n, 2)`), places sounds into it with `song.place()`, and hands it to `add()`:

```python
self.add(buf, gain, rev=0.3, dly=0.2, sc=0.4, cut=curve, hp=150, lp=6000, chorus=True)
```

`add()` applies, in order:

1. `cut`: a per-sample lowpass automation (0 = 120 Hz, 1 = about 19 kHz) through a time-varying biquad
2. `hp` / `lp`: static Butterworth filters
3. `chorus`: the stereo chorus from `dsp.chorus`
4. `sc`: sidechain ducking against the kick, depth 0 to 1
5. `gain`

The result is summed into `self.mix`, and scaled copies go to `self.rev` (reverb send) and `self.dly` (delay send). Building one layer at a time keeps peak memory to a few full-length buffers. A 4-minute piece is about 10.6 million samples per channel, so each stereo float64 buffer is about 170 MB.

`place(buf, sig, pos, gain, pan)` adds a mono or stereo signal at a sample position, clipping at the buffer end. Mono signals are panned with a constant-power law.

## Sidechain

`r_kick` runs first. It records every kick position whose level is above 0.3 and builds `self.sc_env` with `dsp.sidechain_env`: a dip to 0 that recovers over about 0.3 s with a squared curve. Later layers duck by `1 - sc * (1 - sc_env)`. Pads, leads and the ney use depths from 0.2 to 0.5. The bass is not ducked because its notes already sit between the kicks.

## Effect returns

- Delay: `dsp.pingpong` at 0.75 beats (a dotted eighth) of the median tempo, feedback 0.42, with a 2.8 kHz lowpass inside the feedback path so repeats darken. 30% of the delay output also goes into the reverb.
- Reverb: the send is highpassed at 250 Hz, then convolved with a synthetic stereo impulse response from `dsp.make_ir` (3.4 s RT60 for Journey and Mycelium). The IR mixes a bright, fast-decaying noise layer with a dark, slow one, plus 14 early reflections.

Returns are mixed back at 0.5 (delay) and 0.32 (reverb).

## Mastering

1. Macro dynamics: a gain curve from the energy curve, `DYN_DB * (1 - clip(E / DYN_FULL))^1.3`. Journey uses -10 dB below energy 0.65 and Mycelium -12 dB below 0.85. This keeps quiet chapters quiet after loudness normalization.
2. A 5-second squared fade at the end.
3. `dsp.master`: 28 Hz highpass, RMS normalization to `MASTER_RMS` (-11.5 dB) measured on the middle 60% of the track, a half-and-half blend of clean and tanh-saturated signal, then the lookahead limiter (ceiling 0.93, 4 ms lookahead, 80 ms release).

## Caching

Most synth calls are deterministic for a given parameter set, so layers cache rendered notes in dicts keyed by pitch, duration and sound variant. The bass, for example, keys on `(midi, duration, sound, morph)` with the morph value rounded to quarters. This is why a 4-minute render with thousands of notes takes under 30 seconds.

## Determinism

Each piece seeds one `numpy.random.default_rng(seed)` and passes it everywhere. Some decisions use their own short-lived generators seeded from the seed plus a variation counter (bass variants, didgeridoo accents, darbuka rhythm choice). This keeps those choices stable when unrelated code changes how many random numbers are drawn elsewhere. The same seed and code always produce the same audio.

## The three engines

| Engine | File | Structure | Used by |
|---|---|---|---|
| Journey | `psy/journey.py` | Chapters, a continuous energy curve, 2-bar orchestration units, one developed melody, tempo map | Journey, Mycelium (subclass) |
| Twisted | `psy/twisted.py` | Fixed sections with per-bar level tables, composed hooks with development operators, pre-drop gaps, tape-stop | Twisted |
| Style engine | `psy/song.py` + `psy/styles.py` | Arrangement templates, per-bar levels, preset dictionaries | `render.py` presets |

The Journey engine is the current one. [composition.md](composition.md) describes it in detail, and the end of that document covers the other two.
