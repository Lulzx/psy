# Instruments

All instruments live in `psy/instruments.py`. Each is a function that returns a numpy array: mono `(n,)` or stereo `(n, 2)`, at 44.1 kHz, peak roughly 1. Levels are set by the layer that places them, not by the instrument.

`rng` is always a `numpy.random.Generator`. `hz` arguments are frequencies and `midi` arguments are MIDI note numbers. `dsp.midi_hz` converts between them.

The "Used by" column uses M = Mycelium, J = Journey, T = Twisted, S = style engine.

## Kick and bass

| Function | Sound | Key parameters | Used by |
|---|---|---|---|
| `kick(root_hz, p, rng)` | Psytrance kick: a sine swept from `f0` down to the key's root, a 1.4 kHz click transient, then tanh drive. The tail is cut at `len`, about one 16th, so the rolling bass fits between kicks. | `len` (s), `f0` start Hz, `pdecay` sweep time, `tail` fraction of `len` used for the fade, `click`, `drive`, `tune` (multiplier on `root_hz`) | All |
| `rich_bass(hz, dur, p)` | Layered rolling bass note. A clean sine sub, two saws detuned ±6 cents through a 24 dB resonant lowpass with its own envelope (highpassed at 85 Hz so the sub owns the fundamental), and a mid "growl" from a bandpassed pulse an octave up. | `base`/`peak` filter Hz, `env_decay`, `res`, `wave` (`saw` or `pulse`), `sub_lvl`, `growl`, `amp_decay`, `sustain`, `drive` | M, J, T |
| `bass_note(hz, dur, p)` | The older single-saw bass note | Same filter and envelope keys, `sub_lvl` | S |
| `sub_note(hz, dur)` | Plain sine sub with a little 2nd harmonic | | (unused) |
| `reese(midi, dur, rng)` | Four saws detuned up to ±12 cents through a slowly moving 320 Hz lowpass, plus a clean sine. Slow attack, 1 s release. Fills the low end when the rolling bass is absent. | | M, J, T |

## Drums and percussion

| Function | Sound | Used by |
|---|---|---|
| `hand_drum(kind, hz, rng, strength)` | Modal darbuka/djembe. Ten circular-membrane modes (`MEMBRANE` ratios 1, 1.594, 2.136, ...), each with its own decay, plus an amplitude-dependent pitch drop at the onset. `STROKES` sets the mode weights: `doum` excites the round centre modes and adds a goblet air resonance. `tek` and `slap` excite the rim (diametric) modes. A contact-time smoothing means soft hits are darker, and a little skin noise is added. `ghost`: a quiet tek. Lowpassed at 2.6 to 5.8 kHz depending on `strength`. | M |
| `tom(hz, decay, rng)` | Pitched tom with a pitch drop and a short skin noise | J, T |
| `log_drum(hz, rng)` | Wooden slit drum: inharmonic partials at 1, 2.76 and 5.4 times the pitch, decaying in 110, 40 and 15 ms. Damped, no bell sustain. | M |
| `udu(hz, rng)` | Clay pot "bloop": a sine whose pitch rises after the hit | M |
| `perc(rng, f, decay, kind)` | Small percussion: `tom`, `click`, `fm` | S |
| `hat`, `ride`, `clap`, `snare` | Metallic and noise percussion | S only (banned in the composed pieces, see [sound-guide.md](sound-guide.md)) |
| `shaker`, `crash` | Seed shaker, crash cymbal | Unused since the palette rules. Kept for experiments. |

## Melodic voices

| Function | Sound | Register in use | Used by |
|---|---|---|---|
| `ney_phrase(notes, n, rng)` | Ney or bansuri flute played as one breath-connected phrase. Notes closer than 60 ms glide into each other (35 ms portamento). Detached notes scoop up from a semitone below. Grace notes flick from a whole tone above. Vibrato fades in after 0.35 s. Breath noise follows the 2nd harmonic and is strongest at note onsets. `notes = [(start_sample, len_samples, midi, grace)]`. | B3 to C#5 | M, J, T |
| `oud(midi, dur, rng, bright)` | Plucked fretted string by Karplus-Strong: a lowpassed noise burst with a pick-position comb, into a tuned delay-line filter, then two wooden body resonances at 260 and 620 Hz. Layers re-pluck long notes as tremolo. | E3 to C5 | M |
| `warm_lead(midi, dur, rng)` | 7-voice supersaw (±0.22 semitone spread, 700 to 3900 Hz filter envelope) plus a resonant sub-octave layer from `reso_lead` | Mid | M, J, T |
| `supersaw(midi, dur, p, rng)` | Detuned saw stack with vibrato, stereo-split voices | Mid | S, via `warm_lead` |
| `reso_lead(midi, dur, p, rng)` | Saw plus pulse through a resonant filter with vibrato, Goa-style | Mid | S, via `warm_lead` |
| `pad_chord(midis, dur, p, rng)` | Chord of detuned saws (`voices` per note), random stereo spread, lowpass with a slow LFO, long attack and release | Low-mid | All |
| `acid_line(steps, n_total, step_len, root_midi, cutoff, p, rng)` | Monophonic 303-style line rendered as one continuous signal: per-step pitch with exponential slides, gated amplitude, an accent-aware filter envelope, a 24 dB resonant lowpass driven by a per-sample cutoff curve, then drive. `steps(i)` returns `{"semi", "accent", "slide"}` or `None`. | Low-mid | J, T, S |
| `fm_pluck`, `alien` | FM bell pluck, formant-swept squelch | Mid to high | S (banned in the composed pieces) |
| `flute`, `squelch` | Sine flute (replaced by `ney_phrase`), resonant "pew" squelch | Mid to high | Unused since the palette rules |

