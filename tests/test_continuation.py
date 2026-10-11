"""Synthetic continuation state/trace regressions; not original-engine certification."""

import importlib.util
import json
import os
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from spire import continuation as c
from spire import continuation_protocol as p
from spire.bridge import BridgeDisconnected
from spire.evidence import normalized_observation_fingerprint
from spire.protocol import ProtocolError, decision_from_message


def combat(floor=1, hp=80, gold=199, intent="ATTACK"):
    card = {"id": "Strike_R", "upgrades": 0, "cost": 1, "has_target": True, "is_playable": True}
    deck = [{"id": name, "upgrades": 0} for name in ["Strike_R"] * 5 + ["Defend_R"] * 4 + ["Bash"]]
    return {
        "ready_for_command": True,
        "in_game": True,
        "available_commands": ["play", "end", "wait"],
        "game_state": {
            "class": "IRONCLAD",
            "ascension_level": 0,
            "act": 1,
            "floor": floor,
            "current_hp": hp,
            "max_hp": 80,
            "gold": gold,
            "deck": deck,
            "relics": [{"id": "Burning Blood", "counter": -1}],
            "potions": [{"id": "Potion Slot"}] * 3,
            "room_type": "MonsterRoom",
            "room_phase": "COMBAT",
            "screen_type": "NONE",
            "combat_state": {
                "turn": 1,
                "hand": [card],
                "draw_pile": [],
                "discard_pile": [],
                "exhaust_pile": [],
                "player": {"current_hp": hp, "max_hp": 80, "energy": 1, "block": 0, "powers": []},
                "monsters": [
                    {
                        "id": "Cultist" if floor == 1 else "JawWorm",
                        "current_hp": 6,
                        "max_hp": 50,
                        "block": 0,
                        "intent": intent,
                        "move_adjusted_damage": 6,
                        "move_hits": 1,
                        "powers": [],
                        "is_gone": False,
                        "half_dead": False,
                    }
                ],
            },
        },
    }


def reward(floor=1, hp=77, gold=199, claimed=False):
    raw = combat(floor, hp, gold)
    game = raw["game_state"]
    game.pop("combat_state")
    rewards = (
        [{"reward_type": "CARD"}]
        if claimed
        else [{"reward_type": "GOLD", "gold": 19}, {"reward_type": "CARD"}]
    )
    game.update(
        room_phase="COMPLETE",
        screen_type="COMBAT_REWARD",
        screen_state={"rewards": rewards},
        choice_list=[r["reward_type"].lower() for r in rewards],
    )
    raw["available_commands"] = ["choose", "proceed"]
    return raw


def map_message():
    raw = reward(gold=218, claimed=True)
    raw["game_state"].update(
        screen_type="MAP",
        choice_list=["x=4", "x=1"],
        screen_state={
            "current_node": {"x": 0, "y": 0},
            "boss_available": False,
            "first_node_chosen": True,
            "next_nodes": [{"x": 4, "y": 1, "symbol": "?"}, {"x": 1, "y": 1, "symbol": "M"}],
        },
    )
    raw["available_commands"] = ["choose", "return"]
    return raw


def messages():
    return [
        combat(),
        reward(),
        reward(gold=218, claimed=True),
        map_message(),
        combat(2, 77, 218, "DEBUG"),
        combat(2, 77, 218),
        reward(2, 78, 218),
    ]


@pytest.fixture(autouse=True)
def synthetic_pin(monkeypatch):
    public = decision_from_message(combat(), session_id="test", sequence=1).to_dict()["observation"]
    monkeypatch.setitem(
        c.CONTRACT, "initial_start_sha256", normalized_observation_fingerprint(public)
    )


def drive(values, second_policy="heuristic"):
    machine = c.Segment("test", second_policy)
    commands = []
    for sequence, raw in enumerate(values, 1):
        previous = machine.pending["action"]["id"] if machine.pending else None
        plan = machine.observe(raw, sequence, previous)
        if plan:
            commands.append(plan["action"]["command"])
            machine.sent(plan)
    return machine, commands


def test_two_combat_progress_gold_removal_map_ordinal_and_second_settle():
    machine, commands = drive(messages())
    assert commands == ["play 1 0", "CHOOSE 0", "PROCEED", "CHOOSE 1", "WAIT 60", "play 1 0"]
    assert machine.terminal == "completed_segment"
    assert machine.summary()["completed_combats"] == 2
    assert machine.summary()["combat_actions"] == 2
    assert machine.summary()["transit_actions"] == 3
    assert [(item["starting_hp"], item["ending_hp"], item["gold"]) for item in machine.combats] == [
        (80, 77, 199),
        (77, 78, 218),
    ]


