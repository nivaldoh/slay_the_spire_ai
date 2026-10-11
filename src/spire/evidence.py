"""Offline consistency checks and metrics for recorded original-engine attempts.

This checks the evidence that exists; it does not attest that a recording was
produced by a particular executable. Only verified gameplay endings enter scores.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from statistics import mean
from typing import Any

from spire.protocol import ProtocolError, combat_outcome, decision_from_message, validate_action


class EvidenceError(ValueError):
    """Evidence is incomplete, contradictory, or unsafe to ingest."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_bad_constant)


def _bad_constant(value: str) -> None:
    raise EvidenceError(f"Nonfinite JSON number: {value}")


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def normalized_observation_fingerprint(observation: Mapping) -> str:
    """Hash a public observation; the protocol already canonicalizes unordered piles."""
    return hashlib.sha256(json.dumps(_plain(observation), sort_keys=True).encode()).hexdigest()


def _prefix_details(raw: dict, command: str) -> dict:
    """Check prefix command identity and retain the meaning of positional choices."""
    commands = raw.get("available_commands", [])
    state = raw.get("game_state", {})
    tokens = command.split()
    _require(bool(tokens), "Empty action command")
    verb = tokens[0].lower()
    details = {"command": command, "screen_type": state.get("screen_type")}
    if verb == "start":
        _require(not raw.get("in_game") and "start" in commands, "START outside main menu")
        _require(len(tokens) == 4 and tokens[1:3] == ["IRONCLAD", "0"], "Invalid START")
    elif verb == "choose":
        _require("choose" in commands and len(tokens) == 2, "CHOOSE unavailable or malformed")
        index = int(tokens[1])
        choices = state.get("choice_list", [])
        _require(0 <= index < len(choices), "Prefix choice index is outside choice_list")
        details["choice"] = choices[index]
        screen = state.get("screen_state", {})
        details["event_id"] = screen.get("event_id")
        for option in screen.get("options", []):
            if option.get("choice_index") == index and not option.get("disabled"):
                details["choice_text"] = option.get("text")
    elif verb in ("proceed", "confirm"):
        _require(len(tokens) == 1, "PROCEED/CONFIRM has unexpected arguments")
        _require(bool({"proceed", "confirm"} & set(commands)), "PROCEED/CONFIRM unavailable")
    else:
        raise EvidenceError(f"Unsupported prefix command: {verb}")
    return details


def _successor(
    raw: dict, session: str, sequence: int, floor: int
) -> tuple[dict | None, str | None]:
    outcome = combat_outcome(raw, combat_floor=floor)
    if outcome:
        state = raw["game_state"]
        return {
            "terminal": outcome,
            "floor": state.get("floor"),
            "current_hp": state.get("current_hp"),
            "max_hp": state.get("max_hp"),
        }, outcome
    try:
        next_decision = decision_from_message(raw, session_id=session, sequence=sequence)
    except ProtocolError:
        return None, None
    return next_decision.to_dict()["observation"], None


def _language_behavior(decision, selected, behavior) -> None:
    """Check public choice linkage; the evaluator also replays tokenizer decoding."""
    from spire.demonstrations import FORMAT_VERSION, parse_completion, render_prompt

    _require(isinstance(behavior, dict), "Missing language behavior metadata")
    for name, expected in (
        ("type", "language"),
        ("prompt_format", FORMAT_VERSION),
        ("parser_version", "single-json-choice-v1"),
    ):
        _require(behavior.get(name) == expected, f"Unsupported language behavior {name}")
    _require(
        behavior.get("prompt_sha256")
        == hashlib.sha256(render_prompt(decision).encode("utf-8")).hexdigest(),
        "Language prompt differs from public decision",
    )
    chat_hash = behavior.get("chat_prompt_sha256")
    _require(
        isinstance(chat_hash, str) and re.fullmatch(r"[a-f0-9]{64}", chat_hash) is not None,
        "Invalid language chat prompt hash",
    )
    _require(
        type(behavior.get("max_prompt_tokens")) is int and behavior["max_prompt_tokens"] == 2048,
        "Unsupported language context limit",
    )
    _require(
        type(behavior.get("prompt_tokens")) is int and 1 <= behavior["prompt_tokens"] <= 2048,
        "Invalid language prompt token count",
    )
    count = behavior.get("completion_tokens")
    _require(type(count) is int and 1 <= count <= 12, "Invalid language completion token count")
    tokens = behavior.get("completion_token_ids")
    _require(
        isinstance(tokens, list)
        and len(tokens) == count
        and all(type(token) is int and token >= 0 for token in tokens),
        "Invalid language completion token IDs",
    )
    _require(isinstance(behavior.get("raw_completion"), str), "Missing raw language completion")
    _require(isinstance(behavior.get("completion"), str), "Missing parsed language completion")
    _require(
        parse_completion(decision, behavior["completion"]) == selected,
        "Language completion selects a different action",
    )
    _require(
        type(behavior.get("selected_index")) is int
        and behavior["selected_index"] == decision.candidates.index(selected),
        "Language selected index differs from recorded action",
    )
    inference = behavior.get("inference_seconds")
    _require(
        type(inference) in (int, float) and math.isfinite(inference) and inference >= 0,
        "Invalid language inference duration",
    )


