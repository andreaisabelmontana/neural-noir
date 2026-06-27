"""Game-loop and reproducibility tests."""

import pytest

from noir import generate_mystery, Game
from noir.solver import deduction_chain


@pytest.mark.parametrize("seed", range(0, 50))
def test_correct_accusation_wins(seed):
    m = generate_mystery(seed, num_suspects=5)
    g = Game(m, use_llm=False)
    out = g.accuse(m.culprit.name)
    assert g.won is True
    assert g.solved is True
    assert "CORRECT" in out


@pytest.mark.parametrize("seed", range(0, 50))
def test_wrong_accusation_loses(seed):
    m = generate_mystery(seed, num_suspects=5)
    innocent = next(s for s in m.suspects if s != m.culprit)
    g = Game(m, use_llm=False)
    out = g.accuse(innocent.name)
    assert g.won is False
    assert g.solved is True
    assert "WRONG" in out
    # The real culprit is revealed on a loss.
    assert m.culprit.name in out


def test_generation_is_reproducible_per_seed():
    """Same seed -> identical mystery (title, crime, culprit, clue texts)."""
    a = generate_mystery(123, num_suspects=6)
    b = generate_mystery(123, num_suspects=6)
    assert a.title == b.title
    assert a.crime == b.crime
    assert a.culprit.name == b.culprit.name
    assert [s.name for s in a.suspects] == [s.name for s in b.suspects]
    assert [c.text for c in a.clues] == [c.text for c in b.clues]


def test_different_seeds_differ():
    """Different seeds generally produce different cases (sanity, not a law)."""
    cases = {generate_mystery(s, num_suspects=6).culprit.name for s in range(20)}
    assert len(cases) > 1


def test_interrogation_reveals_constraints():
    m = generate_mystery(7, num_suspects=5)
    g = Game(m, use_llm=False)
    # Interrogating the culprit: no real clue should rule them out.
    out = g.interrogate(m.culprit.name)
    assert m.culprit.name in out
    assert "rules them out" in out or "consistent" in out


def test_interrogate_unknown_name():
    m = generate_mystery(7, num_suspects=5)
    g = Game(m, use_llm=False)
    assert "No suspect" in g.interrogate("Nobody McGhost")


def test_accuse_unknown_name_does_not_solve():
    m = generate_mystery(7, num_suspects=5)
    g = Game(m, use_llm=False)
    out = g.accuse("Nobody McGhost")
    assert "No suspect" in out
    assert g.solved is False


def test_deduction_chain_names_the_culprit():
    m = generate_mystery(7, num_suspects=5)
    chain = "\n".join(deduction_chain(m.suspects, m.clues))
    assert m.culprit.name in chain
    assert "That is the culprit" in chain


def test_hint_reports_single_survivor():
    m = generate_mystery(7, num_suspects=5)
    g = Game(m, use_llm=False)
    assert "1 (" in g.hint()


def test_briefing_and_clue_listing_render():
    m = generate_mystery(7, num_suspects=5)
    g = Game(m, use_llm=False)
    assert m.title in g.briefing()
    listing = g.list_clues()
    for c in m.clues:
        assert c.text in listing


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        generate_mystery(1, num_suspects=1)
    with pytest.raises(ValueError):
        generate_mystery(1, num_suspects=99)
