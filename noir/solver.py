"""The deduction solver.

Given a cast of suspects and a set of clues, the solver eliminates every
suspect contradicted by a clue and returns whoever survives. The mystery
is *uniquely solvable* iff exactly one suspect survives.

This is deliberately simple and transparent -- a constraint-propagation
pass -- so the deduction can be replayed step by step for the player.
"""

from __future__ import annotations

from .model import Clue, Suspect


def solve(suspects: list[Suspect], clues: list[Clue]) -> list[Suspect]:
    """Return the suspects consistent with *all* clues.

    A suspect survives only if every clue implicates them. The returned
    list preserves the input order.
    """
    survivors: list[Suspect] = []
    for s in suspects:
        if all(clue.implicates(s) for clue in clues):
            survivors.append(s)
    return survivors


def is_uniquely_solvable(suspects: list[Suspect], clues: list[Clue]) -> bool:
    """True iff the clues narrow the cast to exactly one suspect."""
    return len(solve(suspects, clues)) == 1


def deduction_chain(suspects: list[Suspect], clues: list[Clue]) -> list[str]:
    """Replay the elimination as an ordered, human-readable explanation.

    Walks the clues in order, applying each to the still-standing pool and
    recording who it rules out. Red-herring clues (which eliminate nobody
    new) are reported as such. Ends by naming the lone survivor.
    """
    lines: list[str] = []
    pool = list(suspects)

    for clue in clues:
        eliminated = [s for s in pool if not clue.implicates(s)]
        if eliminated:
            pool = [s for s in pool if clue.implicates(s)]
            who = ", ".join(s.name for s in eliminated)
            lines.append(f"CLUE: {clue.text}\n  -> rules out: {who}")
        else:
            tag = " (red herring -- changes nothing)" if clue.red_herring else " (no new eliminations)"
            lines.append(f"CLUE: {clue.text}\n  -> consistent with everyone still standing{tag}")

    if len(pool) == 1:
        lines.append(f"DEDUCTION: only {pool[0].name} fits every clue. That is the culprit.")
    elif not pool:
        lines.append("DEDUCTION: no suspect fits every clue -- the case is contradictory.")
    else:
        remaining = ", ".join(s.name for s in pool)
        lines.append(f"DEDUCTION: ambiguous -- {remaining} all still fit. Not enough clues.")

    return lines