def _inspect_episode(directory: Path, config: dict | None) -> dict:
    result = _read_json(directory / "result.json")
    session = result["session_id"]
    _require(isinstance(session, str) and bool(session), "Invalid session ID")
    status = result["status"]
    _require(
        status
        in {
            "won",
            "lost",
            "infrastructure_failure",
            "unsupported_or_invalid",
            "truncated",
            "interrupted",
            "policy_failure",
        },
        f"Unknown result status: {status}",
    )
    if config is not None:
        for field, expected in (
            ("seed", config["game_seed"]),
            ("policy", config["policy"]),
            (
                "policy_seed",
                None
                if result.get("policy_rng") == "externally_checkpointed"
                else config["policy_seed"] + result["episode"],
            ),
        ):
            _require(result.get(field) == expected, f"Result {field} disagrees with configuration")
    text = (directory / "trace.jsonl").read_text(encoding="utf-8")
    _require(bool(text) and text.endswith("\n"), "Trace is empty or has an incomplete final line")
    events = [json.loads(line, parse_constant=_bad_constant) for line in text.splitlines()]
    latest = None
    sequence = 0
    elapsed = -1.0
    pending = None
    selected = None
    selected_decision = None
    needs_execution = False
    used_sequences: set[int] = set()
    action_ids: set[str] = set()
    executed_sequences: set[int] = set()
    transitions = []
    prefix = []
    first_decision = None
    first_combat_observation_time = None
    first_decision_time = None
    combat_floor = None
    terminal = None
    final_seen = False
    launch_seen = False
    action_count = combat_count = rejected_count = 0
    settle_count = 0
    policy_failure = None
    turns = None
    terminal_hp = None

    for offset, event in enumerate(events):
        _require(not final_seen, "Events follow the final result")
        timestamp = event.get("elapsed")
        _require(type(timestamp) in (int, float) and math.isfinite(timestamp), "Invalid timestamp")
        _require(timestamp >= elapsed and timestamp >= 0, "Trace timestamps run backwards")
        elapsed = timestamp
        kind = event["kind"]
        _require(terminal is None or kind == "result", "Events follow the terminal outcome")
        _require(policy_failure is None or kind == "result", "Events follow a policy failure")
        if kind == "launch":
            _require(offset == 0 and not launch_seen, "Launch must appear once at trace start")
            launch_seen = True
        elif kind == "observation":
            _require(launch_seen, "Observation precedes launch")
            _require(not needs_execution, "Stable successor is missing its execution linkage")
            _require(selected is None, "Selected decision has no corresponding action")
            _require(
                event.get("sequence") == sequence + 1, "Observation sequence is not contiguous"
            )
            sequence += 1
            _require(
                event.get("previous_action_id")
                == (pending["action"]["action_id"] if pending else None),
                "Observation does not reference the outstanding action",
            )
            latest = event
            raw = event["raw"]
            _require(isinstance(raw, dict), "Observation raw state is not an object")
            needs_execution = bool(pending) and (
                "error" in raw or raw.get("ready_for_command") is True
            )
        elif kind == "decision":
            _require(latest is not None and pending is None, "Decision before an available state")
            _require(not needs_execution and selected is None, "Overlapping decisions")
            expected = decision_from_message(latest["raw"], session_id=session, sequence=sequence)
            _require(event.get("decision") == expected.to_dict(), "Decision differs from raw state")
            selected = validate_action(expected, event.get("selected_action_id"))
            if result.get("policy") == "language":
                _language_behavior(expected, selected, event.get("behavior"))
            elif result.get("policy") == "language_sample":
                from spire.language_sampling import check_sampled_behavior

                try:
                    check_sampled_behavior(expected, selected, event.get("behavior"))
                except ValueError as error:
                    raise EvidenceError(str(error)) from error
            selected_decision = expected.to_dict()
            if first_decision is None:
                first_decision = selected_decision
                combat_floor = latest["raw"]["game_state"]["floor"]
                first_combat_observation_time = latest["elapsed"]
                first_decision_time = timestamp
            turns = expected.observation["combat_state"].get("turn")
        elif kind == "action":
            _require(latest is not None and pending is None, "More than one outstanding command")
            _require(not needs_execution, "Action precedes successor acknowledgment")
            raw = latest["raw"]
            _require(
                raw.get("ready_for_command") is True and "error" not in raw,
                "Action selected from an unstable or error observation",
            )
            _require(event.get("sequence") == sequence, "Action uses a stale observation sequence")
            _require(sequence not in used_sequences, "Observation reused for another command")
            used_sequences.add(sequence)
            action_id = event["action_id"]
            _require(action_id not in action_ids, "Action ID reused")
            action_ids.add(action_id)
            if selected is not None:
                _require(event.get("role") != "settle", "Policy action mislabeled as settling")
                _require(action_id == selected.id, "Action differs from selected candidate")
                _require(event.get("command") == selected.command, "Selected command was changed")
                combat_count += 1
            else:
                _require(combat_floor is None, "Combat action lacks a recorded decision")
                if event.get("role") == "settle":
                    _require(
                        action_id == f"{session}:{sequence}:settle", "Settling action ID is stale"
                    )
                    _require(event.get("command") == "WAIT 60", "Unknown settling command")
                    _require("wait" in raw.get("available_commands", []), "WAIT unavailable")
                    state = raw.get("game_state", {})
                    _require(state.get("room_phase") == "COMBAT", "Settling outside initial combat")
                    _require(
                        any(
                            m.get("intent") == "DEBUG" and m.get("current_hp", 0) > 0
                            for m in state.get("combat_state", {}).get("monsters", [])
                        ),
                        "Settling without a live DEBUG intent",
                    )
                    settle_count += 1
                    _require(settle_count <= 3, "Exceeded settling attempt limit")
                    details = {"command": "WAIT 60", "role": "settle", "screen_type": "NONE"}
                else:
                    _require(
                        action_id == f"{session}:{sequence}:prefix", "Prefix action ID is stale"
                    )
                    details = _prefix_details(raw, event["command"])
                if details["command"].startswith("START "):
                    _require(
                        details["command"] == f"START IRONCLAD 0 {result['seed']}",
                        "START command differs from declared seed",
                    )
                prefix.append(details)
            pending = {"action": event, "decision": selected_decision}
            selected = selected_decision = None
            action_count += 1
        elif kind == "execution":
            _require(latest is not None, "Execution has no observation")
            _require(sequence not in executed_sequences, "Duplicate execution linkage")
            executed_sequences.add(sequence)
            raw = latest["raw"]
            _require(
                event.get("action_id") == (pending["action"]["action_id"] if pending else None),
                "Execution refers to a different action",
            )
            if event.get("status") == "rejected":
                _require(
                    "error" in raw and event.get("error") == raw["error"],
                    "Rejection lacks matching engine error",
                )
                rejected_count += 1
            else:
                _require(event.get("status") == "next_stable_state", "Unknown execution status")
                _require(pending is not None and needs_execution, "Duplicate or unlinked execution")
                _require(event.get("sequence") == sequence, "Execution successor sequence mismatch")
                _require(
                    raw.get("ready_for_command") is True and "error" not in raw,
                    "Execution successor is not stable",
                )
                if pending["decision"] is not None:
                    after, outcome = _successor(raw, session, sequence, combat_floor)
                    before = pending["decision"]["observation"]
                    action = pending["action"]
                    transitions.append(
                        {
                            "transition_id": f"{session}/{action['action_id']}",
                            "episode": result["episode"],
                            "action_id": action["action_id"],
                            "sequence": action["sequence"],
                            "next_sequence": sequence,
                            "command": action["command"],
                            "action": next(
                                candidate
                                for candidate in pending["decision"]["candidates"]
                                if candidate["id"] == action["action_id"]
                            ),
                            "candidates": pending["decision"]["candidates"],
                            "observation": before,
                            "next_observation": after,
                            "terminal": outcome is not None,
                            "outcome": outcome,
                            "ingestible": after is not None,
                        }
                    )
            pending = None
            needs_execution = False
        elif kind == "terminal":
            _require(
                latest is not None and pending is None and selected is None,
                "Terminal precedes completed action linkage",
            )
            _require(
                terminal is None and combat_floor is not None, "Terminal without a unique combat"
            )
            _require(event.get("sequence") == sequence, "Terminal observation sequence mismatch")
            terminal = combat_outcome(latest["raw"], combat_floor=combat_floor)
            _require(
                terminal is not None and event.get("outcome") == terminal,
                "Terminal outcome is not supported by engine state",
            )
            terminal_hp = latest["raw"]["game_state"].get("current_hp")
        elif kind == "policy_failure":
            from spire.demonstrations import parse_completion, render_prompt

            _require(
                latest is not None and pending is None and selected is None and not needs_execution,
                "Policy failure outside an available decision",
            )
            _require(result.get("policy") == "language", "Policy failure requires language policy")
            expected = decision_from_message(latest["raw"], session_id=session, sequence=sequence)
            _require(
                event.get("decision") == expected.to_dict(),
                "Failed decision differs from raw state",
            )
            failure = event.get("failure")
            _require(isinstance(failure, dict), "Missing policy failure metadata")
            _require(
                failure.get("prompt_sha256")
                == hashlib.sha256(render_prompt(expected).encode("utf-8")).hexdigest(),
                "Failed prompt differs from public decision",
            )
            for name in ("prompt_tokens", "max_prompt_tokens", "completion_tokens"):
                _require(
                    type(failure.get(name)) is int and failure[name] >= 0,
                    f"Invalid policy failure {name}",
                )
            _require(failure["max_prompt_tokens"] == 2048, "Unsupported language context limit")
            inference = failure.get("inference_seconds")
            _require(
                type(inference) in (int, float) and math.isfinite(inference) and inference >= 0,
                "Invalid policy inference duration",
            )
            if failure.get("kind") == "context_limit":
                _require(
                    failure["prompt_tokens"] > failure["max_prompt_tokens"]
                    and failure.get("completion") is None
                    and failure["completion_tokens"] == 0,
                    "Context failure does not exceed the declared limit",
                )
            elif failure.get("kind") == "invalid_completion":
                _require(isinstance(failure.get("completion"), str), "Missing failed completion")
                _require(
                    failure["prompt_tokens"] <= failure["max_prompt_tokens"]
                    and failure["completion_tokens"] <= 12,
                    "Failed completion exceeds the declared inference budget",
                )
                try:
                    parse_completion(expected, failure["completion"])
                except ProtocolError:
                    pass
                else:
                    raise EvidenceError("A legal completion was labelled a policy failure")
            else:
                raise EvidenceError("Unknown policy failure kind")
            policy_failure = failure
            if first_decision is None:
                first_decision = expected.to_dict()
                combat_floor = latest["raw"]["game_state"]["floor"]
                first_combat_observation_time = latest["elapsed"]
                first_decision_time = timestamp
            turns = expected.observation["combat_state"].get("turn")
        elif kind == "result":
            _require(selected is None, "Selected decision has no corresponding action")
            _require(not needs_execution, "Final result omits an execution linkage")
            _require(event.get("result") == result, "Result file differs from trace result")
            final_seen = True
        else:
            raise EvidenceError(f"Unknown trace event: {kind}")

    _require(final_seen, "Trace has no final result; episode was interrupted or truncated on disk")
    _require(
        (status == "policy_failure") == (policy_failure is not None),
        "Policy failure status/event mismatch",
    )
    if policy_failure is not None:
        _require(
            result.get("policy_failure") == policy_failure,
            "Policy failure result differs from event",
        )
    else:
        _require("policy_failure" not in result, "Policy failure metadata lacks its event")
    if combat_floor is not None and latest is not None and "error" not in latest["raw"]:
        _require(
            combat_outcome(latest["raw"], combat_floor=combat_floor) == terminal,
            "Observed engine terminal is missing its terminal event",
        )
    if status in ("won", "lost"):
        _require(terminal == status and pending is None, "Gameplay result lacks verified terminal")
        _require(result.get("ending_hp") == terminal_hp, "Ending HP disagrees with terminal state")
        _require(
            (directory / "deployment.json").is_file(), "Gameplay result lacks deployment record"
        )
    else:
        _require(terminal is None, "Non-gameplay result contains a gameplay terminal")
    expected_actions = {action_count}
    if status == "infrastructure_failure" and pending is not None:
        # The runner writes its attempted action before bridge.send, then only
        # increments its sent counter if send succeeds.
        expected_actions.add(action_count - 1)
    _require(result.get("actions") in expected_actions, "Result action count differs from trace")
    _require(result.get("combat_actions") == combat_count, "Result combat action count mismatch")
    _require(
        result.get("invalid_actions") == rejected_count, "Result rejected-action count mismatch"
    )
    _require(type(result.get("elapsed_seconds")) in (int, float), "Missing elapsed_seconds")
    _require(abs(result["elapsed_seconds"] - elapsed) < 0.1, "Elapsed time disagrees with trace")
    first_public = first_decision["observation"] if first_decision else None
    reset_seconds = combat_seconds = starting_hp = None
    if first_public is not None:
        _require(
            prefix and prefix[0]["command"] == f"START IRONCLAD 0 {result['seed']}",
            "Combat has no recorded seeded START prefix",
        )
        _require(
            _read_json(directory / "combat_start.json") == first_public,
            "Combat start file differs from first decision",
        )
        fingerprint = normalized_observation_fingerprint(first_public)
        _require(result.get("combat_start_sha256") == fingerprint, "Combat start hash mismatch")
        _require(result.get("floor") == combat_floor, "Combat floor mismatch")
        starting_hp = first_public.get("current_hp")
        _require(result.get("starting_hp") == starting_hp, "Starting HP mismatch")
        _require(result.get("turns") == turns, "Turn count differs from last combat decision")
        reset_seconds = result.get("reset_seconds")
        combat_seconds = result.get("combat_seconds")
        _require(type(reset_seconds) in (int, float), "Missing reset time")
        _require(
            first_combat_observation_time <= reset_seconds <= first_decision_time,
            "Reset time falls outside first-combat observation/decision interval",
        )
        _require(type(combat_seconds) in (int, float), "Missing combat time")
        _require(
            abs(combat_seconds - (elapsed - reset_seconds)) < 0.1,
            "Combat time disagrees with trace",
        )
    else:
        fingerprint = None
        _require(status not in ("won", "lost"), "Gameplay result never entered combat")
    category = status
    if status == "unsupported_or_invalid":
        category = "invalid_action" if rejected_count else "unsupported"
    return {
        "valid": True,
        "issues": [],
        "directory": str(directory.resolve()),
        "episode": result["episode"],
        "session_id": session,
        "status": category,
        "claimed_status": status,
        "result": result,
        "actions": action_count,
        "combat_actions": combat_count,
        "rejected_actions": rejected_count,
        "starting_hp": starting_hp,
        "ending_hp": terminal_hp,
        "net_hp_lost": starting_hp - terminal_hp if terminal_hp is not None else None,
        "turns": turns,
        "reset_seconds": reset_seconds,
        "combat_seconds": combat_seconds,
        "elapsed_seconds": elapsed,
        "combat_start_sha256": fingerprint,
        "initial_intents_settled": (
            not any(
                m.get("intent") == "DEBUG" and m.get("current_hp", 0) > 0
                for m in first_public["combat_state"]["monsters"]
            )
            if first_public
            else None
        ),
        "prefix": prefix,
        "transitions": transitions,
        "evidence": {
            name: str((directory / name).resolve())
            for name in (
                "trace.jsonl",
                "result.json",
                "combat_start.json",
                "deployment.json",
                "game.log",
            )
            if (directory / name).exists()
        },
    }


