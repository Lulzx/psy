# The pieces

Timestamps below are for the default seed. Changing `--seed` rewrites every melody, bass line, drum pattern and orchestration choice, but keeps the chapters, keys, tempo map and energy curve, so the story stays the same.

## Mycelium

`python3 make_song.py` (seed 5, home key E, MIDI root 28)

An earthy psychedelic ceremony, written as something to hear on mushrooms. The rhythm section draws on Astrix's jungle-tribal full-on ("Deep Jungle Walk"): a tight rolling bass at 142 to 145 BPM under tribal drums and ethnic flute. The melodic writing and the oud "guitar" take after Infected Mushroom's dramatic, classically shaped leads.

| Time | Chapter | Key and mode | Energy | What happens |
|---|---|---|---|---|
| 0:00 | spores | E phrygian dominant (hijaz) | 0.01 → 0.22 | Throat singing carries the theme over wind, frogs and earth rumble. Heartbeat doums on the hand drum. |
| 0:18 | mycelium | E hijaz | 0.23 → 0.47 | Darbuka rhythms begin, a dubby half-time kick and a syncopated dub bass, wooden log drums. Ney and oud trade the motif. |
| 0:46 | breathing walls | E double harmonic | 0.48 → 0.60 | The "melt": pads and flute wobble in pitch, a phaser swirls, reverse swells suck into each chord change. Oud and chant lead. |
| 1:13 | deep jungle | E dorian | 0.63 → 0.82 | Four on the floor. The bass becomes an Astrix-style tight roll. Didgeridoo, oud tremolo, duets. An 8-bar drum roll and wind riser lead into the peak. |
| 1:54 | dissolution | F hijaz (up a semitone) | 0.85 → 0.82 | The peak. A dramatic lead, oud and ney duets, choir, the bass following the chords. |
| 2:33 | afterglow | D dorian | 0.69 → 0.55 | A breathing valley, about 4 dB quieter: ney, chant and finger-picked oud. |
| 3:00 | grounding | E hijaz | 0.58 → 0.56 (peak 0.85 mid-chapter) | The groove returns, heavy and rooted. |
| 3:34 | return to soil | E hijaz | 0.48 → 0.04 | Elements leave one by one. Throat singing, frogs and wind close the piece. |

Instruments: kick, layered rolling/dub bass, reese, tanpura, darbuka (doum, tek, slap, ghost), udu, log drums, didgeridoo, oud, ney, throat singing, chant and choir, warm lead, pads, wind and earth bed, frogs.

Loudness per 5 seconds runs from -27 dB in the opening to -10 dB at the dissolution, dips to -14 dB in the afterglow and fades to -29 dB.

## Journey

`python3 make_song.py --piece journey` (seed 7, home key F#, MIDI root 30)

A through-composed tone poem. One seed motif, taken from the Twisted hook, is developed across nine chapters.

| Time | Chapter | Key and mode | Energy | What happens |
|---|---|---|---|---|
| 0:00 | temple | F# phrygian dominant | 0.04 → 0.26 | Lone ney flute, chant, tanpura, a heartbeat kick far away. |
| 0:20 | path | F# phrygian dominant | 0.25 → 0.52 | The beat approaches through a closing lowpass, didgeridoo enters, the bass starts with a gallop. |
| 0:48 | forest | F# aeolian | 0.50 → 0.70 | Soft acid line, the melody passes between ney and lead. |
| 1:21 | ascent | B aeolian | 0.72 → 0.87 | Climbing. The bass follows the chord roots. |
| 1:47 | storm | F# hungarian minor | 0.89 → 0.65 | Dark harmony, triplet bass, the peak at about 45%, then it eases off. |
| 2:19 | clearing | E dorian | 0.60 → 0.48 | Gentle groove, ney and chant duet. |
| 2:45 | ritual | F# phrygian dominant | 0.47 → 0.97 | Layers pile up two bars at a time toward the biggest build. |
| 3:18 | revelation | G phrygian dominant | 1.00 → 0.80 | The theme turns majestic: lead, ney and choir. |
| 3:50 | return | F# phrygian dominant | 0.74 → 0.04 | Everything dissolves back to the opening flute. |

Instruments: kick, rolling bass, reese, tanpura, tribal toms, didgeridoo, soft acid, warm lead, ney, chant and choir, pads.

## Twisted

`python3 make_song.py --piece twisted` (seed 11, F# phrygian dominant, 147 BPM)

A Mandragora-inspired full-on track with a classic section structure. It came before Journey and keeps a composed hook (HOOK_A) and counter-theme (HOOK_B).

| Time | Section | What happens |
|---|---|---|
| 0:00 | open | The hook, chant, ney, tanpura and reese, no drums |
| 0:06 | intro | Kick and rolling bass, filter opening, toms |
| 0:19 | groove | Didgeridoo grooves, acid enters, a chant shout fills the silent beat before the drop |
| 0:32 | drop 1 | Hook stated, then answered, ornamented, sequenced, displaced, inverted |
| 1:11 | twist | Triplet and acid bass lines, ends in a tape-stop |
| 1:31 | tribal | Toms, chant, half-time hook, kick and bass rebuild |
| 1:51 | drop 2 | Counter-theme and hook in harmony |
| 2:30 | breakdown | Pads, chant, half-time counter-theme, acid build |
| 2:49 | climax | Harmonised hook, key change up a semitone halfway |
| 3:28 | outro | Bass filter closes, chant returns |

## Style engine presets

`python3 render.py [style ...] [--seed N] [--length 0.5]`

These are short, pattern-based tracks, one per subgenre. They predate the palette rules in [sound-guide.md](sound-guide.md) and still use hi-hats, claps, FM plucks and laser FX.

| Key | Name | BPM | Scale | Notes |
|---|---|---|---|---|
| goa | Goa Trance | 143 | phrygian dominant | Melodic riff bass, resonant squelchy lead, acid, pads, ride |
| fullon | Full-On | 146 | phrygian | KBBB rolling bass, gated supersaw lead, twisted acid |
| progressive | Progressive Psy | 136 | aeolian | K-BB gallop bass, deep pads, FM plucks |
| darkpsy | Dark Psy | 150 | locrian | Distorted resonant bass, alien squelches, no pads |
| forest | Forest Psy | 152 | hungarian minor | Triplet bass, gurgles and bubbles |
| hitech | Hi-Tech | 185 | phrygian | Triplet bass, stutter bursts, gated FM lead |
| zenonesque | Zenonesque | 132 | dorian | Minimal, perc-heavy, quirky FM blips |
| psybient | Psybient / Psychill | 96 | phrygian dominant | Half-time drums, long bass notes, pads |

The `out/*_s1.*` files were rendered before the gain-staging fixes. Re-render them with `python3 render.py` for balanced mixes.
