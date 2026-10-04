# Follower

A scary psytrance piece, 3:53, Eb phrygian rising to E phrygian dominant, 126 → 150 → 128 BPM.

```
python3 make_song.py --piece follower
python3 tools/check_journey.py follower
```

You walk through a pine forest at night playing a flute. Something in the dark plays your phrase back. The fear comes from space and imitation. There are no shrieks, and everything stays in the low and middle register of the [sound guide](sound-guide.md).

| Time | Chapter | What happens |
|---|---|---|
| 0:00 | lantern | Muffled heartbeat instead of a kick, owls. Your call comes back as an exact echo from across the valley. |
| 0:22 | footsteps behind | Footsteps walk slower than the beat and drift until they land on it. Then they are the kick. |
| 0:52 | it answers | The answers come closer, a little flat, and the last note sags. An endless Shepard rise leads into the drop. |
| 1:27 | run | Hungarian minor, full-on. The answer is an octave below you now, with a growl in it. |
| 2:07 | hold your breath | Locrian. Energy drops away, the heartbeat returns, and a wind falls without end. Something large breathes nearby, and the answers are whispered from beside you. |
| 2:34 | it is here | A semitone up. Low moaning voices in a semitone cluster. Each answer ends a tritone away from yours. |
| 3:20 | first light? | The forest comes back, and the steps walk up and stop. The last answer is your exact phrase, sung right behind you. |

## Techniques

- **Call and answer with a hole.** Every eighth-bar arc cuts the melody after beat 1 of bars 4 and 8. The "follower" replays the call from three bars earlier, a little faster. Each chapter sets its `answer` distance (1 = across the valley, 0 = beside you), how wrong it is (flat, bent, tritone), octave and voice. Within a chapter each answer drifts further: flatter, a forgotten note, a different stretch.
- **Heartbeat into kick.** Below energy 0.46, `r_kick` plays a lub-dub through the energy lowpass. The four-on-the-floor kick fades in over it.
- **Phasing footsteps.** The steps are placed backwards from the chapter end with intervals of `1 + 0.16·(1 − x)^1.4` beats, so they drift until they lock onto the grid.
- **Shepard-Risset wind** (`shepard_wind`). Five narrow noise bands an octave apart glide forever under a bell over log-frequency (55 Hz to 1.7 kHz). The `SHEPARD` table lists where it falls or rises.
- **Roughness.** A 40 to 70 Hz amplitude flutter, the acoustic cue that makes screams alarming, is applied to the breath exhales, the moaning voices and the late answers.

New sounds in `psy/follower.py`: `footfall`, `owl`, `breath_cycle`, `whisper_phrase`, `shepard_wind`.