def audit_episode(directory: Path, config: dict | None = None) -> dict:
    """Audit one complete attempt; inconsistent evidence never becomes a gameplay loss."""
    directory = Path(directory)
    try:
        return _inspect_episode(directory, config)
    except (EvidenceError, ProtocolError, OSError, KeyError, TypeError, ValueError) as exc:
        try:
            result = _read_json(directory / "result.json")
        except (OSError, ValueError):
            result = {}
        return {
            "valid": False,
            "issues": [str(exc)],
            "directory": str(directory.resolve()),
            "episode": result.get("episode"),
            "claimed_status": result.get("status"),
            "status": "interrupted"
            if result.get("status") == "interrupted"
            else "invalid_evidence",
            "result": result,
            "transitions": [],
        }


def compare_resets(episodes: list[dict]) -> dict:
    """Compare initial public states and every transition in shared action prefixes."""
    eligible = [e for e in episodes if e["valid"] and e.get("combat_start_sha256")]
    comparisons = []
    for index, left in enumerate(eligible):
        for right in eligible[index + 1 :]:
            shared = 0
            differences = []
            for step, (a, b) in enumerate(zip(left["transitions"], right["transitions"])):
                if a["command"] != b["command"]:
                    break
                shared += 1
                for state in ("observation", "next_observation"):
                    if a[state] != b[state]:
                        differences.append({"step": step, "state": state})
            comparisons.append(
                {
                    "episodes": [left["episode"], right["episode"]],
                    "initial_state_equal": left["combat_start_sha256"]
                    == right["combat_start_sha256"],
                    "prefix_equal": left["prefix"] == right["prefix"],
                    "shared_combat_actions": shared,
                    "shared_action_states_equal": not differences,
                    "differences": differences,
                }
            )
    return {
        "eligible_episodes": len(eligible),
        "initial_state_hashes": sorted({e["combat_start_sha256"] for e in eligible}),
        "all_initial_states_equal": (
            len({e["combat_start_sha256"] for e in eligible}) == 1 if len(eligible) >= 2 else None
        ),
        "comparisons": comparisons,
        "scope": "Public state equality; does not establish hidden-state equivalence",
    }