@pytest.mark.parametrize(
    "index,mutation,expected",
    [
        (2, lambda g: g.update(gold=199), "continuity"),
        (2, lambda g: g.update(current_hp=78), "continuity"),
        (
            2,
            lambda g: g["screen_state"]["rewards"].insert(0, {"reward_type": "GOLD", "gold": 20}),
            "ordinals",
        ),
        (3, lambda g: g["screen_state"]["current_node"].update(x=2), "declared first node"),
        (4, lambda g: g.update(floor=3), "declared second floor"),
        (4, lambda g: g.update(current_hp=76), "continuity"),
        (5, lambda g: g["combat_state"]["monsters"][0].update(id="AcidSlime_M"), "encounter"),
        (5, lambda g: g["deck"][0].update(upgrades=1), "starter deck"),
        (5, lambda g: g["potions"][0].update(id="Fire Potion"), "empty slots"),
    ],
)
def test_continuity_and_unsupported_second_encounter_fail_closed(index, mutation, expected):
    values = messages()
    mutation(values[index]["game_state"])
    with pytest.raises(ProtocolError, match=expected):
        drive(values)


def test_second_death_is_not_segment_completion():
    values = messages()
    values[-1]["game_state"].update(
        current_hp=0, screen_type="GAME_OVER", screen_name="DEATH", screen_state={"victory": False}
    )
    machine, commands = drive(values, "end_turn")
    assert commands[-1] == "end"
    assert machine.terminal == "lost" and machine.summary()["completed_combats"] == 1


def test_transit_choices_hide_private_fields_and_rebind_changed_reward_ordinals():
    raw = reward()
    raw["game_state"].update(seed=123, current_action="private")
    raw["game_state"]["deck"][0]["uuid"] = "private-uuid"
    raw["game_state"]["screen_state"]["rewards"].insert(
        0, {"reward_type": "CARD", "cards": ["future"]}
    )
    raw["game_state"]["choice_list"] = ["card", "gold", "card"]
    first = p.transit_decision(raw, session_id="test", sequence=1)
    assert p.choose_transit(first)["command"] == "CHOOSE 1"
    serialized = json.dumps(first)
    assert all(word not in serialized for word in ("private", "future", "uuid", "seed"))
    second = p.transit_decision(reward(), session_id="test", sequence=2)
    assert p.choose_transit(second)["command"] == "CHOOSE 0"
    with pytest.raises(ProtocolError):
        p.validate_transit_action(second, p.choose_transit(first))


@pytest.fixture
def runtime(monkeypatch):
    state = SimpleNamespace(
        values=messages(), commands=[], launched=0, closed=0, cleanup_error=None
    )

    class Bridge:
        address = ("172.18.1.2", 19876)

        def __init__(self, **kwargs):
            self.values = iter(state.values)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def receive(self):
            value = next(self.values)
            if isinstance(value, BaseException):
                raise value
            return value() if callable(value) else value

        def send(self, command):
            state.commands.append(command)

    class Game:
        info = {"pid": 1234}

        def __init__(self, *args, **kwargs):
            state.launched += 1

        def __enter__(self):
            return self

        def __exit__(self, *_):
            state.closed += 1
            if state.cleanup_error:
                raise state.cleanup_error

    monkeypatch.setattr(c, "BridgeServer", Bridge)
    monkeypatch.setattr(c, "OwnedGame", Game)
    monkeypatch.setattr(c, "RuntimeLock", nullcontext)
    monkeypatch.setattr(c, "_deadline", lambda *_: nullcontext(lambda: None))
    monkeypatch.setattr(c, "wsl_bridge_host", lambda: "172.18.1.2")
    monkeypatch.setattr(
        c, "prepare_runtime", lambda *a, **kw: {"mods": {n: p[1] for n, p in c.PINS.items()}}
    )
    monkeypatch.setattr(c, "collect_diagnostics", lambda: {"game": {"sha256": c.ENGINE_SHA256}})
    monkeypatch.setattr(c, "collect_profile", lambda *_: {"active_slot": 0})
    monkeypatch.setattr(
        c.subprocess, "check_output", lambda args, **kw: "" if "status" in args else "a" * 40
    )
    return state


def refresh_hashes(directory):
    manifest = json.loads((directory / "manifest.json").read_text())
    manifest["files"] = {name: c.sha256(directory / name) for name in manifest["files"]}
    c.write_json(directory / "manifest.json", manifest)


