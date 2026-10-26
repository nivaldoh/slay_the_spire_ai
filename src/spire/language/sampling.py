"""Seeded sampling from a language model's normalized distribution over legal choices.

The policy scores every canonical ``{"a":N}`` completion (see
``policy.candidate_log_probs``), normalizes those scores over the current
Decision's legal candidates at a declared temperature, and draws one choice with an
explicit per-episode RNG. Every draw and log-probability is recorded so a saved trace
can be re-audited without the model, and a learner can associate each action with
the exact behavior probabilities that produced it.
"""

from __future__ import annotations

import hashlib
import math
import random
import time

from gameai.lm import normalized, sample_index  # noqa: F401  (re-exported)
from spire.language.demonstrations import FORMAT_VERSION, render_prompt
from spire.protocol import Action, Decision, ProtocolError

SCORING = "canonical-choice-completion-sum-v1"
LOG_PROB_TOLERANCE = 1e-4


class CandidateSampler:
    """Policy-facing sampler: receives only the public Decision."""

    def __init__(self, scorer, *, seed: int, temperature: float, model_sha256: str):
        if not (math.isfinite(temperature) and temperature > 0):
            raise ValueError("Temperature must be positive and finite")
        self.scorer = scorer
        self.seed = seed
        self.temperature = temperature
        self.model_sha256 = model_sha256
        self._random = random.Random(seed)
        self._last_id = None
        self._last_metadata = None

    def choose(self, decision: Decision) -> Action:
        started = time.monotonic()
        scores, prompt_tokens = self.scorer(decision)
        if len(scores) != len(decision.candidates) or not all(map(math.isfinite, scores)):
            raise ProtocolError("Candidate scores differ from legal choices or are nonfinite")
        log_probs = normalized(scores, self.temperature)
        draw = self._random.random()
        index = sample_index(log_probs, draw)
        self._last_id = decision.id
        self._last_metadata = {
            "type": "language_sample",
            "prompt_format": FORMAT_VERSION,
            "scoring": SCORING,
            "prompt_sha256": hashlib.sha256(render_prompt(decision).encode()).hexdigest(),
            "prompt_tokens": prompt_tokens,
            "temperature": self.temperature,
            "candidate_log_probs": log_probs,
            "draw": draw,
            "selected_index": index,
            "model_sha256": self.model_sha256,
            "inference_seconds": time.monotonic() - started,
        }
        return decision.candidates[index]

    def choice_metadata(self, decision_id: str) -> dict:
        if decision_id != self._last_id or self._last_metadata is None:
            raise ValueError("No sampled language choice for this decision")
        return dict(self._last_metadata)


def check_sampled_behavior(decision: Decision, selected: Action, behavior) -> None:
    """Re-audit a recorded draw: public prompt, normalized log-probs and inverse CDF."""

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(isinstance(behavior, dict), "Missing sampled language behavior metadata")
    for name, expected in (
        ("type", "language_sample"),
        ("prompt_format", FORMAT_VERSION),
        ("scoring", SCORING),
    ):
        require(behavior.get(name) == expected, f"Unsupported sampled language {name}")
    require(
        behavior.get("prompt_sha256")
        == hashlib.sha256(render_prompt(decision).encode()).hexdigest(),
        "Sampled language prompt differs from public decision",
    )
    require(
        type(behavior.get("prompt_tokens")) is int and 1 <= behavior["prompt_tokens"] <= 2048,
        "Invalid sampled language prompt token count",
    )
    temperature = behavior.get("temperature")
    require(
        type(temperature) in (int, float) and math.isfinite(temperature) and temperature > 0,
        "Invalid sampling temperature",
    )
    log_probs = behavior.get("candidate_log_probs")
    require(
        isinstance(log_probs, list)
        and len(log_probs) == len(decision.candidates)
        and all(type(value) in (int, float) and math.isfinite(value) for value in log_probs),
        "Invalid candidate log-probabilities",
    )
    peak = max(log_probs)
    log_total = peak + math.log(sum(math.exp(value - peak) for value in log_probs))
    require(abs(log_total) <= LOG_PROB_TOLERANCE, "Candidate probabilities are not normalized")
    draw = behavior.get("draw")
    require(type(draw) is float and 0.0 <= draw < 1.0, "Invalid sampling draw")
    index = decision.candidates.index(selected)
    require(
        behavior.get("selected_index") == index == sample_index(log_probs, draw),
        "Recorded draw does not select the recorded action",
    )
    digest = behavior.get("model_sha256")
    require(
        isinstance(digest, str) and len(digest) == 64 and set(digest) <= set("0123456789abcdef"),
        "Invalid behavior model identity",
    )
    seconds = behavior.get("inference_seconds")
    require(
        type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0,
        "Invalid sampled inference duration",
    )
