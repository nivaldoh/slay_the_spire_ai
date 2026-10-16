"""The policies a job can name, fresh controllers per trial, controller cards and the
recorded trial rotation.

A model policy name may carry its own model and effort: ``llm_rules@gpt-6-luna`` or
``llm_rules@gpt-6-luna/medium``; the bare name uses the job's --model and --effort.
"""

import importlib
import inspect
import math
import random
import secrets
import subprocess
from functools import partial
from pathlib import Path

from gameai.ledger import Ledger
from gameai.llm import EFFORTS, PRICES, api_key, post
from gameai.provenance import sha256
from twwarhammer3.battle import commander, llm
from twwarhammer3.battle.scripted import POLICIES
from twwarhammer3.battle.skills import ProbeAbilities, Skills

BUILTINS = {**POLICIES, "skills": Skills, "probe_abilities": ProbeAbilities}
# The paid model controllers and their system prompts, which play snapshots per job.
MODEL_PROMPTS = {"llm": llm.SYSTEM_PROMPT_PATH, "llm_rules": llm.RULES_PROMPT_PATH,
                 "commander": commander.PROMPT_PATH}
MODEL_POLICIES = frozenset(MODEL_PROMPTS)
VERSIONS = {"llm": "v18", "llm_rules": "v18", "commander": "v5", "skills": "v1.2"}


def policy_parts(name: str, config: dict) -> tuple[str, str | None, str | None]:
    """A policy name's base name and the model and effort it plays with: a model policy's
    ``@MODEL[/EFFORT]`` suffix, else the job's; None for other policies. Readers of recorded
    jobs use it too, so only rotation checks the suffix against today's prices."""
    base, separator, suffix = name.partition("@")
    if base not in MODEL_POLICIES:
        if separator:
            raise ValueError(f"{name}: only {', '.join(sorted(MODEL_POLICIES))} take @MODEL")
        return name, None, None
    model, _, effort = suffix.partition("/")
    return base, model or config.get("model"), effort or config.get("effort")


def rotation(config: dict) -> list[dict]:
    names = config["policy"].split(",")
    delays = [float(value) for value in str(config.get("delay_seconds", "0")).split(",")]
    if any(not math.isfinite(value) or value < 0 for value in delays):
        raise ValueError("delay seconds must be finite and nonnegative")
    # Two names are one controller when their base, model and effort match.
    identity = {name: policy_parts(name, config) for name in names}
    for name, (base, _, _) in identity.items():
        model, slash, effort = name.partition("@")[2].partition("/")
        if "@" in name and (model not in PRICES or slash and effort not in EFFORTS):
            raise ValueError(f"{name}: use {base}@MODEL or {base}@MODEL/EFFORT with a model in "
                             f"{', '.join(sorted(PRICES))} and an effort in {', '.join(EFFORTS)}")
        if base not in BUILTINS and base not in MODEL_POLICIES:
            controller_class(name)  # fail before launching on an invalid import
    trials = [{"policy": name, "delay_ms": round(delay * 1000)}
              for name in names for delay in delays]
    if len({(identity[t["policy"]], t["delay_ms"]) for t in trials}) != len(trials):
        raise ValueError("duplicate controller/delay entry; use --episodes for repeats")
    count = config["episodes"] if config.get("episodes") is not None else len(trials)
    if count < len(trials):
        raise ValueError("episodes must include every controller/delay combination")
    if config.get("rotation_seed") is None:
        config["rotation_seed"] = secrets.randbelow(2**31)
    rng = random.Random(config["rotation_seed"])
    ordered = []
    while len(ordered) < count:
        block = [dict(trial) for trial in trials]
        rng.shuffle(block)
        ordered.extend(block)
    config["episodes"] = count
    return ordered[:count]


def controller_class(name: str):
    if name in BUILTINS:
        return BUILTINS[name]
    module, separator, attribute = name.partition(":")
    if not separator or not module or not attribute:
        raise ValueError(f"unknown policy {name!r}; use a built-in name or package.module:Class")
    kind = getattr(importlib.import_module(module), attribute)
    if not inspect.isclass(kind) or any(not callable(getattr(kind, method, None))
                                      for method in ("decide", "acknowledge", "metadata")):
        raise ValueError(f"{name} must be a class with decide, acknowledge and metadata")
    return kind


def card(name: str, policy, config: dict) -> dict:
    path = inspect.getsourcefile(type(policy))
    base, model, effort = policy_parts(name, config)
    result = {
        "name": name, "kind": "hybrid" if base == "commander" else
        "model" if base in MODEL_POLICIES else "scripted" if base in BUILTINS else "external",
        "version": VERSIONS.get(base),
        "class": f"{type(policy).__module__}:{type(policy).__qualname__}",
        "source_file": path, "source_sha256": sha256(Path(path)) if path else None,
        "model": model, "effort": effort,
        "timing": "asynchronous" if base == "commander" else "blocking",
        "disclosure": getattr(policy, "card", None),
        "description": inspect.getdoc(type(policy)),
        "cost_source": "WH3 ledger" if base in MODEL_POLICIES else "self-reported",
    }
    if path:
        revision = subprocess.run(["git", "-C", str(Path(path).parent), "rev-parse", "HEAD"],
                                  capture_output=True, text=True)
        result["source_revision"] = revision.stdout.strip() if revision.returncode == 0 else None
    return result


def factories(config: dict) -> dict:
    """Prepare constructors once; each trial calls one to get fresh episode state."""
    parts = {name: policy_parts(name, config) for name in config["policy"].split(",")}
    models = {name for name, (base, _, _) in parts.items() if base in MODEL_POLICIES}
    makers = {}
    if models:
        if config.get("budget_usd") is None:
            raise ValueError("model controllers require --budget-usd")
        ledger = Ledger(Path(config["ledger"]), config["budget_usd"])
        send = partial(post, api_key(), record_transport=True)
        for name in models:
            base, model, effort = parts[name]
            kind = commander.CommanderPolicy if base == "commander" else llm.LLMPolicy
            makers[name] = partial(kind, model, effort, ledger, send=send,
                                   system_prompt=MODEL_PROMPTS[base].read_text())
    for name in parts.keys() - models:
        makers[name] = controller_class(name)
    return makers
