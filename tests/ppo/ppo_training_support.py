"""Shared synthetic fixtures; pattern: huggingface/datasets tests/utils.py."""

import copy
import json
from pathlib import Path

import pytest

from spire.combat.evidence import normalized_observation_fingerprint  # noqa: E402
from spire.ppo import training  # noqa: E402
from spire.protocol import decision_from_message  # noqa: E402


def write(path, value):
    path.write_text(json.dumps(value) + "\n")


def read(path):
    return json.loads(path.read_text())


def raw_combat():
    return {
        "in_game": True,
        "ready_for_command": True,
        "available_commands": ["play", "end"],
        "game_state": {
            "class": "IRONCLAD",
            "ascension_level": 0,
            "floor": 1,
            "act": 1,
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
                        "name": "Strike",
                        "has_target": True,
                        "is_playable": True,
                        "cost": 1,
                        "upgrades": 0,
                    }
                ],
                "monsters": [
                    {
                        "id": "Louse",
                        "name": "Louse",
                        "current_hp": 6,
                        "max_hp": 6,
                        "is_gone": False,
                        "half_dead": False,
                        "block": 0,
                        "intent": "ATTACK",
                        "move_adjusted_damage": 6,
                        "move_hits": 1,
                    }
                ],
            },
        },
    }


def synthetic_collector(directory, config, episode, *, policy):
    """One audited stochastic decision, then a synthetic terminal outcome."""
    directory.mkdir()
    index = int(directory.parent.name.rsplit("-", 1)[1])
    session = f"synthetic-{index}"
    raw = raw_combat()
    decision = decision_from_message(raw, session_id=session, sequence=2)
    action = policy.choose(decision)
    public = decision.to_dict()["observation"]
    outcome = "won" if index % 2 == 0 else "lost"
    ending_hp = 75 if outcome == "won" else 0
    after = copy.deepcopy(raw)
    after["game_state"].update(
        room_phase="COMPLETE", screen_type="COMBAT_REWARD", current_hp=ending_hp
    )
    after["game_state"].pop("combat_state")
    if outcome == "lost":
        after["game_state"].update(
            screen_type="GAME_OVER", screen_name="DEATH", screen_state={"victory": False}
        )
    result = {
        "episode": episode,
        "session_id": session,
        "policy": config["policy"],
        "policy_rng": "externally_checkpointed",
        "policy_seed": None,
        "seed": config["game_seed"],
        "status": outcome,
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
    prefix = f"{session}:1:prefix"
    trace = [
        {"kind": "launch", "elapsed": 0.1, "pid": 1},
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
            "action_id": prefix,
            "command": f"START IRONCLAD 0 {config['game_seed']}",
        },
        {
            "kind": "observation",
            "elapsed": 2.0,
            "sequence": 2,
            "previous_action_id": prefix,
            "raw": raw,
        },
        {
            "kind": "execution",
            "elapsed": 2.1,
            "sequence": 2,
            "action_id": prefix,
            "status": "next_stable_state",
        },
        {
            "kind": "decision",
            "elapsed": 2.3,
            "decision": decision.to_dict(),
            "selected_action_id": action.id,
            "behavior": policy.choice_metadata(decision.id),
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
            "raw": after,
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
    (directory / "trace.jsonl").write_text("".join(json.dumps(event) + "\n" for event in trace))
    write(directory / "result.json", result)
    write(directory / "combat_start.json", public)
    write(directory / "deployment.json", {"fixture": True})
    return result


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(training, "_TRAINING_LOCK_PATH", tmp_path / "training.lock")
    suite_path = tmp_path / "suite.json"
    public = decision_from_message(raw_combat(), session_id="x", sequence=1).to_dict()[
        "observation"
    ]
    write(
        suite_path,
        {
            "schema_version": 1,
            "id": "synthetic-development",
            "purpose": "development",
            "game_seed": "ABC",
            "policy_seed": 1000,
            "episodes": 2,
            "expected_start_sha256": normalized_observation_fingerprint(public),
        },
    )
    provenance = {
        "source_revision": "a" * 40,
        "source_status": "",
        "source_files": {"source": "hash"},
        "environment": {"fixture": True},
        "command": ["synthetic-test"],
    }
    monkeypatch.setattr(training, "_provenance", lambda: copy.deepcopy(provenance))
    monkeypatch.setattr(training, "source_fingerprints", lambda: dict(provenance["source_files"]))
    calls = []

    def collect(*args, **kwargs):
        calls.append(str(args[0]))
        return synthetic_collector(*args, **kwargs)

    monkeypatch.setattr(training, "run_episode", collect)
    config = {
        "suite_path": str(suite_path),
        "total_episodes": 2,
        "batch_steps": 2,
        "max_updates": 2,
        "time_budget_seconds": 1000,
        "seed": 7,
    }
    return config, calls


def make_catalog_config(config, monkeypatch):
    """Two synthetic seeded scenarios; this is not an executable engine catalog."""
    original_raw = raw_combat

    def cultist_combat():
        raw = original_raw()
        raw["game_state"]["combat_state"]["monsters"][0].update(id="Cultist", name="Cultist")
        return raw

    monkeypatch.setitem(globals(), "raw_combat", cultist_combat)
    suite = read(Path(config["suite_path"]))
    suite["expected_start_sha256"] = normalized_observation_fingerprint(
        decision_from_message(cultist_combat(), session_id="fixture", sequence=1).to_dict()[
            "observation"
        ]
    )
    write(Path(config["suite_path"]), suite)
    catalog = {
        "schema_version": 2,
        "purpose": "development",
        "id": "synthetic-catalog",
        "scenarios": [
            {
                "id": name,
                "game_seed": seed,
                "expected_start_sha256": suite["expected_start_sha256"],
                "encounter_family": "cultist",
                "monster_ids": ["Cultist"],
                "discovery_trace_sha256": "0123456789abcdef" * 4,
            }
            for name, seed in (("cultist-first", "ABC"), ("cultist-second", "DEF"))
        ],
        "schedule": [
            {"scenario_id": "cultist-first", "policy_seed": 9000},
            {"scenario_id": "cultist-first", "policy_seed": 9001},
            {"scenario_id": "cultist-second", "policy_seed": 9002},
        ],
    }
    path = Path(config["suite_path"]).with_name("catalog.json")
    write(path, catalog)
    return {**config, "suite_path": str(path)}


@pytest.fixture
def catalog_setup(setup, monkeypatch):
    config, calls = setup
    return make_catalog_config(config, monkeypatch), calls
