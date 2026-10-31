"""Synthetic Spire traces shared by combat and language component tests.

Pattern: Hugging Face datasets tests/utils.py and our fullrun_support.py keep shared
builders outside collected tests. These invented records do not establish game behavior.
"""

import copy
import hashlib
import json

import pytest

from spire.combat.evidence import normalized_observation_fingerprint
from spire.protocol import decision_from_message


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n")



def read(path):
    return json.loads(path.read_text())



def events(directory):
    return [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]



def write_events(directory, values):
    (directory / "trace.jsonl").write_text("".join(json.dumps(v) + "\n" for v in values))



def set_result(run, **changes):
    """Change all claimed-result copies, so engine evidence must catch tampering."""
    directory = run / "episode-0000"
    result = read(directory / "result.json")
    result.update(changes)
    write(directory / "result.json", result)
    trace = events(directory)
    trace[-1]["result"] = result
    write_events(directory, trace)
    manifest = read(run / "manifest.json")
    manifest["episodes"][0] = result
    write(run / "manifest.json", manifest)



def combat_message():
    return {
        "in_game": True,
        "ready_for_command": True,
        "available_commands": ["play", "end"],
        "game_state": {
            "class": "IRONCLAD",
            "ascension_level": 0,
            "floor": 1,
            "act": 1,
            "seed": 999,
            "current_hp": 80,
            "max_hp": 80,
            "room_phase": "COMBAT",
            "room_type": "MonsterRoom",
            "screen_type": "NONE",
            "screen_name": "NONE",
            "is_screen_up": False,
            "combat_state": {
                "turn": 1,
                "player": {"current_hp": 80, "max_hp": 80, "block": 0, "energy": 3},
                "hand": [
                    {
                        "id": "Strike_R",
                        "uuid": "private-card-id",
                        "name": "Strike",
                        "cost": 1,
                        "has_target": True,
                        "is_playable": True,
                        "upgrades": 0,
                    }
                ],
                "monsters": [
                    {
                        "id": "Louse",
                        "name": "Louse",
                        "current_hp": 6,
                        "max_hp": 6,
                        "block": 0,
                        "intent": "ATTACK",
                        "move_adjusted_damage": 5,
                        "move_hits": 1,
                        "is_gone": False,
                        "half_dead": False,
                        "move_id": 2,
                    }
                ],
            },
        },
    }



def make_episode(run, index=0, ending_hp=80, outcome="won"):
    directory = run / f"episode-{index:04d}"
    directory.mkdir()
    session = f"session-{index}"
    raw = combat_message()
    decision = decision_from_message(raw, session_id=session, sequence=2)
    action = decision.candidates[0]
    prefix_id = f"{session}:1:prefix"
    public = decision.to_dict()["observation"]
    terminal = copy.deepcopy(raw)
    terminal["game_state"].update(
        current_hp=ending_hp, room_phase="COMPLETE", screen_type="COMBAT_REWARD"
    )
    terminal["game_state"].pop("combat_state")
    if outcome == "lost":
        terminal["game_state"].update(
            screen_type="GAME_OVER", screen_name="DEATH", screen_state={"victory": False}
        )
    result = {
        "episode": index,
        "session_id": session,
        "status": outcome,
        "seed": "ABC",
        "policy": "random",
        "policy_seed": index,
        "actions": 2,
        "combat_actions": 1,
        "invalid_actions": 0,
        "floor": 1,
        "starting_hp": 80,
        "ending_hp": ending_hp,
        "turns": 1,
        "reset_seconds": 2.2,
        "combat_seconds": 2.8,
        "elapsed_seconds": 5.0,
        "combat_start_sha256": normalized_observation_fingerprint(public),
    }
    trace = [
        {"kind": "launch", "elapsed": 0.1, "pid": 123},
        {
            "kind": "observation",
            "elapsed": 1.0,
            "sequence": 1,
            "previous_action_id": None,
            "raw": {"in_game": False, "ready_for_command": True, "available_commands": ["start"]},
        },
        {
            "kind": "action",
            "elapsed": 1.1,
            "sequence": 1,
            "action_id": prefix_id,
            "command": "START IRONCLAD 0 ABC",
        },
        {
            "kind": "observation",
            "elapsed": 2.0,
            "sequence": 2,
            "previous_action_id": prefix_id,
            "raw": raw,
        },
        {
            "kind": "execution",
            "elapsed": 2.1,
            "sequence": 2,
            "action_id": prefix_id,
            "status": "next_stable_state",
        },
        {
            "kind": "decision",
            "elapsed": 2.3,
            "decision": decision.to_dict(),
            "selected_action_id": action.id,
        },
        {
            "kind": "action",
            "elapsed": 2.4,
            "sequence": 2,
            "action_id": action.id,
            "command": action.command,
        },
        {
            "kind": "observation",
            "elapsed": 4.0,
            "sequence": 3,
            "previous_action_id": action.id,
            "raw": terminal,
        },
        {
            "kind": "execution",
            "elapsed": 4.1,
            "sequence": 3,
            "action_id": action.id,
            "status": "next_stable_state",
        },
        {"kind": "terminal", "elapsed": 4.2, "sequence": 3, "outcome": outcome},
        {"kind": "result", "elapsed": 5.0, "result": result},
    ]
    write(directory / "result.json", result)
    write(directory / "combat_start.json", public)
    write(directory / "deployment.json", {"fixture": True})
    write_events(directory, trace)
    return result



