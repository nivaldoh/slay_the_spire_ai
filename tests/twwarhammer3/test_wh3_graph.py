"""Hand-computed cases for the owner-agreed initial graph contract (2026-10-31).

References: gap-plan G2–G9; bridge flag names in twwarhammer3_battle.lua unit_record.
These are component cases, not live effects or policy-strength evidence.
"""

import json
from copy import deepcopy

import pytest
from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation

from twwarhammer3.battle import graph, play
from twwarhammer3.battle import skill_contracts as catalog
from twwarhammer3.protocol import IllegalActionError, PolicyFailure


def state(seq=1, time_ms=10000, **changes):
    return {"battle": "b1", "phase": "Deployed", "seq": seq, "time_ms": time_ms,
            "friendly": [{"id": "u", "x": 0, "z": 0, "men": 100, "state": []}],
            "enemy": [{"id": "e", "x": 20, "z": 0, "men": 100, "state": []}], **changes}


def move_graph():
    return {"version": graph.VERSION, "entry": "move", "nodes": {
        "move": {"op": "move", "inputs": {"units": ["u"], "point": {"x": 20, "z": 0}},
                 "next": {"succeeded": "end", "failed": "end", "cancelled": "end"}},
        "end": {"op": "end", "inputs": {}, "next": {}}}}


def attack_graph(op="engage"):
    return {"version": graph.VERSION, "entry": "owned", "nodes": {
        "owned": {"op": "owned", "inputs": {},
                  "next": {"succeeded": "pick", "empty": "owned"}},
        "pick": {"op": "select_target", "inputs": {"units": {"ref": "owned.units"}},
                 "next": {"succeeded": "act", "empty": "owned"}},
        "act": {"op": op, "inputs": {"units": {"ref": "owned.units"},
                                       "target": {"ref": "pick.target"}},
                "next": {"succeeded": "owned", "failed": "owned", "cancelled": "owned"}}}}


def test_move_needs_arrival_not_ack_and_preserves_run_source():
    policy = graph.GraphPolicy(move_graph())
    orders = policy.decide(state())
    assert len(orders) == 1 and orders[0]["unit"] == "u"
    assert (orders[0]["x"], orders[0]["z"]) == (20, 0)
    policy.acknowledge({"accepted": True, "results": [{"ok": True}]}, {})
    policy.decide(state(2, 11000))
    assert policy.node == "move" and policy.run.status == "running"
    arrived = state(3, 12000)
    arrived["friendly"][0]["x"] = 16
    assert policy.decide(arrived) == [] and policy.node == "end"
    events = policy.drain_events()
    finished = next(e for e in events if e["event"] == "transition")
    assert finished["status"] == "succeeded" and finished["witness"] == "inside arrival radius"
    assert finished["source"] == {"battle": "b1", "seq": 3, "time_ms": 12000}


def test_effect_timeout_refusal_and_cancel_do_not_invent_success():
    policy = graph.GraphPolicy(move_graph())
    policy.decide(state())
    policy.decide(state(2, 10000 + catalog.TIMEOUT_MS))
    assert policy.metadata()["status"] == "failed"
    assert "deadline" in policy.metadata()["witness"]
    policy = graph.GraphPolicy(move_graph())
    policy.decide(state())
    policy.acknowledge({"results": [{"ok": False, "error": "unreachable"}]}, {})
    policy.decide(state(2, 11000))
    assert policy.metadata()["status"] == "failed"
    policy = graph.GraphPolicy(move_graph())
    policy.decide(state())
    policy.close()
    assert policy.run.status == "cancelled" and "no stop order" in policy.run.reason
    assert policy.decide(state(2, 11000)) == []


def test_late_arrival_cannot_retroactively_pass_a_deadline():
    policy = graph.GraphPolicy(move_graph())
    policy.decide(state())
    late = state(2, 10000 + catalog.TIMEOUT_MS)
    late["friendly"][0]["x"] = 20
    assert policy.decide(late) == []
    assert policy.metadata()["status"] == "failed"


def test_dispatch_guard_handles_empty_end_and_rejects_expired_or_old_runs():
    policy = graph.GraphPolicy(move_graph())
    orders = policy.decide(state())
    with pytest.raises(IllegalActionError, match="expired"):
        policy.dispatch_guard(orders, state(2, 10000 + graph.MAX_AGE_MS))
    with pytest.raises(IllegalActionError, match="battle"):
        policy.dispatch_guard(orders, state(2, battle="different"))
    policy.run = None
    with pytest.raises(IllegalActionError, match="node run"):
        policy.dispatch_guard(orders, state(2))
    policy.close()
    policy.dispatch_guard([], state(2))
    with pytest.raises(IllegalActionError, match="battle"):
        policy.dispatch_guard(orders, state(2))