def _metrics(episodes: list[dict]) -> dict:
    valid = [episode for episode in episodes if episode["valid"]]
    scored = [episode for episode in valid if episode["status"] in ("won", "lost")]
    counts = Counter(episode["status"] for episode in episodes)
    policy_attempts = len(scored) + counts["policy_failure"]
    stats = {
        "attempts": len(episodes),
        "valid_evidence_episodes": len(valid),
        "valid_gameplay_episodes": len(scored),
        "wins": counts["won"],
        "losses": counts["lost"],
        "infrastructure_failures": counts["infrastructure_failure"],
        "policy_failures": counts["policy_failure"],
        "policy_attempts": policy_attempts,
        "policy_attempt_win_rate": counts["won"] / policy_attempts if policy_attempts else None,
        "unsupported": counts["unsupported"],
        "invalid_actions": counts["invalid_action"],
        "truncated": counts["truncated"],
        "interrupted": counts["interrupted"],
        "invalid_evidence": sum(not episode["valid"] for episode in episodes),
        "win_rate": counts["won"] / len(scored) if scored else None,
        "validated_transitions": sum(
            transition["ingestible"] for episode in valid for transition in episode["transitions"]
        ),
    }
    for field in ("starting_hp", "ending_hp", "net_hp_lost", "turns"):
        values = [episode[field] for episode in scored if episode[field] is not None]
        stats[f"mean_{field}"] = mean(values) if values else None
    for field in ("reset_seconds", "combat_seconds", "elapsed_seconds"):
        values = [episode[field] for episode in valid if episode[field] is not None]
        stats[f"mean_{field}"] = mean(values) if values else None
    stats["hp_scope"] = "Combat-start HP minus engine-terminal HP, including postcombat healing"
    return stats


