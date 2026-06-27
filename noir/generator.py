"""The mystery generator.

Strategy for a *guaranteed* unique solution:

1. Build a cast of suspects, each given a value on every attribute axis.
   Within an axis the values are dealt without repetition where possible
   so clues can discriminate cleanly.
2. Pick a culprit.
3. Generate candidate clues. Every clue is a true statement about the
   crime scene phrased as a constraint ("the culprit arrived by car"),
   built from the *culprit's own* attribute values -- so the culprit is
   never eliminated, by construction.
4. Greedily select clues until every other suspect has been eliminated by
   at least one selected clue. Because each selected clue only ever rules
   out non-culprits, the culprit is always among the survivors; once every
   non-culprit is ruled out, the culprit is the *unique* survivor.
5. Verify with the independent solver. Add red-herring clues (true facts
   that match the culprit and therefore eliminate nobody) and re-verify.
6. Mark which selected clues are strictly necessary (removing one makes the
   solution ambiguous again).

Step 5's verification means the uniqueness property is never assumed -- it
is checked by the same solver the player's game uses.
"""

from __future__ import annotations

import random

from .model import Attr, Clue, Mystery, Suspect
from .solver import solve

# --------------------------------------------------------------------------- #
# Flavour vocabulary. Each axis has a pool of distinct values plus a phrasing
# template so a clue reads like a line from a detective story.
# --------------------------------------------------------------------------- #

VALUES: dict[Attr, list[str]] = {
    Attr.MEANS: [
        "the lead pipe", "the antique revolver", "the kitchen knife",
        "the silk cord", "the heavy candlestick", "the vial of poison",
        "the letter opener", "the wrench",
    ],
    Attr.MOTIVE: [
        "a gambling debt", "a jilted romance", "a contested inheritance",
        "professional jealousy", "blackmail", "a buried scandal",
        "revenge for a ruined career", "a stolen invention",
    ],
    Attr.LOCATION: [
        "the library", "the conservatory", "the wine cellar",
        "the billiard room", "the east terrace", "the boathouse",
        "the study", "the servants' stair",
    ],
    Attr.TRAIT: [
        "a limp", "a signet ring", "ink-stained fingers",
        "a heavy cologne", "a quick temper", "a foreign accent",
        "a nervous cough", "left-handedness",
    ],
    Attr.TRANSPORT: [
        "the night train", "a motorcar", "on foot through the rain",
        "a rowing boat", "a hired cab", "a bicycle",
        "the early ferry", "horseback",
    ],
}

# How each axis is phrased as a constraint on the culprit.
PHRASING: dict[Attr, str] = {
    Attr.MEANS: "The killing was done with {v}.",
    Attr.MOTIVE: "Whoever did it was driven by {v}.",
    Attr.LOCATION: "The culprit was seen in {v} at the time of the crime.",
    Attr.TRAIT: "A witness recalls the culprit had {v}.",
    Attr.TRANSPORT: "The culprit reached the estate by {v}.",
}

# Phrasing for red herrings -- true, but shared by everyone so they cut nobody.
HERRING_PHRASING: dict[Attr, str] = {
    Attr.MEANS: "Every weapon in the house had been recently cleaned, including {v}.",
    Attr.MOTIVE: "Old letters hint that more than one guest knew of {v}.",
    Attr.LOCATION: "The whole party had passed through {v} earlier that evening.",
    Attr.TRAIT: "Several guests, by chance, shared {v}.",
    Attr.TRANSPORT: "The roads were busy that night; many arrived by {v}.",
}

NAMES = [
    "Colonel Hargreave", "Dr. Vane", "Miss Ashby", "Professor Lott",
    "Mrs. Fenwick", "Mr. Calloway", "Lady Orme", "Captain Reyes",
    "Sister Brevik", "Mr. Okonkwo", "Madame Duval", "Inspector-General Pace",
]

CRIMES = [
    "the poisoning of the railway magnate Edmund Royce",
    "the strangling of the heiress Cordelia Vane",
    "the shooting of the art dealer Lucian Mercer",
    "the drowning of the yacht owner Tobias Crane",
    "the stabbing of the novelist Hadley Frost",
]

TITLES = [
    "A Death at Blackwater Hall",
    "The Last Train from Thorne",
    "Murder Under the Conservatory Glass",
    "The Silence at Ravensmoor",
    "An Evening that Ended in Blood",
]


def _deal(rng: random.Random, axis: Attr, n: int, distinct: int) -> list[str]:
    """Assign one value per suspect on ``axis``, drawn from only ``distinct``
    options so values *overlap*.

    Overlap is the whole point: if every suspect had a unique value, a single
    clue would crack the case. By restricting each axis to a handful of shared
    values, no one clue is enough -- the player must intersect several. We
    guarantee every chosen value is actually used (and reused) so each clue
    eliminates *some* but not *all* other suspects.
    """
    pool = list(VALUES[axis])
    rng.shuffle(pool)
    k = max(1, min(distinct, len(pool), n))
    options = pool[:k]
    # Start by using each option once (so each appears), then fill the rest
    # randomly from the same small option set -> guaranteed overlaps when k < n.
    assignment = list(options)
    while len(assignment) < n:
        assignment.append(rng.choice(options))
    rng.shuffle(assignment)
    return assignment[:n]


