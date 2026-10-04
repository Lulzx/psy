# Sound guide

These rules apply to Mycelium, Journey and Twisted. They came from a listener's direct feedback on earlier renders (see [history.md](history.md)), and any new piece should follow them unless the listener asks otherwise. The style engine presets predate the rules and do not follow them.

## Banned sounds

| Sound | Why it is banned | What replaced it |
|---|---|---|
| Closed and open hi-hats, ride, shaker, crash and reverse crash | Heard as a high "cham cham" | Nothing. The groove comes from the rolling bass, toms and hand drums. |
| Clap and snare backbeat, snare fills and rolls | "The beat then cham sound" | Pitched tom fills and accelerating tom or doum rolls |
| FM plucks, bells, blips, high arpeggios | "Artificial piano-like, alienish" | Warm supersaw lead, oud, ney |
| Laser zaps, resonant squelch riffs, stutter bursts, alien chirps | "Pew pew pew" | Rhythmic didgeridoo, log drums |
| Chirpy, high-resonance acid accents | Read as "pew" | Acid at resonance 3.6 with a 2-octave envelope, mixed low, or left out (Mycelium) |
| High flute (around F#6) | Too high | `ney_phrase` in the B3 to C#5 range |

## Register limits

- Melody notes fold into the piece root +29 to +44 semitones, about 250 to 550 Hz for F#1 and 220 to 520 Hz for E1. `Journey.note()` enforces this.
- Counter-lines and choir stay at or below root +40.
- Log drums stay at or below root +31.
- Bus lowpasses: lead 6 to 6.5 kHz, oud 5 kHz, pads 4.5 kHz, hand drums 6 kHz, FX 3 kHz.

## Spectral targets

Historical baseline measured with `tools/check_journey.py` on the original renders
(not acceptance thresholds for the revised Mycelium):

| Band | Mycelium | Journey |
|---|---|---|
| 20 to 120 Hz | 60 to 68% | about 60% |
| 120 to 1000 Hz | about 30% | about 37% |
| 1 to 3 kHz | about 2.5% | about 2% |
| 3 to 8 kHz | under 0.2% | under 0.2% |
| above 8 kHz | about 0 | about 0 |

Current renders (`python3 tools/compare.py before.wav after.wav`): Mycelium 0.11%
at 3 to 8 kHz and 0.01% above 8 kHz; Journey 0.21% and 0.02%. That soft top end
comes from ney breath, hand-drum skin and the reverb return, all scaled by the
`AIR` class attribute (`make_song.py --air 0` restores the old fully dark top).

Judge brightness per instrument. Breath, wood and string attack may need upper
midrange detail; avoid imposing a global energy cap that removes articulation.
Keep the banned harsh percussion and high melodic registers out of the palette.

## Space

Every melodic and percussive bus has a place on a stage (`STAGE` in `Journey`
and `Mycelium`). Each entry sets azimuth, distance, width and an optional slow
drift (the ney and didgeridoo move). Kick, bass and reese stay centred and dry.
Rules that came out of the measurements:

- Close and up front: ney (dist 0.1), hand drums (0.15), oud (0.25).
- Mid-stage: lead (0.35), tanpura (0.4), logs (0.45).
- Far: chant (0.55), didgeridoo (0.6), pads (0.65), throat singing (0.7), frogs (0.85).
- Mycelium's space is a rock hollow open to the sky, `(20, 16, 9)` m. Journey's is a stone temple, `(24, 20, 12)` m.
- Width targets: L/R correlation above 300 Hz of about 0.45 to 0.65 (it was 0.73 to 0.86 before staging).

## Mix levels

RMS of each layer while it plays, from the analysis tools:

| Layer | Target |
|---|---|
| Kick | about -6 dB |
| Bass | -8 to -9 dB, 2.5 to 3 dB under the kick |
| Melody carrier (ney, lead, oud) | -18 to -23 dB |
| Hand drums or toms | -20 to -23 dB |
| Tanpura, reese, pads, chant, throat | -20 to -25 dB |
| Didgeridoo, log drums | -23 to -27 dB |
| Nature bed and FX | -23 to -35 dB |

The ney is the listener's favourite element ("a very spiritual vibe... that mysterious vibe"). Keep it present in every chapter, up front in calm passages and as a counter-line or duet behind the beat.

## Structure rules

- Develop recognizable themes. Mycelium returns to its motif in eight-bar
  question/answer arcs, varies the answers, and leaves breathing space at the
  end of the arc. `python3 tools/check_score.py` reports recurrence, not a pass/fail
  novelty score.
- Something changes every 2 bars (3.2 to 3.6 seconds at 132 to 150 BPM), but not everything at once.
- No sudden breaks. Energy moves along a continuous curve, and kick and bass fade in and out through level ramps and lowpass automation instead of hard cuts.
- Real dynamics. Quiet chapters should sit 10 to 17 dB below the peak (Mycelium: -27 dB opening, -10 dB peak).
- Key changes go through pivot chords (see [composition.md](composition.md#key-changes-that-flow)).
