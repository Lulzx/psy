# DSP library

`psy/dsp.py` holds every signal-processing primitive. The code is vectorized numpy and scipy. The only Python loops run per filter block or per delay chunk, never per sample.

## Conventions

- `SR = 44100`. All times are in seconds unless a name says `_ms`.
- Mono signals are `(n,)` and stereo signals are `(n, 2)` float64.
- Frequency and cutoff arguments accept either a scalar or a per-sample array of length `n`, for sweeps and glides.

## Oscillators

| Function | Notes |
|---|---|
| `phasor(freq, n, phase0)` | Phase in [0, 1) and per-sample increment, from a cumulative sum of `freq / SR`. All oscillators build on it, so frequency can change every sample without phase jumps. |
| `saw(freq, n, phase0)` | Band-limited sawtooth using polyBLEP correction at each wrap (`_blep`) |
| `pulse(freq, n, width, phase0)` | Difference of two polyBLEP saws offset by the pulse width, mean removed |
| `sine(freq, n, phase0)` | Sine from the phasor |
| `noise(n, rng)` | Uniform white noise in [-1, 1] |
| `midi_hz(m)` | `440 * 2^((m - 69) / 12)`, works on arrays |
| `secs(n)` | Time axis `arange(n) / SR` |

## Envelopes

| Function | Notes |
|---|---|
| `adsr(n, a, d, s, r, gate)` | Linear attack, exponential decay toward sustain, linear release starting at `gate` seconds from the level reached there |
| `fade_edges(x, fin, fout)` | Short linear fades at both ends, in place, to remove clicks |

## Filters

| Function | Notes |
|---|---|
| `filt(x, kind, fc, q, block)` | RBJ biquad, `kind` is `lp`, `hp` or `bp` (bandpass with 0 dB peak). With scalar `fc` and `q` it is one `lfilter` call. With arrays, coefficients are recomputed every `block` samples and the filter state carries across blocks. Use `block=16` or `32` for fast envelopes (bass, acid) and `128` to `512` for slow automation. Cutoffs are clamped to 15 Hz to 0.45 × SR. |
| `lp4(x, fc, res, block)` | 24 dB/octave resonant lowpass: two cascaded biquads, the first at Q 0.54, the second at Q `res`. Used for every synth voice. |
| `static(x, kind, fc, order)` | Butterworth filter in second-order sections, applied along axis 0, so it works on mono or stereo. `bp` needs a `(low, high)` pair, so use `filt` for single-centre bandpasses. |
| `sos(kind, fc, order)` | The SOS coefficients behind `static` |

## Effects

| Function | Notes |
|---|---|
| `drive(x, amt)` | `tanh(x * amt) / tanh(amt)`: saturation that keeps peaks at 1 |
| `crush(x, bits, down)` | Bit depth and sample-rate reduction |
| `pan(x, p)` | Constant-power pan of a mono signal to stereo, `p` in [-1, 1] |
| `pingpong(x, delay_s, fb, damp)` | Stereo ping-pong delay, returns the wet signal only. It is computed in chunks one delay-length long, so each chunk depends only on the previous one. A biquad lowpass at `damp` sits inside the feedback path, so every repeat is darker. |
| `chorus(x, base_ms, depth_ms, rate, mix)` | Modulated fractional delay with opposite LFO phase per side |
| `melt(x, depth_ms, seed, base_ms)` | The "melting" effect: a fractional delay modulated by three slow, incommensurate sines (0.07 to 0.25 Hz), different per channel, so pitch wanders slowly and unpredictably. `depth_ms` can be a per-sample array, which is how Mycelium automates it per chapter. |
| `phaser(x, rate, mix, seed)` | Two swept notches (a bandpass subtracted from the signal), the second at 2.7 times the first, opposite sweep phase per side |
| `make_ir(rt60, rng, predelay, bright, dark)` | Synthetic stereo impulse response: noise lowpassed at `bright` decaying at 0.45 × RT60, plus noise lowpassed at `dark` decaying at the full RT60. 14 random early reflections are added, then everything is highpassed at 180 Hz and normalized. |
| `reverb(x, ir)` | Overlap-add convolution per channel (`scipy.signal.oaconvolve`), trimmed to the input length |
| `sidechain_env(n, hits, depth, release_s, attack_s)` | Gain envelope that dips at each hit position and recovers with a squared curve |

## Mastering

| Function | Notes |
|---|---|
| `limiter(x, ceiling, look_s, release_s)` | Lookahead peak limiter. The gain is computed from a max-filtered peak envelope, min-filtered and averaged over the lookahead window (so the reduction starts before the peak and is guaranteed to cover it), then smoothed with a one-pole release. A final clip at the ceiling catches anything left. |
| `master(x, target_rms_db)` | 28 Hz highpass, RMS normalization to the target (measured on the middle 60% so intros and fades do not skew it), 50/50 blend with a tanh-saturated copy, then `limiter` at a 0.93 ceiling |
| `to_int16(x, rng)` | 16-bit conversion with TPDF dither |

## Performance notes

- A time-varying `filt` over 10 million samples at `block=256` is about 40,000 `lfilter` calls and takes well under a second.
- `pingpong` runs `n / D` iterations, where D is the delay length in samples: under 1,000 for a 4-minute piece with a dotted-8th delay.
- Reverb is the most expensive single step: two FFT convolutions of about 10 million samples with a 165,000-sample IR (3.4 s RT60), a few seconds in total.
- numba would allow per-sample filters, but it does not support numpy 2.5, so everything is block-based.
