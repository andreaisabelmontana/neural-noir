"""Neural Noir -- a procedural mystery engine with guaranteed unique solvability.

The real engine is pure Python and needs no LLM. An optional LLM hook
(`noir.llm`) can render flavor text, but every mystery is generated, solved
and played without one.
"""

from .model import Suspect, Mystery, Clue
from .generator import generate_mystery
from .solver import solve, deduction_chain
from .game import Game

__all__ = [
    "Suspect",
    "Mystery",
    "Clue",
    "generate_mystery",
    "solve",
    "deduction_chain",
    "Game",
]

__version__ = "1.0.0"
