"""Complete original-engine runs driven by a full-run policy, one fresh JVM per run.

The policy decides everything from Neow onward. Forced single-choice states are
answered without a policy call, and initial ``DEBUG`` enemy intents are settled
with a logged ``wait`` as in first-combat rollouts. Only the engine's death or
victory screen is a gameplay outcome.
"""

from __future__ import annotations

import json
import math
import shutil
import sys
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from spire.engine.bridge import BridgeError, BridgeServer
from spire.engine.doctor import collect_profile
from spire.engine.runtime import (
    BRIDGE_PORT,
    GAME_DIR,
    OwnedGame,
    RuntimeLock,
    prepare_runtime,
    wsl_bridge_host,
)
from spire.fullrun import decisions
from spire.fullrun.api import BudgetExhausted
from spire.fullrun.llm import SYSTEM_PROMPT_PATH
from spire.protocol import BridgeCommandError, IllegalActionError, PolicyFailure, ProtocolError
from spire.provenance import committed_revision, sha256, source_fingerprints, write_json

# A run that ends in one of these is a scored attempt; anything else stops the job.
SCORED = {"won", "lost", "policy_failure", "truncated"}


def _unsettled(message: dict) -> bool:
    combat = (message.get("game_state") or {}).get("combat_state") or {}
    monsters = combat.get("monsters", [])
    return any(monsters[i].get("intent") == "DEBUG" for i in decisions.live_targets(monsters))


def _summary(state: dict) -> dict:
    return {
        "act": state.get("act"),
        "floor": state.get("floor"),
        "current_hp": state.get("current_hp"),
        "max_hp": state.get("max_hp"),
        "gold": state.get("gold"),
        "deck_size": len(state.get("deck", [])),
        "relics": [relic.get("id") for relic in state.get("relics", [])],
    }


def play_run(directory: Path, config: dict, policy) -> dict:
    directory.mkdir(exist_ok=False)
    started = time.monotonic()
    deadline = started + config["run_timeout"]
    session_id = uuid.uuid4().hex
    result = {"seed": config["seed"], "session_id": session_id, "status": "interrupted",
              "actions": 0, "decisions": 0, "policy_calls": 0, "settle_waits": 0}
    write_json(directory / "profile.json", collect_profile(GAME_DIR))
    write_json(directory / "result.json", result)
    state: dict = {}
    with (directory / "trace.jsonl").open("x", buffering=1) as trace:

        def event(kind: str, **fields) -> None:
            record = {"kind": kind, "elapsed": time.monotonic() - started, **fields}
            trace.write(json.dumps(record, sort_keys=True) + "\n")

        try:
            with RuntimeLock(), BridgeServer(
                host=wsl_bridge_host(), port=BRIDGE_PORT, timeout=config["bridge_timeout"]
            ) as bridge:
                deployment = prepare_runtime(*bridge.address, timeout=config["bridge_timeout"])
                write_json(directory / "deployment.json", deployment)
                with OwnedGame(directory / "game.log", timeout=config["run_timeout"]) as game:
                    event("launch", **game.info)
                    sequence = settles = 0
                    run_started = False
                    while True:
                        if time.monotonic() >= deadline:
                            result.update(status="truncated", reason="run_time_limit")
                            break
                        message = bridge.receive()
                        sequence += 1
                        event("observation", sequence=sequence, raw=message)
                        if "error" in message:
                            raise BridgeCommandError(message["error"])
                        if not message.get("ready_for_command"):
                            continue
                        state = message.get("game_state") or state
                        if not message.get("in_game"):
                            if run_started:
                                raise ProtocolError("Main menu reached without a run outcome")
                            command = f"START IRONCLAD 0 {config['seed']}"
                            run_started = True
                        elif outcome := decisions.run_outcome(message):
                            score = (state.get("screen_state") or {}).get("score")
                            result.update(status=outcome, score=score)
                            event("terminal", outcome=outcome, sequence=sequence)
                            break
                        elif result["actions"] >= config["max_actions"]:
                            result.update(status="truncated", reason="action_limit")
                            break
                        elif _unsettled(message) and "wait" in message["available_commands"]:
                            if settles >= 3:
                                raise ProtocolError("Enemy intents did not settle")
                            command, settles = "wait 60", settles + 1
                            result["settle_waits"] += 1
                        else:
                            settles = 0
                            decision = decisions.decision_from_message(
                                message, session_id=session_id, sequence=sequence
                            )
                            if len(decision.candidates) == 1:
                                choice, behavior = decision.candidates[0], {"type": "forced"}
                            else:
                                try:
                                    choice = policy.choose(decision)
                                finally:
                                    result["policy_calls"] += 1
                                if choice not in decision.candidates:
                                    raise IllegalActionError("Choice is not a current candidate")
                                behavior = policy.choice_metadata(decision.id)
                            event("decision", decision=decision.to_dict(), choice_id=choice.id,
                                  behavior=behavior)
                            result["decisions"] += 1
                            command = choice.command
                        event("action", sequence=sequence, command=command)
                        bridge.send(command)
                        result["actions"] += 1
        except BridgeError as exc:
            status = "truncated" if time.monotonic() >= deadline else "infrastructure_failure"
            result.update(status=status, error=str(exc), error_type=type(exc).__name__)
        except PolicyFailure as exc:
            event("policy_failure", failure=exc.failure)
            result.update(status="policy_failure", error=str(exc))
        except BudgetExhausted as exc:
            result.update(status="budget_exhausted", error=str(exc))
        except ProtocolError as exc:
            result.update(status="unsupported_or_invalid", error=str(exc),
                          error_type=type(exc).__name__)
        except Exception as exc:  # APIError and anything unexpected
            result.update(status="infrastructure_failure", error=str(exc),
                          error_type=type(exc).__name__)
        finally:
            result.update(_summary(state), elapsed_seconds=time.monotonic() - started)
            result["llm"] = dict(getattr(policy, "totals", {}))
            event("result", result=result)
            write_json(directory / "result.json", result)
    return result


