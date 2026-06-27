"""The core property tests: the generator's uniqueness guarantee.

These prove the engine's central claim -- that every generated mystery is
*uniquely* solvable and the lone survivor is the planted culprit -- and that
the clues are doing real work (removing a necessary clue breaks uniqueness).
"""

import itertools

import pytest

from noir import generate_mystery, solve
from noir.model import Clue
from noir.solver import is_uniquely_solvable

# A wide range of seeds and cast sizes.
SEEDS = list(range(0, 200))
SIZES = [3, 4, 5, 6, 7, 8]


@pytest.mark.parametrize("seed", SEEDS)
def test_every_mystery_is_uniquely_solvable(seed):
    """For many seeds: the solver returns exactly ONE suspect, and it is the
    planted culprit. This is the headline guarantee."""
    m = generate_mystery(seed, num_suspects=5)
    survivors = solve(m.suspects, m.clues)
    assert len(survivors) == 1, f"seed {seed}: expected 1 survivor, got {len(survivors)}"
    assert survivors[0] == m.culprit, f"seed {seed}: survivor is not the planted culprit"


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("seed", range(0, 40))
def test_uniqueness_across_cast_sizes(seed, size):
    """The guarantee holds for casts of 3..8 suspects."""
    m = generate_mystery(seed, num_suspects=size)
    assert m.culprit in m.suspects
    assert len(m.suspects) == size
    survivors = solve(m.suspects, m.clues)
    assert survivors == [m.culprit]


@pytest.mark.parametrize("seed", range(0, 120))
def test_removing_a_necessary_clue_breaks_uniqueness(seed):
    """Removing ANY clue flagged necessary must make the case ambiguous
    (solver returns >1). This proves the necessary clues are load-bearing,
    not decorative."""
    m = generate_mystery(seed, num_suspects=5)
    necessary = [c for c in m.clues if c.necessary]
    assert necessary, f"seed {seed}: a real mystery must have >=1 necessary clue"
    for i, clue in enumerate(m.clues):
        if not clue.necessary:
            continue
        without = m.clues[:i] + m.clues[i + 1:]
        survivors = solve(m.suspects, without)
        assert len(survivors) > 1, (
            f"seed {seed}: removing necessary clue '{clue.text}' still left a "
            f"unique solution -- it wasn't actually necessary"
        )


@pytest.mark.parametrize("seed", range(0, 120))
def test_red_herrings_never_break_uniqueness(seed):
    """Red herrings must eliminate nobody: dropping all of them leaves the
    same unique culprit, and they each implicate every suspect."""
    m = generate_mystery(seed, num_suspects=5, num_red_herrings=3)
    herrings = [c for c in m.clues if c.red_herring]
    # Each red herring implicates everyone (eliminates no one).
    for h in herrings:
        for s in m.suspects:
            assert h.implicates(s), f"seed {seed}: red herring eliminated {s.name}"
    # Removing every red herring leaves the solution unchanged.
    real_only = [c for c in m.clues if not c.red_herring]
    assert solve(m.suspects, real_only) == [m.culprit]
    # And the full set (with herrings) is still uniquely solvable.
    assert solve(m.suspects, m.clues) == [m.culprit]


@pytest.mark.parametrize("seed", range(0, 60))
def test_clue_set_is_minimal_no_redundant_real_clue(seed):
    """Every non-herring clue is necessary: there are no redundant real clues
    in the accepted set."""
    m = generate_mystery(seed, num_suspects=6)
    real = [c for c in m.clues if not c.red_herring]
    for i, clue in enumerate(real):
        without = real[:i] + real[i + 1:]
        # Without this real clue the case must NOT be uniquely solvable.
        assert not is_uniquely_solvable(m.suspects, without), (
            f"seed {seed}: real clue '{clue.text}' was redundant"
        )


def test_solver_returns_empty_for_contradiction():
    """If clues contradict (nobody satisfies all), the solver returns []."""
    m = generate_mystery(1, num_suspects=5)
    impossible = Clue(text="The culprit was on the moon.", predicate=lambda s: False)
    assert solve(m.suspects, m.clues + [impossible]) == []


def test_solver_returns_all_for_no_clues():
    """With no clues, nobody is eliminated."""
    m = generate_mystery(1, num_suspects=5)
    assert solve(m.suspects, []) == m.suspects
