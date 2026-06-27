"""The LLM must be strictly optional. These tests run with NO LLM and prove
the game is fully functional, and that the flavour layer is a no-op pass-through
when disabled."""

import os

from noir import generate_mystery, Game
from noir.llm import Flavor, llm_available


def test_game_fully_playable_without_llm():
    """A whole game -- briefing, clues, interrogation, accusation -- runs with
    the LLM explicitly off."""
    m = generate_mystery(7, num_suspects=5)
    g = Game(m, use_llm=False)
    assert g.flavor.enabled is False
    assert m.title in g.briefing()
    assert g.list_clues()
    for s in m.suspects:
        assert g.interrogate(s.name)
    out = g.accuse(m.culprit.name)
    assert g.won is True
    assert "CORRECT" in out


def test_flavor_disabled_is_identity():
    """When disabled, dress() returns its input verbatim."""
    m = generate_mystery(1, num_suspects=4)
    f = Flavor(enabled=False)
    text = "A body in the library."
    assert f.dress("briefing", text, m) == text


def test_llm_not_available_without_key(monkeypatch):
    """No key / disabled env -> not available, and Flavor stays off even if a
    caller asks for it."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("NEURAL_NOIR_LLM", "0")
    assert llm_available() is False
    f = Flavor(enabled=True)  # request on, but no backend -> stays off
    assert f.enabled is False


def test_default_game_does_not_require_llm():
    """The default Game (use_llm=None auto-detect) must still be playable; in a
    keyless test environment it should auto-disable."""
    # Ensure no key is visible for this test.
    old = os.environ.pop("OPENAI_API_KEY", None)
    try:
        m = generate_mystery(3, num_suspects=5)
        g = Game(m)  # auto-detect
        out = g.accuse(m.culprit.name)
        assert g.won is True
        assert "CORRECT" in out
    finally:
        if old is not None:
            os.environ["OPENAI_API_KEY"] = old