def _make_clue(axis: Attr, value: str) -> Clue:
    """A discriminating clue: implicates exactly the suspects whose value on
    ``axis`` equals ``value`` (i.e. the culprit and any twin)."""
    text = PHRASING[axis].format(v=value)
    return Clue(text=text, predicate=lambda s: s.attrs[axis] == value)


def _make_herring(axis: Attr, value: str) -> Clue:
    """A red herring: literally true of the culprit but phrased as universal,
    so its predicate implicates everyone and it eliminates no one."""
    text = HERRING_PHRASING[axis].format(v=value)
    return Clue(text=text, predicate=lambda s: True, red_herring=True)


def generate_mystery(
    seed: int,
    num_suspects: int = 5,
    num_red_herrings: int = 2,
) -> Mystery:
    """Generate a mystery that is *guaranteed* uniquely solvable.

    Raises ``ValueError`` for impossible parameters. The returned mystery has
    passed an independent solver check: ``solve(suspects, clues)`` yields
    exactly the culprit.
    """
    if num_suspects < 2:
        raise ValueError("need at least 2 suspects")
    if num_suspects > len(NAMES):
        raise ValueError(f"at most {len(NAMES)} suspects supported")

    rng = random.Random(seed)

    # --- 1. Build the cast -------------------------------------------------
    names = list(NAMES)
    rng.shuffle(names)
    names = names[:num_suspects]

    # Each axis uses only a few distinct values so suspects overlap and no
    # single clue solves the case. ~half as many options as suspects gives a
    # satisfying puzzle that still admits a unique solution.
    distinct = max(2, num_suspects // 2 + 1)

    axes = list(Attr)
    dealt: dict[Attr, list[str]] = {
        ax: _deal(rng, ax, num_suspects, distinct) for ax in axes
    }

    suspects: list[Suspect] = []
    for i, nm in enumerate(names):
        attrs = {ax: dealt[ax][i] for ax in axes}
        suspects.append(Suspect(name=nm, attrs=attrs))

    # --- 2. Pick the culprit ----------------------------------------------
    culprit = rng.choice(suspects)

    # --- 3/4. Build discriminating clues from the culprit's own attributes -
    # For each axis, a clue stating the culprit's value rules out exactly the
    # suspects whose value on that axis differs. We want the player to have to
    # *combine* clues, so we prefer clues that each eliminate only a few
    # suspects, then prune any clue that turns out redundant. The result: a
    # minimal clue set where every clue is necessary, and (usually) several
    # clues must be intersected to isolate the culprit.
    others = [s for s in suspects if s is not culprit]

    def elimset(axis: Attr) -> set[str]:
        value = culprit.attrs[axis]
        return {s.name for s in others if s.attrs[axis] != value}

    # Order axes by how few suspects they eliminate (ascending), so we pick
    # gentle clues first and force multi-clue deductions. Ties broken randomly
    # for per-seed variety.
    candidates = [ax for ax in axes if elimset(ax)]
    rng.shuffle(candidates)
    candidates.sort(key=lambda ax: len(elimset(ax)))

    selected_axes: list[Attr] = []
    uncovered = set(s.name for s in others)
    for axis in candidates:
        if not uncovered:
            break
        newly = elimset(axis) & uncovered
        if newly:
            selected_axes.append(axis)
            uncovered -= newly

    if uncovered:
        # Some suspect matches the culprit on every axis (a "twin"): this seed
        # has no clue-based unique solution. Re-deal with a perturbed seed.
        return generate_mystery(seed + 1_000_003, num_suspects, num_red_herrings)

    # Prune redundant clues: keep only those whose removal would re-introduce
    # ambiguity. Iterate in reverse so we drop later (broader) clues first.
    kept_axes = list(selected_axes)
    changed = True
    while changed:
        changed = False
        for axis in list(kept_axes):
            trial = [a for a in kept_axes if a != axis]
            covered = set()
            for a in trial:
                covered |= elimset(a)
            if covered == set(s.name for s in others):
                kept_axes = trial
                changed = True
                break

    selected = [_make_clue(ax, culprit.attrs[ax]) for ax in kept_axes]

    # --- 5. Verify uniqueness with the independent solver ------------------
    survivors = solve(suspects, selected)
    if survivors != [culprit]:
        # Should never happen by construction; guard anyway.
        return generate_mystery(seed + 7_919, num_suspects, num_red_herrings)

    # --- 6. Mark necessary clues (removing one => ambiguous) ---------------
    final: list[Clue] = []
    for i, clue in enumerate(selected):
        without = selected[:i] + selected[i + 1:]
        necessary = len(solve(suspects, without)) != 1
        final.append(Clue(text=clue.text, predicate=clue.predicate,
                          red_herring=clue.red_herring, necessary=necessary))

    # --- Add red herrings (eliminate nobody; never break uniqueness) -------
    herrings: list[Clue] = []
    used_axes = list(axes)
    rng.shuffle(used_axes)
    for ax in used_axes[:num_red_herrings]:
        herrings.append(_make_herring(ax, culprit.attrs[ax]))

    # Interleave herrings among real clues so the player must sift them out.
    all_clues = final + herrings
    rng.shuffle(all_clues)

    # Final paranoia check including herrings.
    assert solve(suspects, all_clues) == [culprit], "uniqueness violated by herrings"

    title = rng.choice(TITLES)
    crime = rng.choice(CRIMES)

    return Mystery(
        seed=seed,
        title=title,
        crime=crime,
        suspects=suspects,
        culprit=culprit,
        clues=all_clues,
    )