def audit_run(directory: Path) -> dict:
    """Derive scores from episode evidence and verify exact manifest/result linkage."""
    directory = Path(directory)
    issues = []
    episodes = []
    manifest = {}
    try:
        manifest = _read_json(directory / "manifest.json")
        _require(manifest.get("schema_version") == 1, "Unsupported manifest schema")
        _require(
            manifest.get("status") in ("completed", "stopped", "interrupted"),
            "Run is not closed or has an unknown status",
        )
        _require(
            manifest.get("engine") == "original" and manifest.get("scope") == "first_combat",
            "Run does not declare the supported original-engine first-combat scope",
        )
        config = manifest["config"]
        linked = manifest["episodes"]
        _require(isinstance(linked, list), "Manifest episodes must be a list")
        expected = {}
        for result in linked:
            index = result["episode"]
            _require(
                type(index) is int and index >= 0 and index not in expected,
                "Manifest has an invalid or duplicate episode index",
            )
            expected[index] = result
        _require(list(expected) == list(range(len(expected))), "Manifest episode order has gaps")
        _require(len(expected) <= config["episodes"], "More attempts than configured")
        paths = sorted(directory.glob("episode-*"))
        seen = set()
        for path in paths:
            episode = audit_episode(path, config)
            episodes.append(episode)
            index = episode["episode"]
            if index in seen:
                issues.append(f"Duplicate episode index {index}")
            seen.add(index)
            if type(index) is not int or path.name != f"episode-{index:04d}":
                issues.append(f"Episode directory name disagrees with result index: {path.name}")
            if index not in expected:
                issues.append(f"Episode {index} is absent from manifest")
            elif episode["result"] != expected[index]:
                issues.append(f"Manifest result differs from episode {index} result")
        for index in expected.keys() - seen:
            issues.append(f"Manifest episode {index} is missing on disk")
        if manifest.get("status") == "completed":
            _require(len(episodes) == config["episodes"], "Completed manifest has missing attempts")
            endings = {"won", "lost"}
            if config.get("policy") == "language":
                endings.add("policy_failure")
            _require(
                all(e["valid"] and e["status"] in endings for e in episodes),
                "Completed manifest contains an unverified ending",
            )
        sessions = [e["session_id"] for e in episodes if e["valid"]]
        _require(len(set(sessions)) == len(sessions), "Episode session ID reused")
        ids = [t["transition_id"] for e in episodes for t in e["transitions"]]
        _require(len(ids) == len(set(ids)), "Duplicate transitions in run")
        if manifest.get("prefix_version") == "neow-maxhp-or-gold-leftmost-settled-v2":
            _require(
                all(e.get("initial_intents_settled") is not False for e in episodes),
                "Settled-v2 contract contains an initial DEBUG policy decision",
            )
        _require(
            isinstance(manifest.get("source_revision"), str)
            and len(manifest["source_revision"]) == 40,
            "Missing source revision",
        )
        for name in ("environment.json", "source.patch"):
            _require((directory / name).is_file(), f"Missing run provenance: {name}")
    except (EvidenceError, OSError, KeyError, TypeError, ValueError) as exc:
        issues.append(str(exc))
    for episode in episodes:
        issues.extend(f"Episode {episode['episode']}: {issue}" for issue in episode["issues"])
    return {
        "valid": not issues,
        "issues": issues,
        "directory": str(directory.resolve()),
        "verification_scope": "Recorded protocol, terminal, and manifest consistency",
        "manifest": manifest,
        "episodes": episodes,
        "metrics": _metrics(episodes),
        "reset_comparison": compare_resets(episodes),
        "evidence": {
            name: str((directory / name).resolve())
            for name in (
                "manifest.json",
                "environment.json",
                "source.patch",
            )
            if (directory / name).exists()
        },
    }