def _committed_source() -> dict:
    return {
        "source_revision": committed_revision("attributable runs"),
        "source_files": source_fingerprints(),
    }


def play(output: Path, config: dict, *, policy_factory: Callable) -> dict:
    """Play each seed once in order; a fresh directory per job, never overwritten."""
    if not config["seeds"] or not all(seed.isalnum() for seed in config["seeds"]):
        raise ValueError("seeds must be nonempty alphanumeric strings")
    for key in ("max_actions", "run_timeout", "bridge_timeout"):
        if not math.isfinite(config[key]) or config[key] <= 0:
            raise ValueError(f"{key} must be positive")
    source = _committed_source()
    output.mkdir(parents=True, exist_ok=False)
    from spire.engine.doctor import collect_diagnostics

    write_json(output / "environment.json", collect_diagnostics())
    shutil.copy2(SYSTEM_PROMPT_PATH, output / "system_prompt.md")
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        **source,
        "command": [sys.executable, *sys.argv],
        "config": config,
        "engine": "original",
        "scope": "full_run",
        "observation_contract": decisions.OBSERVATION_CONTRACT,
        "system_prompt_sha256": sha256(SYSTEM_PROMPT_PATH),
        "status": "running",
        "runs": [],
    }
    write_json(output / "manifest.json", manifest)
    try:
        for index, seed in enumerate(config["seeds"]):
            if source_fingerprints() != manifest["source_files"]:
                raise RuntimeError("Implementation changed during the job; stopped before launch")
            result = play_run(output / f"run-{index:04d}", {**config, "seed": seed},
                              policy_factory())
            manifest["runs"].append(result)
            write_json(output / "manifest.json", manifest)
            print(json.dumps({k: result.get(k) for k in (
                "seed", "status", "act", "floor", "current_hp", "decisions", "llm", "error",
            )}, sort_keys=True), flush=True)
            if result["status"] not in SCORED:
                break
        complete = len(manifest["runs"]) == len(config["seeds"])
        manifest["status"] = "completed" if complete and all(
            r["status"] in SCORED for r in manifest["runs"]) else "stopped"
    finally:
        if manifest["status"] == "running":
            manifest["status"] = "interrupted"
        write_json(output / "manifest.json", manifest)
    return manifest
