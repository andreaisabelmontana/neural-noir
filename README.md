# Neural Noir

A procedural detective game with a real deductive engine. Neural Noir generates
a mystery from a seed — a cast of suspects, a hidden culprit, and a set of
clues — and **guarantees the clues uniquely identify the culprit** before it
ever hands you the case. You examine clues, interrogate suspects, and accuse.

The engine is pure Python (standard library only). An LLM is **optional** —
it can restyle the prose into a noir voice if a key is set, but it never
decides the mystery, the clues, or the verdict. Every case is generated,
solved, and played without one.

- **Live site:** https://andreaisabelmontana.github.io/neural-noir/
- **Index of all my builds:** https://andreaisabelmontana.github.io/coursework-rebuilds/

## The engine

### Generator (`noir/generator.py`)
From a seed it builds a cast of suspects, each described along five axes —
**means, motive, location, trait, transport** — using a small set of *shared*
values per axis so suspects overlap (no single attribute gives anyone away).
It picks a culprit, then writes clues phrased as constraints drawn from the
culprit's own attributes (`"The culprit reached the estate by a hired cab."`),
so a true clue can never eliminate the culprit. It greedily selects gentle
clues that each rule out only a few suspects — forcing you to *combine* clues —
then prunes the set until every remaining clue is load-bearing.

### Constraint solver (`noir/solver.py`)
`solve(suspects, clues)` keeps a suspect only if **every** clue implicates them,
and returns the survivors. A mystery is *uniquely solvable* iff exactly one
survives. `deduction_chain(...)` replays the elimination clue by clue as a
readable explanation.

### The uniqueness guarantee
The generator never *assumes* it succeeded. After building the clue set it runs
the independent solver and **only accepts a mystery when `solve()` returns
exactly the planted culprit** (regenerating with a perturbed seed otherwise).
Red herrings — true statements phrased so they match every suspect — are added
afterward and re-verified, so they add flavour without ever breaking
uniqueness. Each kept clue is marked `necessary`: removing it makes the case
ambiguous. The test suite checks all of this across hundreds of seeds and cast
sizes (see below).

### Game loop (`noir/game.py`)
`Game` wraps a mystery and exposes detective verbs as plain methods (usable as
a library or driven by `play()` in the console):

```
clues          list the clues on the board
ask <name>     interrogate a suspect — reveals which clues clear or implicate them
hint           how many suspects still fit every clue
accuse <name>  name the culprit; correct wins, wrong loses
```

A correct accusation wins; a wrong one loses and reveals the real culprit. Both
end with the full deduction chain.

### Optional LLM hook (`noir/llm.py`)
Strictly cosmetic. If `OPENAI_API_KEY` is set (or `NEURAL_NOIR_LLM=1`) **and**
the `openai` package is installed, `Flavor.dress()` asks the model to rewrite
the engine's already-computed text in a noir voice, under a prompt that forbids
changing any name, clue, or verdict. With no key it returns the engine's text
verbatim. The game is identical and fully playable either way.

## Run it

```bash
pip install -r requirements.txt   # only pytest; the engine needs nothing
python demo.py                    # seeded mystery + solver + deduction + accusation
python demo.py 99                 # any seed
python -m pytest -q               # 855 tests
```

Play interactively:

```python
from noir import generate_mystery, Game
Game(generate_mystery(7)).play()
```

## A real seeded example (`python demo.py 7`)

```
=== Murder Under the Conservatory Glass ===
Seed: 7
Case: the shooting of the art dealer Lucian Mercer.
Suspects: Captain Reyes, Inspector-General Pace, Professor Lott, Madame Duval, Sister Brevik

Clues on the board:
  [1] Every weapon in the house had been recently cleaned, including the kitchen knife.  [red herring]
  [2] The culprit reached the estate by a hired cab.  [necessary]
  [3] The whole party had passed through the billiard room earlier that evening.  [red herring]
  [4] The culprit was seen in the billiard room at the time of the crime.  [necessary]

Solver survivors: ['Captain Reyes']
Unique culprit: Captain Reyes  (planted culprit: Captain Reyes)

Deduction chain:
  CLUE: Every weapon in the house had been recently cleaned, including the kitchen knife.
    -> consistent with everyone still standing (red herring -- changes nothing)
  CLUE: The culprit reached the estate by a hired cab.
    -> rules out: Inspector-General Pace, Madame Duval, Sister Brevik
  CLUE: The whole party had passed through the billiard room earlier that evening.
    -> consistent with everyone still standing (red herring -- changes nothing)
  CLUE: The culprit was seen in the billiard room at the time of the crime.
    -> rules out: Professor Lott
  DEDUCTION: only Captain Reyes fits every clue. That is the culprit.

Simulated accusation (correct):
You accuse Captain Reyes. CORRECT. The case is closed.
won=True solved=True
```

Two clues do the work: the transport clue clears three suspects, the location
clue clears the fourth, leaving exactly one. Drop either and the case goes
ambiguous — which the tests verify.

## Tests

`python -m pytest -q` — **855 passing**. The suite hammers the central property:

- **Unique solvability** — for 200 seeds (and cast sizes 3–8), `solve()` returns
  exactly one suspect and it equals the planted culprit.
- **Clues do real work** — removing any `necessary` clue makes the solver return
  more than one suspect (the case becomes ambiguous).
- **Minimal clue sets** — no redundant real clue survives generation.
- **Red herrings are harmless** — they implicate everyone and dropping them all
  leaves the same unique culprit.
- **Game rules** — correct accusation wins, wrong one loses and reveals the truth.
- **Reproducibility** — the same seed yields an identical mystery.
- **LLM-optional** — a full game runs with the LLM off; the flavour layer is a
  verbatim pass-through when disabled.

## Layout

```
noir/
  model.py      suspects, clues, mystery (pure data)
  generator.py  seeded generation + uniqueness guarantee
  solver.py     constraint solver + deduction chain
  game.py       interactive game loop
  llm.py        optional, cosmetic LLM flavour hook
demo.py         seeded end-to-end demo
tests/          pytest suite (855 tests)
```

## Built with
Python 3.10+ standard library (no runtime dependencies); pytest for tests;
`openai` only if you opt into the optional flavour hook. MIT licensed.