@pytest.fixture
def run(tmp_path):
    directory = tmp_path / "run"
    directory.mkdir()
    result = make_episode(directory)
    write(
        directory / "manifest.json",
        {
            "schema_version": 1,
            "status": "completed",
            "source_revision": "a" * 40,
            "engine": "original",
            "scope": "first_combat",
            "config": {"episodes": 1, "game_seed": "ABC", "policy": "random", "policy_seed": 0},
            "episodes": [result],
        },
    )
    write(directory / "environment.json", {"fixture": True})
    (directory / "source.patch").write_text("")
    return directory



def language_behavior(decision, selected_index=0):
    from spire.language.demonstrations import FORMAT_VERSION, render_prompt

    prompt = render_prompt(decision)
    completion = json.dumps({"a": selected_index}, separators=(",", ":"))
    return {
        "type": "language",
        "prompt_format": FORMAT_VERSION,
        "parser_version": "single-json-choice-v1",
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "chat_prompt_sha256": hashlib.sha256(("fake chat" + prompt).encode()).hexdigest(),
        "prompt_tokens": 100,
        "max_prompt_tokens": 2048,
        "completion_tokens": 6,
        "completion_token_ids": [1, 2, 3, 4, 5, 6],
        "completion": completion,
        "raw_completion": completion + "<eos>",
        "selected_index": selected_index,
        "inference_seconds": 0.1,
    }



def make_language_success(run):
    directory = run / "episode-0000"
    trace = events(directory)
    decision = decision_from_message(trace[3]["raw"], session_id="session-0", sequence=2)
    trace[5]["behavior"] = language_behavior(decision)
    write_events(directory, trace)
    manifest = read(run / "manifest.json")
    manifest["config"]["policy"] = "language"
    write(run / "manifest.json", manifest)
    set_result(run, policy="language")



def make_policy_failure(run, *, kind="invalid_completion", after_action=False, **changes):
    from spire.language.demonstrations import render_prompt

    directory = run / "episode-0000"
    trace = events(directory)
    if after_action:
        first = decision_from_message(trace[3]["raw"], session_id="session-0", sequence=2)
        trace[5]["behavior"] = language_behavior(first)
        trace[7]["raw"] = copy.deepcopy(trace[3]["raw"])
        trace[7]["raw"]["game_state"]["combat_state"]["turn"] = 2
    decision = decision_from_message(
        trace[7 if after_action else 3]["raw"],
        session_id="session-0",
        sequence=3 if after_action else 2,
    )
    invalid = kind == "invalid_completion"
    failure = {
        "kind": kind,
        "completion": "I would attack" if invalid else None,
        "raw_completion": "I would attack<eos>" if invalid else None,
        "completion_token_ids": [1, 2, 3, 4] if invalid else [],
        "prompt_sha256": hashlib.sha256(render_prompt(decision).encode()).hexdigest(),
        "prompt_tokens": 100 if invalid else 2049,
        "max_prompt_tokens": 2048,
        "completion_tokens": 4 if invalid else 0,
        "inference_seconds": 0.1,
        **changes,
    }
    result = read(directory / "result.json")
    result.update(
        status="policy_failure",
        policy="language",
        actions=2 if after_action else 1,
        combat_actions=int(after_action),
        turns=2 if after_action else 1,
        policy_failure=failure,
    )
    result.pop("ending_hp")
    trace = [
        *trace[: 9 if after_action else 5],
        {
            "kind": "policy_failure",
            "elapsed": 4.2 if after_action else 2.3,
            "decision": decision.to_dict(),
            "failure": failure,
        },
        {"kind": "result", "elapsed": 5.0, "result": result},
    ]
    write_events(directory, trace)
    write(directory / "result.json", result)
    manifest = read(run / "manifest.json")
    manifest["config"]["policy"] = "language"
    manifest["episodes"][0] = result
    write(run / "manifest.json", manifest)
    return failure

