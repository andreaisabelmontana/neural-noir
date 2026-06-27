"""Core data model for Neural Noir.

A mystery is a closed world: a fixed cast of suspects, each with a set of
attributes, exactly one culprit, and a list of clues. A clue is a logical
predicate over suspects -- it splits the cast into those it *implicates*
(could be the culprit) and those it *exonerates*.

Everything here is plain data + small pure functions. No randomness, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable


class Attr(str, Enum):
    """Attribute axes every suspect is described along."""

    MEANS = "means"          # the weapon / method they had access to
    MOTIVE = "motive"        # why they might have done it
    LOCATION = "location"    # where they were at the time of the crime
    TRAIT = "trait"          # a distinctive personal trait
    TRANSPORT = "transport"  # how they arrived at the scene


@dataclass(frozen=True)
class Suspect:
    """A single suspect. ``attrs`` maps each :class:`Attr` to a value."""

    name: str
    attrs: dict[Attr, str]

    def get(self, axis: Attr) -> str:
        return self.attrs[axis]

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.name


# A predicate decides whether a suspect is *consistent with being the culprit*
# given this clue. True  -> the clue keeps the suspect in the running.
# False -> the clue exonerates the suspect.
Predicate = Callable[[Suspect], bool]


@dataclass(frozen=True)
class Clue:
    """A single fact/testimony that constrains who the culprit can be.

    ``text`` is the human-readable statement shown to the player.
    ``predicate`` returns True for suspects the clue leaves *implicated*.
    ``red_herring`` marks clues that are true but eliminate nobody beyond
    what other clues already do (flavour that must never break uniqueness).
    ``necessary`` is filled in by the generator: True if removing this clue
    makes the solution ambiguous.
    """

    text: str
    predicate: Predicate = field(compare=False)
    red_herring: bool = False
    necessary: bool = False

    def implicates(self, suspect: Suspect) -> bool:
        return self.predicate(suspect)


@dataclass
class Mystery:
    """A fully generated, self-consistent mystery."""

    seed: int
    title: str
    crime: str
    suspects: list[Suspect]
    culprit: Suspect
    clues: list[Clue]

    def suspect_by_name(self, name: str) -> Suspect | None:
        low = name.strip().lower()
        for s in self.suspects:
            if s.name.lower() == low:
                return s
        return None

    def names(self) -> list[str]:
        return [s.name for s in self.suspects]