def test_collector_auditor_killing_blow_on_final_action_limit(tmp_path, runtime):
    runtime.values.insert(-1, {"ready_for_command": False, "in_game": True})
    report = c.run_continuation(tmp_path / "run", max_actions=6)
    assert report["result"]["status"] == "completed_segment"
    assert report["audit"]["valid"], report["audit"]["errors"]
    assert runtime.launched == runtime.closed == 1


@pytest.mark.parametrize(
    "problem,status",
    [
        (KeyboardInterrupt(), "interrupted"),
        (BridgeDisconnected("probe"), "infrastructure_failure"),
    ],
)
def test_failed_segment_preserves_first_completed_combat(tmp_path, runtime, problem, status):
    runtime.values = messages()[:3] + [problem]
    report = c.run_continuation(tmp_path / "run")
    assert report["result"]["status"] == status
    assert report["result"]["completed_combats"] == 1
    assert report["audit"]["valid"], report["audit"]["errors"]
    assert runtime.closed == 1


def test_unsupported_second_combat_retains_partial_evidence(tmp_path, runtime):
    runtime.values[4]["game_state"]["combat_state"]["monsters"][0]["id"] = "AcidSlime_M"
    report = c.run_continuation(tmp_path / "run")
    assert report["result"]["status"] == "unsupported_or_invalid"
    assert report["result"]["completed_combats"] == 1
    assert report["audit"]["valid"], report["audit"]["errors"]


