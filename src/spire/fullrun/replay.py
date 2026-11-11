"""Replay a recorded full run from its seeded START (docs/spire/state-restore.md, Plan step 2,
route A).

Sends the trace's commands in order, compares each settled observation with the recorded one
under the plan's same-state rule, and stops at the first difference or before the command
that ended the run, so no score reaches the profile's unlock progress. Afterwards it compares
the autosaves it copied with the recorded snapshots, timing fields aside. It writes its
output directory and, like every run, the deployment in C:/spire-agent, the mod's config and
the game's own saves and preferences; the autosave of the stopped run stays in saves/, where
Steam Auto-Cloud may sync it (the plan's Steam Cloud risk). Proposed for step 2: no check is
agreed and it has never run against the game.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from gameai.provenance import committed_revision, write_json
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
from spire.fullrun.play import SOURCES, SaveSnapshots, _save_path, decode_save
from spire.fullrun.stats import JOBS_ROOT
from spire.protocol import BridgeCommandError, ProtocolError

# Fields of an autosave that follow the clock rather than the run.
TIMING = ("play_time", "metric_playtime", "save_date")
# JUDGEMENT?: Protected preferences — Claude, 2026-10-29: the plan says to check before launching
# that every .backUp exists; these are the two files the 2026-10-23 logs show recovered from
# their .backUp (unlock progress, Ironclad statistics). Checking every file would refuse always
# (STSDaily, STSTips and others never have one); none would allow a launch with no recovery copy.
PROTECTED = ("STSUnlockProgress", "STSDataVagabond")


def settled(raw: dict) -> dict:
    """An observation as compared: no card UUIDs, no Library book text.

    rests on JUDGEMENT docs/spire/state-restore.md "same state" (assistant, 2026-10-23).
    """
    def strip(value):
        if isinstance(value, dict):
            return {k: strip(v) for k, v in value.items() if k != "uuid"}
        if isinstance(value, list):
            return [strip(v) for v in value]
        return value
    state = strip(raw)
    screen = (state.get("game_state") or {}).get("screen_state") or {}
    if screen.get("event_id") == "The Library":
        screen.pop("body_text", None)
    return state


def recorded(trace: Path) -> tuple[list[dict], list[str], list[dict]]:
    """A trace's settled observations, its commands and its save snapshots (each with the
    number of commands sent before it), in order. Observation k is the state after commands
    0..k-1; observation 0 is the main menu."""
    observations, commands, snapshots = [], [], []
    for line in trace.open():
        event = json.loads(line)
        if event["kind"] == "observation":
            raw = event["raw"]
            if raw.get("ready_for_command") and "error" not in raw:
                observations.append(raw)
        elif event["kind"] == "action":
            commands.append(event["command"])
        elif event["kind"] == "save_snapshot":
            snapshots.append({**event, "after_commands": len(commands)})
    return observations, commands, snapshots


def last_command(observations: list[dict], commands: list[str]) -> int:
    """How many commands to send: those before the one that reached GAME_OVER, else every
    command whose resulting state was recorded (a trace cut after a command has no state for
    its last one)."""
    for k, raw in enumerate(observations[1:]):
        if (raw.get("game_state") or {}).get("screen_type") == "GAME_OVER":
            return k
    return min(len(commands), len(observations) - 1)


def check_preferences(preferences: Path, profile: dict) -> None:
    if profile.get("slot") not in (0, 1, 2):
        raise RuntimeError(f"the profile's save slot is unreadable: {profile}")
    # Slot zero is unprefixed; the game prefixes slots 1 and 2 with their number.
    prefix = "" if profile["slot"] == 0 else f"{profile['slot']}_"
    for name in (prefix + name for name in PROTECTED):
        backup = preferences / f"{name}.backUp"
        if not backup.exists():
            raise RuntimeError(f"{name} has no .backUp; decide the profile question first")
        if backup.stat().st_size == 0 and (preferences / name).stat().st_size == 0:
            raise RuntimeError(f"{name} and its .backUp are both empty")


def save_differences(recorded_dir: Path, replayed_dir: Path, snapshots: list[dict]) -> list[dict]:
    """For each recorded snapshot, the fields its replayed counterpart differs in, timing
    fields aside, or that the replay made none."""
    rows = []
    for index, snapshot in enumerate(snapshots, 1):
        replayed = replayed_dir / f"{index:04d}.autosave"
        if not replayed.exists():
            rows.append({"snapshot": index, "missing": True})
            continue
        a = decode_save((recorded_dir / snapshot["file"]).read_bytes())
        b = decode_save(replayed.read_bytes())
        fields = sorted(k for k in set(a) | set(b) if k not in TIMING and a.get(k) != b.get(k))
        if fields:
            rows.append({"snapshot": index, "fields": fields})
    return rows


def _follow(bridge, observations, commands, limit, result, event, saves, deadline) -> None:
    sent = sequence = 0
    while time.monotonic() < deadline:
        message = bridge.receive()
        sequence += 1
        event("observation", sequence=sequence, raw=message)
        if "error" in message:
            raise BridgeCommandError(message["error"])
        if not message.get("ready_for_command"):
            continue
        if message.get("in_game"):
            saves.check(sequence)
        if settled(message) != settled(observations[sent]):
            result.update(status="differed", first_difference=sent)
            return
        if sent == limit:
            result.update(status="replayed")
            return
        event("action", sequence=sequence, command=commands[sent])
        bridge.send(commands[sent])
        sent += 1
        result["sent"] = sent
    result.update(status="truncated", reason="run_time_limit")


def replay(trace: Path, output: Path, config: dict) -> dict:
    """One replay of ``trace`` into the new directory ``output``. Config: run_timeout,
    bridge_timeout (seconds)."""
    observations, commands, snapshots = recorded(trace)
    limit = last_command(observations, commands)
    result = {"trace": str(trace), "source_revision": committed_revision("replays", SOURCES),
              "commands": len(commands), "stop_before": limit, "sent": 0,
              "status": "interrupted", "first_difference": None}
    if output.resolve().is_relative_to(JOBS_ROOT.resolve()):
        raise ValueError("a replay's output stays outside runs/fullrun/ (the results register)")
    profile = collect_profile(GAME_DIR)
    check_preferences(GAME_DIR / "preferences", profile)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(GAME_DIR / "preferences", output / "preferences-before")
    write_json(output / "profile-before.json", profile)
    started = time.monotonic()
    with (output / "trace.jsonl").open("x", buffering=1) as log:

        def event(kind: str, **fields) -> None:
            record = {"kind": kind, "elapsed": time.monotonic() - started, **fields}
            log.write(json.dumps(record, sort_keys=True) + "\n")

        saves = SaveSnapshots(_save_path(profile), output / "saves", event)
        try:
            with RuntimeLock(), BridgeServer(
                host=wsl_bridge_host(), port=BRIDGE_PORT, timeout=config["bridge_timeout"]
            ) as bridge:
                deployment = prepare_runtime(*bridge.address, timeout=config["bridge_timeout"])
                write_json(output / "deployment.json", deployment)
                with OwnedGame(output / "game.log", timeout=config["run_timeout"]) as game:
                    event("launch", **game.info)
                    _follow(bridge, observations, commands, limit, result, event, saves,
                            started + config["run_timeout"])
        except BridgeError as exc:
            result.update(status="infrastructure_failure", error=str(exc),
                          error_type=type(exc).__name__)
        except ProtocolError as exc:
            result.update(status="unsupported_or_invalid", error=str(exc),
                          error_type=type(exc).__name__)
        except Exception as exc:  # anything unexpected still leaves a readable result
            result.update(status="infrastructure_failure", error=str(exc),
                          error_type=type(exc).__name__)
        finally:
            reached = [s for s in snapshots if s["after_commands"] <= result["sent"]]
            result["save_differences"] = save_differences(trace.parent, output / "saves", reached)
            write_json(output / "profile-after.json", collect_profile(GAME_DIR))
            write_json(output / "result.json", result)
    return result
