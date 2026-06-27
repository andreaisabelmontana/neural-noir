"""Optional LLM flavour hook -- strictly cosmetic.

The mystery engine, solver and game are complete without this module. If an
LLM is configured, `Flavor.dress()` will ask it to rewrite the engine's plain
text in a noir voice. If not, it returns the engine's text unchanged.

The LLM is NEVER allowed to decide the mystery, the clues or the verdict --
it only restyles already-computed strings. This keeps the game deterministic
and fully playable offline.

Detection: an LLM is considered available only if BOTH
  * the `OPENAI_API_KEY` (or `NEURAL_NOIR_LLM=1`) environment variable is set,
  * and the `openai` package is importable.
Neither is required to play.
"""

from __future__ import annotations

import os
from typing import Optional

from .model import Mystery, Suspect


def llm_available() -> bool:
    """True only if a real LLM could be called right now."""
    if os.environ.get("NEURAL_NOIR_LLM") == "0":
        return False
    has_key = bool(os.environ.get("OPENAI_API_KEY")) or os.environ.get("NEURAL_NOIR_LLM") == "1"
    if not has_key:
        return False
    try:
        import openai  # noqa: F401
    except Exception:
        return False
    return True


class Flavor:
    """Thin, optional restyler. Default behaviour: pass text through verbatim."""

    def __init__(self, enabled: Optional[bool] = None, model: str = "gpt-4o-mini"):
        if enabled is None:
            enabled = llm_available()
        self.enabled = bool(enabled) and llm_available()
        self.model = model

    def dress(self, scene: str, text: str, mystery: Mystery,
              suspect: Optional[Suspect] = None) -> str:
        """Return `text`, optionally rewritten in a noir voice by an LLM.

        On any error -- no key, no package, network failure -- the original
        engine text is returned. Facts are never altered: the prompt forbids
        changing names, the verdict, or which clues rule whom out.
        """
        if not self.enabled:
            return text
        try:  # pragma: no cover - network path, not exercised in tests
            import openai

            client = openai.OpenAI()
            sys_prompt = (
                "You are the narrator of a noir detective game. Rewrite the "
                "user's text in a terse, atmospheric noir voice. You MUST NOT "
                "change any name, any clue, the list of who is ruled out, or "
                "the final verdict. Keep every fact identical; only change the "
                "prose style. Do not add new clues or reveal the culprit early."
            )
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"[scene: {scene}]\n{text}"},
                ],
                temperature=0.7,
            )
            styled = resp.choices[0].message.content
            return styled.strip() if styled else text
        except Exception:
            return text
