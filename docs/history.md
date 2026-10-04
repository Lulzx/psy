# History

The project grew through a series of listening sessions. Each stage below lists what the listener asked for and what changed in the code. The listener's words are quoted where they shaped a rule.

## 1. Style engine (8 subgenres)

Request: "make psytrance music programmatically, create several style and subgenre".

- Built `psy/dsp.py` (polyBLEP oscillators, block-wise time-varying biquads, ping-pong delay, convolution reverb, sidechain, limiter) and the first instruments.
- `psy/styles.py` defines goa, full-on, progressive, dark psy, forest, hi-tech, zenonesque and psybient. Each preset sets its tempo, scale, bass grid (16ths or triplets), drum strings, acid, lead, pads and FX.
- Fixed a biquad that was normalized by `a0` everywhere except `a[0]`, which made every filter unstable.
- Gain staging: a first stem analysis showed the acid about 10 dB too loud and the hats and leads buried, so `TRIM` and `LEAD_TRIM` were added.

## 2. Twisted, a single Mandragora-inspired track

Request: "make it in style of mandragora and non repetitive, make one song only, make it as good as possible".

- `psy/twisted.py`: 147 BPM, F# phrygian dominant, composed hooks with development operators, per-section bass/hat/fill re-picking, pre-drop gaps, a tape-stop, a key change in the climax.

Follow-up requests, in order:

- "I want the instruments to sound richer": `rich_bass` (sub, detuned body, growl), `warm_lead` (supersaw plus resonant sub-octave), 5-voice chorused pads.
- "none of that high pitched instruments. Artificial piano like sound": all FM plucks, arps, blips and lasers removed, and melodies capped around C#5.
- "Add some bass also": a louder bass and the sustained `reese` under breaks.
- "so unique... engaging enough such that everybody wants to re-listen": the length trimmed to about 3:45, the track opens on the hook, the bass gets a per-bar "knob ride" and pitch blips, and the acid loops use odd lengths (polymeter).
- "small drum like, high pitch, cham cham like, I don't like it": hats, shaker, ride and crashes removed.
- "I love like a little flute thing... a very like spiritual vibe": the listener was hearing the formant chant. `ney_phrase` and `tanpura` were added, and the spiritual layer now runs through the whole track.
- "at 0:47... the beat then cham sound": the clap and snare backbeat was the cause. All noise drums were replaced with pitched tom fills and rolls.
- "I don't like pew pew pew sound, around 25th sec": squelch riffs, zaps, stutters and alien chirps removed. A rhythmic `didgeridoo` took the riff slot, and the acid resonance was halved.

## 3. Journey, a through-composed tone poem

Request: "every five seconds should be very different... but in a flow... building up, building down... like how Beethoven... a story or a visual thing coming up when I close my eyes. And more of that mysterious flute".

- New engine in `psy/journey.py`: chapters with their own modes and keys, a continuous energy curve, a tempo map (138 → 150 → 140 BPM), 2-bar orchestration units, and one melody developed from a seed motif with transformations and chord-tone snapping.
- A first analysis showed flat loudness, because the master normalized away the story. Macro dynamics (`DYN_DB`, `DYN_FULL`) were added.

## 4. Mycelium, an earthy ceremony

Request: "make a new one to feel like something to hear on shrooms, very earthy vibe, world class level music", then "you can have inspiration from Astrix and Infected Mushroom".

- The plan changed from slow psydub to jungle-tribal full-on at 142 to 145 BPM after the Astrix and Infected Mushroom reference.
- New instruments: `hand_drum` (darbuka strokes in maqsum, baladi, saidi and others), `udu`, `log_drum`, `oud` (Karplus-Strong with tremolo), `throat_phrase` (overtone singing), `frog`, `earth_bed`.
- New effects: `dsp.melt` (wandering pitch) and `dsp.phaser`.
- The Journey engine was generalized with class attributes and hooks (`LAYERS`, `SLOW_CARRIERS`, `ALWAYS_SLOW`, `_counter_opts`, `_counter_events`) so Mycelium could subclass it.
- Fixed a NaN from `frog`: a fractional power of a sine that dipped below zero on the last sample silenced the whole mix.

## 5. Documentation

- This `docs/` folder, `tools/check_score.py`, `twisted` added to `make_song.py`, and the `FALLS` attribute (Journey's downlifter chapters were hardcoded, which broke subclasses without those chapters).

## 6. Space, richness, natural feel

Request: "suggest better ways to make music, which should feel better, spatial, richer sounds, natural feel", then "do all steps".

Measured first: Mycelium was almost mono (L/R correlation 0.93), had 0.06% of its energy above 3 kHz and 65% below 120 Hz.

- Staging: `dsp.stage` and `dsp.early_ir` (interaural time and level differences, head shadow, distance, image-source reflections), with `STAGE` and `ROOM` per piece and slowly drifting ney and didgeridoo.
- `dsp.fdn_reverb` replaced the noise-IR convolution reverbs.
- Per-hit variation (`Journey.vary`, multiple cached takes) and oversampled `drive`.
- Modal `hand_drum`, glottal-ensemble `voice`, `wander`-based drift in `supersaw`, `pad_chord` and `ney_phrase`.
- `AIR`: soft breath and room air, with `--air 0` to compare against the old dark top end.
- `dsp.master_glue`: LUFS-matched master with a low-end dip, slow glue compression and warm oversampled saturation.

Result (Mycelium, same -10.6 LUFS): correlation above 300 Hz 0.73 to 0.45, side/mid in 300 Hz to 3 kHz -8.0 to -4.1 dB, energy below 120 Hz 65% to 54%, macro range 13.9 dB.
