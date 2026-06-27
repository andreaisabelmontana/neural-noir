"""Demo: generate a seeded mystery, print clues, run the solver to show the
unique culprit and the deduction chain, then simulate a correct accusation.

Run:  python demo.py [seed]

Everything here is pure Python. No LLM is used or required.
"""

from __future__ import annotations

import sys

from noir import generate_mystery, solve, deduction_chain, Game


def main(seed: int = 7) -> None:
    m = generate_mystery(seed, num_suspects=5, num_red_herrings=2)

    print(f"=== {m.title} ===")
    print(f"Seed: {m.seed}")
    print(f"Case: {m.crime}.")
    print(f"Suspects: {', '.join(m.names())}")
    print()

    print("Clues on the board:")
    for i, c in enumerate(m.clues, 1):
        tag = "  [red herring]" if c.red_herring else ("  [necessary]" if c.necessary else "")
        print(f"  [{i}] {c.text}{tag}")
    print()

    survivors = solve(m.suspects, m.clues)
    print(f"Solver survivors: {[s.name for s in survivors]}")
    assert len(survivors) == 1, "engine guarantees a unique solution"
    assert survivors[0] == m.culprit, "the survivor is the planted culprit"
    print(f"Unique culprit: {survivors[0].name}  (planted culprit: {m.culprit.name})")
    print()

    print("Deduction chain:")
    for line in deduction_chain(m.suspects, m.clues):
        print("  " + line.replace("\n", "\n  "))
    print()

    # Simulate a correct accusation through the game loop.
    game = Game(m, use_llm=False)
    print("Simulated accusation (correct):")
    result = game.accuse(m.culprit.name)
    print(result.splitlines()[0])
    print(f"won={game.won} solved={game.solved}")


if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    main(seed)