@pytest.mark.parametrize("corruption", ["hp", "ack", "action", "result", "source", "missing_file"])
def test_auditor_rejects_coherently_rehashed_corruption(tmp_path, runtime, corruption):
    directory = tmp_path / "run"
    assert c.run_continuation(directory)["audit"]["valid"]
    events = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
    if corruption in {"hp", "ack"}:
        event = next(e for e in events if e["kind"] == "observation" and e["sequence"] == 3)
        if corruption == "hp":
            event["raw"]["game_state"]["current_hp"] = 78
        else:
            event["previous_action_id"] = "wrong:stale"
    elif corruption == "action":
        event = next(e for e in events if e["kind"] == "action" and e["plan"]["role"] == "transit")
        event["plan"]["action"]["command"] = "CHOOSE 1"
    elif corruption == "result":
        events[-1]["result"]["completed_combats"] = 3
        c.write_json(directory / "result.json", events[-1]["result"])
    elif corruption == "source":
        manifest = json.loads((directory / "manifest.json").read_text())
        manifest["source_files"]["src/spire/continuation.py"] = "0" * 64
        c.write_json(directory / "manifest.json", manifest)
    else:
        manifest = json.loads((directory / "manifest.json").read_text())
        del manifest["files"]["environment.json"]
        c.write_json(directory / "manifest.json", manifest)
    (directory / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    refresh_hashes(directory)
    assert not c.audit_continuation(directory)["valid"]


def test_discovery_failure_occurs_before_owned_game(tmp_path, runtime, monkeypatch):
    monkeypatch.setattr(c, "wsl_bridge_host", Mock(side_effect=RuntimeError("ambiguous eth0")))
    report = c.run_continuation(tmp_path / "run")
    assert report["result"]["status"] == "infrastructure_failure"
    assert report["audit"]["valid"] and runtime.launched == 0


def test_action_limit_retains_first_win_without_claiming_segment_success(tmp_path, runtime):
    report = c.run_continuation(tmp_path / "run", max_actions=1)
    assert report["result"]["status"] == "truncated"
    assert report["result"]["reason"] == "action_limit"
    assert report["result"]["completed_combats"] == 1
    assert report["audit"]["valid"]


def test_second_settling_is_bounded_and_never_counts_combat_completion():
    values = messages()[:4] + [combat(2, 77, 218, "DEBUG")] * 4
    with pytest.raises(ProtocolError, match="three waits"):
        drive(values)


def test_saved_original_first_combat_reaches_unclaimed_gold_boundary(monkeypatch):
    root = Path(os.environ.get("SPIRE_EVIDENCE_ROOT", Path(__file__).parents[1]))
    episode = root / "runs/baseline-heuristic-settled-20261011/episode-0000"
    if not (episode / "trace.jsonl").exists():
        pytest.skip("Optional saved original-engine first-combat evidence is unavailable")
    monkeypatch.setitem(c.CONTRACT, "initial_start_sha256", p.INITIAL_START_SHA256)
    result = json.loads((episode / "result.json").read_text())
    machine = c.Segment(result["session_id"])
    for line in (episode / "trace.jsonl").read_text().splitlines():
        event = json.loads(line)
        if event["kind"] == "observation":
            machine.observe(event["raw"], event["sequence"], event["previous_action_id"])
        elif event["kind"] == "action":
            assert event["command"] == machine.plan["action"]["command"]
            machine.sent(machine.plan)
    assert machine.terminal is None and machine.phase == "reward"
    assert machine.summary()["completed_combats"] == 1
    assert machine.carried["current_hp"] == 77 and machine.carried["gold"] == 199
    assert machine.plan["action"]["kind"] == "gold"
    assert machine.plan["action"]["choice"] == {"reward_type": "GOLD", "gold": 19}


@pytest.mark.parametrize(
    "error",
    [c.SegmentDeadline("cleanup deadline"), KeyboardInterrupt(), RuntimeError("cleanup failure")],
)
def test_cleanup_failure_cannot_overwrite_timely_verified_endpoint(tmp_path, runtime, error):
    runtime.cleanup_error = error
    report = c.run_continuation(tmp_path / "run")
    assert report["result"]["status"] == "completed_segment"
    assert "cleanup_error" in report["result"]
    assert report["audit"]["valid"], report["audit"]["errors"]


@pytest.mark.parametrize("corruption", ["late_terminal", "source_revision", "contract_document"])
def test_auditor_rejects_false_deadline_or_source_attribution(tmp_path, runtime, corruption):
    directory = tmp_path / "run"
    assert c.run_continuation(directory)["audit"]["valid"]
    if corruption == "late_terminal":
        events = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
        events[-2]["elapsed"] = 241.0
        events[-1]["elapsed"] = 241.2
        events[-1]["result"]["elapsed_seconds"] = 241.1
        c.write_json(directory / "result.json", events[-1]["result"])
        (directory / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    else:
        manifest = json.loads((directory / "manifest.json").read_text())
        field = "source_revision" if corruption == "source_revision" else "contract_document_sha256"
        manifest[field] = "f" * (40 if corruption == "source_revision" else 64)
        c.write_json(directory / "manifest.json", manifest)
    refresh_hashes(directory)
    assert not c.audit_continuation(directory)["valid"]


def test_watchdog_disconnect_at_deadline_is_truncated_not_infrastructure(
    tmp_path, runtime, monkeypatch
):
    now = [0.0]
    monkeypatch.setattr(c.time, "monotonic", lambda: now[0])

    def deadline_disconnect():
        now[0] = 240.0
        raise BridgeDisconnected("owned watchdog stopped game")

    runtime.values = messages()[:3] + [deadline_disconnect]
    report = c.run_continuation(tmp_path / "run")
    assert report["result"]["status"] == "truncated"
    assert report["result"]["reason"] == "time_limit"
    assert report["result"]["completed_combats"] == 1
    assert report["audit"]["valid"], report["audit"]["errors"]


@pytest.mark.parametrize(
    "cleanup_error,exit_code", [(None, 0), ({"status": "infrastructure_failure"}, 1)]
)
def test_command_stops_gate_on_cleanup_failure(monkeypatch, tmp_path, cleanup_error, exit_code):
    spec = importlib.util.spec_from_file_location(
        "continue_two_combats", Path(__file__).parents[1] / "scripts/continue_two_combats.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module,
        "run_continuation",
        lambda *a, **kw: {
            "audit": {"valid": True},
            "result": {"status": "completed_segment", "cleanup_error": cleanup_error},
        },
    )
    monkeypatch.setattr(
        sys, "argv", ["continue_two_combats.py", "run", "--output", str(tmp_path / "run")]
    )
    assert module.main() == exit_code


def test_repeated_complete_reward_is_not_an_ack_or_another_combat():
    machine = c.Segment("test")
    for sequence, raw in enumerate([combat(), reward()], 1):
        previous = machine.pending["action"]["id"] if machine.pending else None
        machine.sent(machine.observe(raw, sequence, previous))
    with pytest.raises(ProtocolError, match="failed to remove"):
        machine.observe(reward(), 3, machine.pending["action"]["id"])
    assert machine.summary()["completed_combats"] == 1
    assert machine.terminal is None


def test_initial_combat_must_match_existing_canonical_pin():
    raw = combat()
    raw["game_state"]["combat_state"]["player"]["energy"] = 2
    with pytest.raises(ProtocolError, match="Initial combat pin"):
        drive([raw])
