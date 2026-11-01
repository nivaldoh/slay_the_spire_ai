"""Hand-computed engine observations for the graph effect checker, including wrong witnesses."""

import json
from copy import deepcopy

import pytest
from check_wh3_graph import assess, recount

from twwarhammer3.battle import team


def view(seq, ms, *, cav_x=0, cav_target=None, cav_state=(), enemy_state=("melee",)):
    return {"battle": "b1", "phase": "Deployed", "seq": seq, "time_ms": ms, "speed": 1,
            "friendly": [
                {"id": "cav", "type": team.KNIGHT, "x": cav_x, "z": 0,
                 "bearing": 90, "state": list(cav_state), "target": cav_target},
                {"id": "line", "type": team.SWORD, "x": 80, "z": 0, "state": ["melee"]}],
            "enemy": [{"id": "e1", "x": 80, "z": 0, "state": list(enemy_state)},
                      {"id": "e2", "x": 90, "z": 0, "state": ["melee"]}]}


def ack(request, uid, applied):
    return {"request": request, "accepted": True, "applied_ms": applied,
            "results": [{"index": 1, "unit": uid, "ok": True}]}


def movement(control=False):
    samples = [{"written_ns": v["time_ms"] * 10**6, "observation": v} for v in (
        view(1, 10000), view(2, 15000),
        view(3, 16000, cav_x=0 if control else 1, cav_state=() if control else ("moving",)),
        view(4, 25000, cav_x=0 if control else 55))]
    events = [{"event": "probe_graph", "source_seq": 2, "unit": "cav",
               "point": {"x": 60, "z": 0}}]
    if not control:
        samples[2]["observation"]["orders"] = ack("move", "cav", 15500)
        events.append({"kind": "decision", "request": "move", "orders": [
            {"type": "move", "unit": "cav", **events[0]["point"]}]})
        events.extend([
            {"event": "started", "node": "m", "node_run": 1, "op": "move",
             "inputs": {"units": ["cav"], "point": events[0]["point"]}},
            {"event": "transition", "node": "m", "node_run": 1, "status": "succeeded",
             "source": {"battle": "b1", "seq": 4, "time_ms": 25000}}])
    return events, samples


def contact():
    samples = [{"written_ns": v["time_ms"] * 10**6, "observation": v} for v in (
        view(1, 10000), view(2, 11000), view(3, 12000, cav_x=40, cav_state=("moving",)),
        view(4, 13000, cav_x=65, cav_state=("melee",), cav_target="e1"))]
    samples[1]["observation"]["orders"] = ack("line", "line", 10500)
    samples[2]["observation"]["orders"] = ack("cav", "cav", 11500)
    events = [{"kind": "decision", "request": uid, "behavior": {
        "member": member, "source_seq": seq, "source_ms": ms},
        "orders": [{"type": "attack", "unit": uid, "target": "e1"}]}
        for uid, member, seq, ms in (("line", "line", 1, 10000), ("cav", "cavalry", 2, 11000))]
    events.extend([{"event": "member_event", "member": "cavalry", "record": record}
                   for record in (
        {"event": "started", "node": "c", "node_run": 1, "op": "charge",
         "inputs": {"units": ["cav"], "target": "e1"}},
        {"event": "transition", "node": "c", "node_run": 1, "status": "succeeded",
         "source": {"battle": "b1", "seq": 4, "time_ms": 13000}})])
    return events, samples


def test_independent_movement_and_no_order_witnesses():
    assert assess("control", *movement(True))["arrivals"] == 0
    assert assess("move", *movement())["arrival_ms"] == 25000


def test_arrival_before_ack_cannot_use_later_idle_frame_as_order_effect():
    events, samples = movement()
    samples[2]["observation"].pop("orders")
    later = {"written_ns": 30000 * 10**6, "observation": view(5, 30000, cav_x=55)}
    later["observation"]["orders"] = ack("move", "cav", 26000)
    samples.append(later)
    with pytest.raises(AssertionError):
        assess("move", events, samples)


@pytest.mark.parametrize("wrong", ["idle_drift", "no_effect", "wrong_unit",
                                  "rejected", "mismatched_ack", "wrong_point", "bad_geometry",
                                  "missing_transition"])
