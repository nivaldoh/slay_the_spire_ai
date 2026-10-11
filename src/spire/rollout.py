"""Recorded first-combat rollouts through the original Windows game."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from spire.bridge import BridgeError, BridgeServer
from spire.doctor import collect_profile
from spire.policies import RandomPolicy, StarterHeuristicPolicy
from spire.protocol import (
    BridgeCommandError,
    ProtocolError,
    combat_outcome,
    decision_from_message,
    validate_action,
)
from spire.runtime import GAME_DIR, OwnedGame, prepare_runtime


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def prefix_command(message: dict) -> str:
    """Logged Neow/max-HP-or-gold and leftmost-map prefix, outside the policy."""
    commands = message.get("available_commands", [])
    state = message.get("game_state", {})
    screen = state.get("screen_type")
    if screen == "EVENT" and "choose" in commands:
        event = state.get("screen_state", {})
        if event.get("event_id") != "Neow Event":
            raise ProtocolError(f"Unsupported prefix event: {event.get('event_id')}")
        enabled = [option for option in event.get("options", []) if not option.get("disabled")]
        # After an early previous run Neow offers max HP or Lament. Prefer max HP;
        # Lament would remove the combat learning problem by setting enemies to 1 HP.
        hp = [option for option in enabled if "max hp" in option.get("text", "").lower()]
        if hp:
            return f"CHOOSE {hp[0]['choice_index']}"
        gold = [
            option for option in enabled if option.get("label", "").lower() == "obtain 100 gold"
        ]
        if gold:
            return f"CHOOSE {gold[0]['choice_index']}"
        if len(enabled) == 1:
            return f"CHOOSE {enabled[0]['choice_index']}"
        raise ProtocolError("Neow has multiple choices without max HP or 100 gold; unsupported")
    if screen == "MAP" and "choose" in commands:
        return "CHOOSE 0"
    if "proceed" in commands:
        return "PROCEED"
    raise ProtocolError(f"Unsupported prefix screen {screen}: {commands}")


def _fingerprint(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def run_episode(directory: Path, config: dict, episode: int) -> dict:
    directory.mkdir(exist_ok=False)
    started = time.monotonic()
    deadline = started + config["episode_timeout"]
    session_id = uuid.uuid4().hex
    result = {
        "episode": episode,
        "session_id": session_id,
        "status": "interrupted",
        "seed": config["game_seed"],
        "policy": config["policy"],
        "policy_seed": config["policy_seed"] + episode,
        "actions": 0,
        "combat_actions": 0,
        "invalid_actions": 0,
        "inference_seconds": 0.0,
    }
    write_json(directory / "profile.json", collect_profile(GAME_DIR))
    write_json(directory / "result.json", result)
    policy = (
        RandomPolicy(result["policy_seed"])
        if config["policy"] == "random"
        else StarterHeuristicPolicy()
    )
    combat_floor = None
    combat_started = None
    pending = None
    sequence = 0
    with (directory / "trace.jsonl").open("x", buffering=1) as trace:

        def event(kind: str, **fields) -> None:
            trace.write(
                json.dumps(
                    {"kind": kind, "elapsed": time.monotonic() - started, **fields}, sort_keys=True
                )
                + "\n"
            )
            trace.flush()

        try:
            with BridgeServer(timeout=config["bridge_timeout"]) as bridge:
                deployment = prepare_runtime(*bridge.address, timeout=config["bridge_timeout"])
                write_json(directory / "deployment.json", deployment)
                with OwnedGame(directory / "game.log", timeout=config["episode_timeout"]) as game:
                    event("launch", **game.info)
                    while True:
                        if time.monotonic() >= deadline:
                            result.update(status="truncated", reason="episode_time_limit")
                            break
                        message = bridge.receive()
                        sequence += 1
                        event(
                            "observation",
                            sequence=sequence,
                            raw=message,
                            previous_action_id=pending,
                        )
                        if "error" in message:
                            result["invalid_actions"] += 1
                            event(
                                "execution",
                                action_id=pending,
                                status="rejected",
                                error=message["error"],
                            )
                            raise BridgeCommandError(message["error"])
                        if not message.get("ready_for_command"):
                            continue
                        if pending:
                            event(
                                "execution",
                                action_id=pending,
                                status="next_stable_state",
                                sequence=sequence,
                            )
                            pending = None
                        state = message.get("game_state", {})
                        if combat_floor is not None:
                            outcome = combat_outcome(message, combat_floor=combat_floor)
                            if outcome:
                                result.update(status=outcome, ending_hp=state.get("current_hp"))
                                event("terminal", outcome=outcome, sequence=sequence)
                                break
                        # Consume the final permitted action's response before checking the
                        # limit: it may be a killing blow or an engine-reported defeat.
                        if result["actions"] >= config["max_actions"]:
                            result.update(status="truncated", reason="action_limit")
                            break
                        if state.get("room_phase") == "COMBAT":
                            decision = decision_from_message(
                                message, session_id=session_id, sequence=sequence
                            )
                            if combat_floor is None:
                                combat_floor = state["floor"]
                                combat_started = time.monotonic()
                                public = decision.to_dict()["observation"]
                                write_json(directory / "combat_start.json", public)
                                result.update(
                                    floor=combat_floor,
                                    starting_hp=state.get("current_hp"),
                                    reset_seconds=combat_started - started,
                                    combat_start_sha256=_fingerprint(public),
                                )
                            inference_start = time.monotonic()
                            action = validate_action(decision, policy.choose(decision))
                            result["inference_seconds"] += time.monotonic() - inference_start
                            pending = action.id
                            command = action.command
                            event(
                                "decision", decision=decision.to_dict(), selected_action_id=pending
                            )
                            result["combat_actions"] += 1
                            result["turns"] = state.get("combat_state", {}).get("turn")
                        else:
                            if combat_floor is not None:
                                raise ProtocolError(
                                    "Left combat without a verified terminal outcome"
                                )
                            if not message.get("in_game") and "start" in message.get(
                                "available_commands", []
                            ):
                                command = f"START IRONCLAD 0 {config['game_seed']}"
                            else:
                                command = prefix_command(message)
                            pending = f"{session_id}:{sequence}:prefix"
                        event("action", action_id=pending, sequence=sequence, command=command)
                        bridge.send(command)
                        result["actions"] += 1
        except BridgeError as exc:
            if time.monotonic() >= deadline:
                result.update(status="truncated", reason="episode_time_limit", error=str(exc))
            else:
                result.update(
                    status="infrastructure_failure", error=str(exc), error_type=type(exc).__name__
                )
        except ProtocolError as exc:
            result.update(
                status="unsupported_or_invalid", error=str(exc), error_type=type(exc).__name__
            )
        except Exception as exc:
            result.update(
                status="infrastructure_failure", error=str(exc), error_type=type(exc).__name__
            )
        finally:
            result["elapsed_seconds"] = time.monotonic() - started
            if combat_started is not None:
                result["combat_seconds"] = time.monotonic() - combat_started
            event("result", result=result)
            write_json(directory / "result.json", result)
    return result


def rollout(output: Path, config: dict) -> dict:
    """Every new invocation gets a fresh directory; completed evidence is never overwritten."""
    if not config["game_seed"].isalnum():
        raise ValueError("game seed must be alphanumeric")
    if config["policy"] not in {"random", "heuristic"}:
        raise ValueError("unknown policy")
    for key in ("episodes", "max_actions", "episode_timeout", "bridge_timeout"):
        if not math.isfinite(config[key]) or config[key] <= 0:
            raise ValueError(f"{key} must be positive")
    source_paths = ["src", "scripts", "configs", "pyproject.toml", "uv.lock", ".python-version"]
    source_status = subprocess.check_output(
        ["git", "status", "--porcelain", "--", *source_paths], text=True
    )
    if source_status:
        raise ValueError(
            "Commit implementation changes before attributable rollouts: " + source_status
        )
    output.mkdir(parents=True, exist_ok=False)
    from spire.doctor import collect_diagnostics

    diagnostics = collect_diagnostics()
    write_json(output / "environment.json", diagnostics)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], text=True)
    patch = subprocess.check_output(["git", "diff", "HEAD"], text=True)
    (output / "source.patch").write_text(patch)
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_revision": revision,
        "source_status": dirty,
        "config": config,
        "engine": "original",
        "scope": "first_combat",
        "observation_version": "ironclad-starter-combat-v1",
        "prefix_version": "neow-maxhp-or-gold-leftmost-v1",
        "reset": "owned_jvm_restart_then_seeded_start",
        "status": "running",
        "episodes": [],
    }
    write_json(output / "manifest.json", manifest)
    try:
        for index in range(config["episodes"]):
            result = run_episode(output / f"episode-{index:04d}", config, index)
            manifest["episodes"].append(result)
            write_json(output / "manifest.json", manifest)
            print(json.dumps(result, sort_keys=True), flush=True)
            if result["status"] not in {"won", "lost"}:
                # Preserve a failed attempt and diagnose; never silently retry a failure.
                break
        manifest["status"] = (
            "completed"
            if len(manifest["episodes"]) == config["episodes"]
            and all(r["status"] in {"won", "lost"} for r in manifest["episodes"])
            else "stopped"
        )
    finally:
        if manifest["status"] == "running":
            manifest["status"] = "interrupted"
        write_json(output / "manifest.json", manifest)
    return manifest