def summarize_run(directory: Path) -> dict:
    """Return a compact CLI/report result without copying full transition observations."""
    audit = audit_run(directory)
    summary = {
        key: audit[key]
        for key in (
            "valid",
            "issues",
            "directory",
            "verification_scope",
            "metrics",
            "reset_comparison",
            "evidence",
        )
    }
    summary["provenance"] = {
        key: audit["manifest"].get(key)
        for key in (
            "source_revision",
            "source_status",
            "config",
            "engine",
            "scope",
            "observation_version",
            "prefix_version",
            "reset",
            "status",
        )
    }
    summary["episodes"] = [
        {
            key: episode.get(key)
            for key in (
                "episode",
                "valid",
                "status",
                "issues",
                "starting_hp",
                "ending_hp",
                "turns",
                "combat_start_sha256",
                "evidence",
            )
        }
        for episode in audit["episodes"]
    ]
    return summary


def load_transitions(directories: Path | Iterable[Path]) -> list[dict]:
    """Load each acknowledged supported transition once, rejecting invalid runs.

    Valid interrupted or policy-failed attempts can retain acknowledged prefixes.
    This does not certify a complete training episode: PPO and demonstration
    callers must require an engine-confirmed complete outcome before ingestion.
    """
    if isinstance(directories, (str, Path)):
        directories = [Path(directories)]
    transitions = []
    seen = set()
    for directory in directories:
        audit = audit_run(Path(directory))
        if not audit["valid"]:
            raise EvidenceError(f"Run failed audit: {directory}: {audit['issues']}")
        for episode in audit["episodes"]:
            for transition in episode["transitions"]:
                if not transition["ingestible"]:
                    continue
                identity = transition["transition_id"]
                _require(identity not in seen, f"Duplicate transition ingestion: {identity}")
                seen.add(identity)
                transitions.append(transition)
    return transitions