def test_public_contact_branches_and_loops_yield_on_new_observations():
    spec = {"version": graph.VERSION, "entry": "contact", "nodes": {
        "contact": {"op": "contact", "inputs": {}, "max_visits": 2,
                    "next": {"yes": "done", "no": "contact"}},
        "done": {"op": "end", "inputs": {}, "next": {}}}}
    policy = graph.GraphPolicy(spec)
    assert policy.decide(state()) == [] and policy.visits["contact"] == 1
    assert policy.decide(state()) == [] and policy.visits["contact"] == 1
    fighting = state(2, 11000, allies=[{"id": "ally", "men": 40, "x": 0, "z": 0,
                                      "state": ["melee"]}])
    policy.decide(fighting)
    assert policy.node == "done"
    exhausted = graph.GraphPolicy(spec)
    for seq in range(1, 4):
        assert exhausted.decide(state(seq)) == []
    assert exhausted.closed
    assert any(e["event"] == "exhausted" for e in exhausted.drain_events())


def test_target_selection_identity_and_typed_provenance_then_visibility_loss():
    policy = graph.GraphPolicy(attack_graph())
    policy.decide(state())  # owned
    policy.decide(state(2))  # pick e
    orders = policy.decide(state(3))
    assert len(orders) == 1 and orders[0]["target"] == "e" and orders[0]["unit"] == "u"
    started = [e for e in policy.drain_events() if e["event"] == "started"][-1]
    source = started["input_sources"]["target"]
    assert source["producer"] == "pick" and source["node_run"] == 1
    assert source["battle"] == "b1" and source["seq"] == 2
    assert source["graph_sha256"] == policy.revision
    with pytest.raises(IllegalActionError, match="not visible"):
        policy.dispatch_guard(orders, state(4, enemy=[]))
    assert policy.decide(state(4, enemy=[])) == []
    assert policy.node == "owned" and policy.metadata()["status"] == "failed"


def test_empty_selection_cannot_use_an_old_target_and_new_units_join_next_cycle():
    policy = graph.GraphPolicy(attack_graph())
    for seq in range(1, 4):
        policy.decide(state(seq))
    contact = state(4)
    contact["friendly"][0].update(target="e", state=["melee"])
    policy.decide(contact)
    policy.decide(state(5, enemy=[]))
    policy.decide(state(6, enemy=[]))
    assert "pick.target" not in policy.values and policy.node == "owned"
    rallied = state(7)
    rallied["friendly"].append({"id": "new", "x": 0, "z": 5, "men": 10, "state": []})
    policy.decide(rallied)
    assert policy.values["owned.units"]["value"] == ["u", "new"]


@pytest.mark.parametrize("op", ["engage", "charge"])
def test_named_tactic_never_substitutes_a_different_target(op):
    view = state()
    view["friendly"][0].update(ammo=10, range=100, **{"class": "cavalry"})
    view["enemy"][0]["state"] = ["melee"]
    view["enemy"].append({"id": "other", "x": 1, "z": 0, "men": 100,
                           "class": "lord", "state": ["melee"]})
    run = catalog.SkillRun(op, {"units": ["u"], "target": "e"}, view["time_ms"])
    status, orders, _ = run.tick(view)
    assert status == "running" and orders[0]["target"] == "e"
    run.acknowledge({"results": [{"ok": True}]})
    assert run.tick(view)[0] == "running"
    view["friendly"][0].update(target="other", state=["melee"], ammo=9)
    assert run.tick(view)[0] == "running"
    view["friendly"][0]["target"] = "e"
    assert run.tick(view)[0] == "succeeded"


def test_charge_requires_target_contact_and_shoot_final_round_is_a_witness():
    run = catalog.SkillRun("charge", {"units": ["u"], "target": "e"}, 10000)
    assert run.tick(state())[0:2] == ("failed", [])
    view = state()
    view["friendly"][0].update(ammo=1, range=100, target="e")
    run = catalog.SkillRun("shoot", {"units": ["u"], "target": "e"}, 10000)
    assert run.tick(view)[0] == "running"
    view["friendly"][0].update(ammo=0, target="e")
    assert run.tick(view)[0] == "succeeded"


