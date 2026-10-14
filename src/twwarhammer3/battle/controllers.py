"""Fresh controllers and recorded trial rotation for a single battle instance."""

import importlib
import inspect
import math
import random
import secrets
import subprocess
from pathlib import Path

from gameai.provenance import sha256
from twwarhammer3.battle.scripted import POLICIES
from twwarhammer3.battle.skills import ProbeAbilities, Skills

BUILTINS = {**POLICIES, "skills": Skills, "probe_abilities": ProbeAbilities}
MODEL_POLICIES = {"llm", "commander"}


def rotation(config: dict) -> list[dict]:
    names = config["policy"].split(",")
    delays = [float(value) for value in str(config.get("delay_seconds", "0")).split(",")]
    if any(not math.isfinite(value) or value < 0 for value in delays):
        raise ValueError("delay seconds must be finite and nonnegative")
    for name in names:
        if name not in BUILTINS and name not in MODEL_POLICIES:
            controller_class(name)  # fail before launching on an invalid import
    trials = [{"policy": name, "delay_ms": round(delay * 1000)}
              for name in names for delay in delays]
    if len({(t["policy"], t["delay_ms"]) for t in trials}) != len(trials):
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
    result = {
        "name": name, "kind": "hybrid" if name == "commander" else
        "model" if name == "llm" else "scripted" if name in BUILTINS else "external",
        "class": f"{type(policy).__module__}:{type(policy).__qualname__}",
        "source_file": path, "source_sha256": sha256(Path(path)) if path else None,
        "model": config.get("model") if name in MODEL_POLICIES else None,
        "effort": config.get("effort") if name in MODEL_POLICIES else None,
        "timing": "asynchronous" if name == "commander" else "blocking",
        "disclosure": getattr(policy, "card", None),
        "description": inspect.getdoc(type(policy)),
        "cost_source": "WH3 ledger" if name in MODEL_POLICIES else "self-reported",
    }
    if path:
        revision = subprocess.run(["git", "-C", str(Path(path).parent), "rev-parse", "HEAD"],
                                  capture_output=True, text=True)
        result["source_revision"] = revision.stdout.strip() if revision.returncode == 0 else None
    return result


def factories(config: dict) -> dict:
    """Prepare constructors once; each trial calls one to get fresh episode state."""
    names = set(config["policy"].split(","))
    makers = {}
    if names & MODEL_POLICIES:
        from functools import partial

        from gameai.ledger import Ledger
        from gameai.llm import api_key, post
        from twwarhammer3.battle.commander import CommanderPolicy
        from twwarhammer3.battle.llm import LLMPolicy

        if config.get("budget_usd") is None:
            raise ValueError("llm and commander require --budget-usd")
        ledger = Ledger(Path(config["ledger"]), config["budget_usd"])
        send = partial(post, api_key())
        for name, kind in (("llm", LLMPolicy), ("commander", CommanderPolicy)):
            if name in names:
                makers[name] = partial(kind, config["model"], config["effort"], ledger, send=send)
    for name in names - MODEL_POLICIES:
        makers[name] = controller_class(name)
    return makers
