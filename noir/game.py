"""The interactive game loop.

`Game` wraps a `Mystery` and exposes the verbs a detective needs:
examine clues, interrogate a suspect (which reveals the constraints touching
them), and accuse. The class is fully usable as a library (every verb is a
plain method returning text), and `play()` drives a console session.

No LLM is required. If one is configured, `Game` will ask it to dress up
its output, but every word here is produced by pure Python otherwise.
"""

from __future__ import annotations

from .model import Mystery, Suspect
from .solver import deduction_chain, solve
from . import llm


class Game:
    def __init__(self, mystery: Mystery, use_llm: bool | None = None):
        self.m = mystery
        self.solved = False
        self.won = False
        # If use_llm is None, auto-detect (only on if a key/provider exists).
        self.flavor = llm.Flavor(enabled=use_llm)

    # -- information verbs ------------------------------------------------- #

    def briefing(self) -> str:
        intro = (
            f"=== {self.m.title} ===\n"
            f"Case: {self.m.crime}.\n"
            f"There are {len(self.m.suspects)} suspects. "
            f"Examine the clues, interrogate whoever you like, then accuse.\n"
            f"Suspects: {', '.join(self.m.names())}"
        )
        return self.flavor.dress("briefing", intro, self.m)

    def list_clues(self) -> str:
        lines = ["The clues on the board:"]
        for i, c in enumerate(self.m.clues, 1):
            lines.append(f"  [{i}] {c.text}")
        return "\n".join(lines)

    def interrogate(self, name: str) -> str:
        """Interrogating a suspect reveals which clues are consistent with
        them and which clues rule them out -- the constraint view the player
        reasons over."""
        suspect = self.m.suspect_by_name(name)
        if suspect is None:
            return f"No suspect named '{name}'. Known: {', '.join(self.m.names())}."

        fits, against = [], []
        for c in self.m.clues:
            (fits if c.implicates(suspect) else against).append(c)

        out = [f"You interrogate {suspect.name}."]
        if against:
            out.append("  These clues count AGAINST clearing them (they break their story):")
            for c in against:
                out.append(f"    - {c.text}")
        else:
            out.append("  No clue rules them out -- every clue is consistent with them.")
        if fits:
            out.append("  Consistent with:")
            for c in fits:
                out.append(f"    - {c.text}")

        body = "\n".join(out)
        return self.flavor.dress("interrogate", body, self.m, suspect=suspect)

    def hint(self) -> str:
        """Show how many suspects currently survive all clues."""
        survivors = solve(self.m.suspects, self.m.clues)
        names = ", ".join(s.name for s in survivors)
        return f"Suspects still consistent with every clue: {len(survivors)} ({names})."

    # -- the accusation ---------------------------------------------------- #

    def accuse(self, name: str) -> str:
        suspect = self.m.suspect_by_name(name)
        if suspect is None:
            return f"No suspect named '{name}'. Known: {', '.join(self.m.names())}."

        self.solved = True
        self.won = suspect == self.m.culprit
        verdict = "CORRECT" if self.won else "WRONG"

        chain = deduction_chain(self.m.suspects, self.m.clues)
        explanation = "\n".join(chain)

        if self.won:
            head = f"You accuse {suspect.name}. {verdict}. The case is closed."
        else:
            head = (
                f"You accuse {suspect.name}. {verdict}. "
                f"The real culprit was {self.m.culprit.name}."
            )
        body = f"{head}\n\nThe deduction:\n{explanation}"
        return self.flavor.dress("accuse", body, self.m, suspect=suspect)

    # -- console driver ---------------------------------------------------- #

    def play(self, input_fn=input, output_fn=print) -> None:  # pragma: no cover
        output_fn(self.briefing())
        output_fn("\nCommands: clues | ask <name> | hint | accuse <name> | quit\n")
        while not self.solved:
            try:
                raw = input_fn("> ").strip()
            except (EOFError, KeyboardInterrupt):
                output_fn("\nLeaving the case unsolved.")
                return
            if not raw:
                continue
            cmd, _, arg = raw.partition(" ")
            cmd = cmd.lower()
            if cmd in ("quit", "exit", "q"):
                output_fn("Leaving the case unsolved.")
                return
            elif cmd in ("clues", "clue", "c"):
                output_fn(self.list_clues())
            elif cmd in ("ask", "interrogate", "i"):
                output_fn(self.interrogate(arg))
            elif cmd in ("hint", "h"):
                output_fn(self.hint())
            elif cmd in ("accuse", "a"):
                output_fn(self.accuse(arg))
            else:
                output_fn("Unknown command. Try: clues | ask <name> | hint | accuse <name> | quit")