def test_unrelated_shot_then_target_acquisition_is_not_a_shoot_witness():
    view = state()
    view["friendly"][0].update(ammo=10, range=100, target="old")
    run = catalog.SkillRun("shoot", {"units": ["u"], "target": "e"}, 10000)
    assert run.tick(view)[0] == "running"
    view["friendly"][0]["ammo"] = 9
    assert run.tick(view)[0] == "running"  # unrelated shot
    view["friendly"][0]["target"] = "e"
    assert run.tick(view)[0] == "running"  # only target acquisition
    view["friendly"][0]["ammo"] = 8
    assert run.tick(view)[0] == "succeeded"


def test_hold_may_engage_and_rout_is_failure_then_rally_reselects():
    view = state()
    run = catalog.SkillRun("hold", {"units": ["u"], "point": {"x": 0, "z": 0}}, 10000)
    assert run.tick(view)[1][0]["type"] == "attack"
    view["friendly"][0]["state"] = ["routing"]
    assert run.tick(view)[0] == "failed"
    policy = graph.GraphPolicy(attack_graph())
    assert policy.decide(view) == [] and policy.node == "owned"
    policy.decide(state(2))
    assert policy.values["owned.units"]["value"] == ["u"]


def test_hidden_fields_do_not_change_graph_output_or_events():
    a, b = graph.GraphPolicy(attack_graph()), graph.GraphPolicy(attack_graph())
    for seq in range(1, 5):
        view = state(seq)
        poisoned = deepcopy(view)
        poisoned.update(evaluation={"secret": seq}, final={"enemy": 4}, setup={"secret": 2},
                        native={"peer": 4}, orders={"private": 9})
        poisoned["friendly"][0].update(target="hidden", target_dead=True)
        assert a.decide(view) == b.decide(poisoned)
        assert a.drain_events() == b.drain_events()


def test_new_battle_requires_fresh_instance_and_terminal_discards_work():
    a, b = graph.GraphPolicy(move_graph()), graph.GraphPolicy(move_graph())
    a.decide(state())
    assert b.battle is None and b.visits == {}
    with pytest.raises(PolicyFailure, match="different battle"):
        a.decide(state(2, battle="new"))
    assert a.decide(state(2, phase="Complete", result="won")) == [] and a.closed


@pytest.mark.parametrize("change", ["op", "input", "exit", "script", "type", "path", "empty"])
def test_invalid_or_ambiguous_graphs_are_rejected(change):
    spec = attack_graph()
    if change == "op":
        spec["nodes"]["act"]["op"] = "eval"
    elif change == "input":
        spec["nodes"]["act"]["inputs"]["hidden"] = 1
    elif change == "exit":
        spec["nodes"]["act"]["next"]["succeeded"] = "missing"
    elif change == "script":
        spec["nodes"]["act"]["script"] = "arbitrary.py"
    elif change == "type":
        spec["nodes"]["act"]["inputs"]["target"] = {"ref": "owned.units"}
    elif change == "path":
        spec["entry"] = "act"
    else:
        spec["nodes"]["pick"]["next"]["empty"] = "act"
    with pytest.raises(ValueError, match="graph:"):
        graph.validate(spec)


def test_repeated_consumer_without_new_producer_is_refused():
    spec = attack_graph()
    spec["nodes"]["act"]["next"]["failed"] = "act"
    policy = graph.GraphPolicy(spec)
    for seq in range(1, 4):
        policy.decide(state(seq))
    policy.decide(state(4, enemy=[]))
    with pytest.raises(PolicyFailure, match="stale input"):
        policy.decide(state(5, enemy=[]))


def test_single_graph_dispatch_also_checks_latest_view_when_input_is_delayed(tmp_path):
    spec = move_graph()
    spec["nodes"]["move"]["inputs"]["units"] = ["f1"]
    mailbox = FakeMailbox([
        bridge_observation(0, 0),
        bridge_observation(1, 10000),
        bridge_observation(2, 16000),
        bridge_observation(3, 16500, ack=True),
        bridge_observation(4, 17000, result="won")])
    directory = tmp_path / "episode"
    result = play.play_episode(directory, {**CONFIG, "interval_ms": 0, "delay_ms": 5000},
                               lambda: graph.GraphPolicy(spec), mailbox, not_battle=None)
    assert result["invalid"] == 1
    assert mailbox.requests[0][1:] == (1, [])  # old source seq retained; no stale orders sent
    events = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
    assert "expired" in next(e for e in events if e["kind"] == "invalid")["error"]
