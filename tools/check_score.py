"""Score-level repetition check for Journey-engine pieces, no audio rendering.

    python3 tools/check_score.py [mycelium|journey] [seed]

Reports how many 2-bar melody phrases are unique, how often the melody changes
hands, and how many 2-bar orchestration boundaries change something.
"""
import sys
from collections import Counter

sys.path.insert(0, ".")
from psy.journey import Journey
from psy.mycelium import Mycelium

piece = sys.argv[1] if len(sys.argv) > 1 else "mycelium"
cls = dict(mycelium=Mycelium, journey=Journey)[piece]
song = cls(**({"seed": int(sys.argv[2])} if len(sys.argv) > 2 else {}))

phrases = {}
for bar, beat, ln, d, grace, carrier in song.melody:
    phrases.setdefault(bar // 2, []).append((bar % 2, round(beat, 3), ln, song.note(bar, d)))
counts = Counter(tuple(v) for v in phrases.values())
print(f"melody 2-bar phrases: {sum(counts.values())}, unique: {len(counts)}")

carriers = [u["carrier"] for u in song.units]
print(f"melody hand-offs: {sum(a != b for a, b in zip(carriers, carriers[1:]))} of {len(carriers) - 1} boundaries")
print("carrier per unit:", " ".join(c[:2] for c in carriers))

states = [(u["carrier"], u["counter"], u["bassvar"], u["tomgen"], u["didgevar"]) for u in song.units]
print(f"orchestration boundaries that change something: "
      f"{sum(a != b for a, b in zip(states, states[1:]))} of {len(states) - 1}")
print("counter-lines used:", dict(Counter(u["counter"] for u in song.units)))