## Voices

| Function | Sound | Used by |
|---|---|---|
| `voice(midi, dur, vowels, rng, singers)` | Formant chant from a small ensemble (3 by default). Each singer is a Rosenberg glottal pulse (`glottal()`) with its own detune, vibrato rate, pitch scoop, jitter (fast pitch wobble), shimmer (level wobble), aspiration noise and a staggered entry. The sum goes through three formants whose bandwidths grow with frequency (70 Hz + 6%) and glide across a vowel list such as `["a", "o", "u"]`. Formant table: `VOWELS`. Also used for choir counter-lines. | M, J, T |
| `throat_phrase(notes, n, f0, rng)` | Overtone (throat) singing. A low drone at `f0` (E2 in Mycelium) with vowel body formants, plus a very narrow bandpass (Q 28) that picks out one harmonic of the drone as a whistle. Each note's target pitch snaps to the nearest harmonic (4th to 14th), and the whistle glides between harmonics. The melody therefore sounds in just intonation, as real throat singing does. | M |

## Drones

| Function | Sound | Used by |
|---|---|---|
| `tanpura(midi, dur, rng)` | Karplus-Strong drone string with a slowly sweeping bandpass "jawari" shimmer over harmonics 6 to 12. Layers pluck it in the classic Pa, Sa', Sa', Sa order, one pluck every two beats. | M, J, T |
| `didgeridoo(midi, dur, accents, rng)` | One bar of rhythmic didgeridoo. A low saw and pulse buzz is shaped by two formants that open from "u" toward "a" on each accent, `accents = [(beat, strength)]`, lowpassed at 1.8 kHz. | M, J, T |

## Nature and atmosphere

| Function | Sound | Used by |
|---|---|---|
| `earth_bed(n, rng, level)` | Full-length stereo bed: wind (bandpassed noise whose centre wanders between 160 and 740 Hz) with an 11-second swell, plus earth rumble (noise below 55 Hz). `level` is a per-sample array. | M |
| `frog(rng)` | One croak: a 28 to 45 Hz pulse train through a 380 to 650 Hz bandpass | M |
| `gurgle(rng)` | Sample-and-hold FM bubbling, 120 to 700 Hz | J, T, S |

## Transitions

| Function | Sound | Used by |
|---|---|---|
| `impact(rng)` | Low boom (sine 100 → 30 Hz) with a lowpassed noise hit | All |
| `riser(dur, rng)` | Bandpassed noise sweeping up 5 octaves from 300 Hz, plus a rising saw | J, T, S |
| `downlifter(dur, rng)` | Lowpassed noise falling from 9 kHz | J, T, S |
| `zap`, `laser`, `bubbles`, `blip`, `stutter` | Laser and glitch FX, collected in the `FX` dict | S only |

Mycelium builds its own riser inside `r_fx`: wind-like bandpassed noise sweeping 150 Hz to 1.5 kHz, with a slowly rising saw at the bass root, lowpassed at 3 kHz.

## Writing a new instrument

The revised `ney_phrase` uses a continuous performer state: variable vibrato,
slow pitch drift, and note pressure affecting amplitude, harmonics, noise and
intonation. `expression` controls pitch expressiveness. `hand_drum` accepts
`strength`, which affects tuning variation, attack tone and deep-stroke decay.
Mycelium caches eight takes per strength/stroke/tuning and adds a small consistent
offbeat delay plus timing deviations; the electronic rhythm stays on its grid.

`oud` now synthesizes two slightly detuned strings with a fractional allpass in
each feedback loop, intensity-dependent excitation, alternating pick position,
and body resonances. `strength` and `stroke` control playing behavior. The strings
are summed together; explicit mechanical coupling is not modeled.

Organic motion: `supersaw` gives every voice its own slow pitch drift and a
wandering vibrato rate, `pad_chord` drifts its voices and moves its filter
with `dsp.wander` (the two sides breathe slightly apart), and `ney_phrase` drifts with
`wander` too. `ney_phrase(..., air_amt)` adds a soft breath band (2.5 to 9 kHz)
that follows blowing pressure and note onsets, with no transients. `rich_bass`
accepts `phase` and `cents`, and `log_drum` randomizes its partials, so
callers can keep several variants of each note instead of one cached copy.

- Return mono unless the sound is inherently stereo. `place()` pans mono signals.
- Normalize to a peak around 1 and let the layer set the level.
- End with `fade_edges()`, or another envelope that reaches zero, to avoid clicks.
- Keep fractional powers away from values that can dip below zero. `np.sin(...) ** 0.7` returns NaN for -1e-16, and one NaN silences the whole master. Clip first.
- Prefer filters with per-sample cutoff arrays (`dsp.filt(x, kind, fc_array, q, block)`) for sweeps, and static Butterworth filters (`dsp.static`) for fixed tone shaping.
- If the layer calls the instrument many times with the same arguments, cache the result in the layer.