def test_movement_rejects_wrong_witnesses(wrong):
    control = wrong == "idle_drift"
    events, samples = movement(control)
    if wrong == "idle_drift":
        samples[-1]["observation"]["friendly"][0]["x"] = 55
    elif wrong == "no_effect":
        samples[-1]["observation"]["friendly"][0]["x"] = 1
    elif wrong == "wrong_unit":
        events[1]["orders"][0]["unit"] = "line"
    elif wrong == "rejected":
        samples[2]["observation"]["orders"]["results"][0]["ok"] = False
    elif wrong == "mismatched_ack":
        samples[2]["observation"]["orders"]["request"] = "other"
    elif wrong == "wrong_point":
        events[1]["orders"][0]["x"] = 61
    elif wrong == "missing_transition":
        events.pop()
    else:
        events[0]["point"]["x"] = 61
        events[1]["orders"][0]["x"] = 61
    with pytest.raises((AssertionError, StopIteration)):
        assess("control" if control else "move", events, samples)


def test_contact_requires_accepted_targeted_order_then_same_target_melee():
    assert assess("contact", *contact())["target"] == "e1"


@pytest.mark.parametrize("wrong", ["before_contact", "wrong_target", "not_visible", "no_effect",
                                  "rejected", "wrong_owner", "wrong_source", "speed",
                                  "missing_transition", "premature_transition"])
def test_contact_rejects_wrong_witnesses(wrong):
    events, samples = deepcopy(contact())
    if wrong == "before_contact":
        samples[1]["observation"]["enemy"][0]["state"] = []
    elif wrong == "wrong_target":
        events[1]["orders"][0]["target"] = "e2"
    elif wrong == "not_visible":
        samples[1]["observation"]["enemy"] = []
    elif wrong == "no_effect":
        samples[-1]["observation"]["friendly"][0]["state"] = []
    elif wrong == "rejected":
        samples[2]["observation"]["orders"]["results"][0]["ok"] = False
    elif wrong == "wrong_owner":
        events[1]["orders"][0]["unit"] = "line"
    elif wrong == "wrong_source":
        events[1]["behavior"]["source_ms"] = 12000
    elif wrong == "speed":
        samples[2]["observation"]["speed"] = 2
    elif wrong == "missing_transition":
        events.pop()
    else:
        events[-1]["record"]["source"]["seq"] = 3
    with pytest.raises((AssertionError, StopIteration)):
        assess("contact", events, samples)


@pytest.mark.parametrize("kind", ["control", "move", "contact"])
@pytest.mark.parametrize("wrong", ["slow", "foreign_battle"])
def test_measured_speed_and_battle_identity_are_required(kind, wrong):
    events, samples = contact() if kind == "contact" else movement(kind == "control")
    if wrong == "slow":
        for sample in samples:
            sample["written_ns"] *= 10
    else:
        samples[-1]["observation"]["battle"] = "another"
    with pytest.raises(AssertionError):
        assess(kind, events, samples)


def evidence(root, *, short_control=False, reused_battle=False):
    for kind in ("control", "move", "contact"):
        events, samples = contact() if kind == "contact" else movement(kind == "control")
        battle = "reused" if reused_battle else kind
        for sample in samples:
            sample["observation"]["battle"] = battle
        for event in events:
            record = event.get("record", event)
            if "source" in record:
                record["source"]["battle"] = battle
        if kind == "control" and short_control:
            samples[-1]["observation"]["time_ms"] = 20000
            samples[-1]["written_ns"] = 20000 * 10**6
        directory = root / kind
        (directory / "episode").mkdir(parents=True)
        for name, rows in (("observations.jsonl", samples), ("episode/trace.jsonl", events)):
            (directory / name).write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        (directory / "manifest.json").write_text(json.dumps({
            "closed": True, "remaining_pids": [],
            "result": {"status": "truncated", "battle": battle}}))


def test_recount_requires_matched_control_duration_and_fresh_battles(tmp_path):
    evidence(tmp_path / "good")
    assert recount(tmp_path / "good")["passed"] is True
    evidence(tmp_path / "short", short_control=True)
    result = recount(tmp_path / "short")
    assert result["passed"] is False and result["control_covers_arrival"] is False
    evidence(tmp_path / "reused", reused_battle=True)
    result = recount(tmp_path / "reused")
    assert result["passed"] is False and result["fresh_battles"] is False
