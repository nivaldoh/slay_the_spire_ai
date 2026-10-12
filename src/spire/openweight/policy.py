"""An open-weight model choosing among a Decision's labeled choices through Tinker.

It has the interface of ``spire.fullrun.llm.LLMPolicy`` (``choose``, ``choice_metadata``,
``totals``), so ``spire.fullrun.play.play`` can run it on the real game for stage B
baselines, and ``rollout`` can run it on any ``env`` backend. Its metadata keeps the
sampled tokens and their log-probabilities, which a GRPO update needs.

The prompt and reply formats are part of a trained policy: version them, and never change
them under a trained adapter. Both are placeholders, as is ending the episode on an invalid
reply rather than re-asking.
"""

from __future__ import annotations

from collections import Counter

from spire.decisions import Choice
from spire.fullrun.llm import render_state
from spire.openweight.remote import TinkerSession
from spire.protocol import Decision, PolicyFailure

PROMPT_FORMAT = "openweight-v0"


def render_prompt(decision: Decision) -> str:
    """The full-run state text and numbered choices, without notes or history."""
    choices = "\n".join(f"{i}: {c.label}" for i, c in enumerate(decision.candidates))
    state = render_state(decision.to_dict()["observation"])
    return f"State:\n{state}\n\nChoices:\n{choices}\n\nReply with one choice number."


class SampledPolicy:
    """One instance per episode."""

    def __init__(self, session: TinkerSession, *, temperature: float = 1.0):
        self.session, self.temperature = session, temperature
        self.totals = Counter()
        self._last_id = self._metadata = None

    def choose(self, decision: Decision) -> Choice:
        prompt = render_prompt(decision)
        sample = self.session.sample(prompt, 1, temperature=self.temperature)[0]
        self.totals.update(calls=1, prompt_tokens=len(sample.prompt_tokens),
                           sampled_tokens=len(sample.tokens))
        self._last_id = decision.id
        self._metadata = {"type": "open_weight", "model": self.session.model,
                          "format": PROMPT_FORMAT, "prompt": prompt, "sample": sample}
        text = sample.text.strip()
        if not text.isdigit() or int(text) >= len(decision.candidates):
            raise PolicyFailure("Invalid reply", failure={"kind": "invalid_reply", "text": text})
        return decision.candidates[int(text)]

    def choice_metadata(self, decision_id: str) -> dict:
        if decision_id != self._last_id or self._metadata is None:
            raise ValueError("No sampled reply for this decision")
        return self._metadata
