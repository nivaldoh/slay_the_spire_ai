"""Graph literal types and unit availability in the frozen skill library (skill_contracts)."""

import pytest

from twwarhammer3.battle import graph

END = {"op": "end", "inputs": {}, "next": {}}


def one_skill(op, inputs):
    return {"version": graph.VERSION, "entry": "act", "nodes": {"end": END, "act": {
        "op": op, "inputs": inputs,
        "next": {"succeeded": "end", "failed": "end", "cancelled": "end"}}}}


@pytest.mark.parametrize("op,field,value", [
    ("move", "units", []), ("move", "units", "uv"),
    ("engage", "target", ""), ("engage", "target", 7),
    ("move", "point", {"x": 1, "z": 2, "y": 3}), ("move", "point", {"x": 1}),
])
def test_graph_typing_refuses_literals_outside_the_published_types(op, field, value):
    # graph_author.frozen_library() "types": units are a non-empty array of distinct strings,
    # a target is a non-empty string, a point has exactly numeric x and z.
    inputs = {"units": ["u"], **({"point": {"x": 0, "z": 0}} if op == "move" else {"target": "e"})}
    graph.validate(one_skill(op, inputs))
    inputs[field] = value
    with pytest.raises(ValueError, match=f"invalid {field} literal"):
        graph.validate(one_skill(op, inputs))


def test_destroyed_friendly_units_are_not_owned():
    # The mod lists every friendly unit with men = number_of_men_alive (unit_record), so a
    # destroyed unit stays in the observation with 0 men; graph_author.DESCRIPTIONS: "owned"
    # excludes destroyed units.
    spec = {"version": graph.VERSION, "entry": "owned", "nodes": {"end": END, "owned": {
        "op": "owned", "inputs": {}, "next": {"succeeded": "end", "empty": "end"}}}}

    def finished(friendly):
        policy = graph.GraphPolicy(spec)
        policy.decide({"battle": "b", "phase": "Deployed", "seq": 1, "time_ms": 1000,
                       "friendly": friendly, "enemy": []})
        return next(e for e in policy.drain_events() if e["event"] == "transition")

    alive = {"id": "u", "x": 0, "z": 0, "men": 40, "state": []}
    destroyed = {"id": "d", "x": 5, "z": 0, "men": 0, "state": []}
    assert finished([alive, destroyed])["outputs"] == {"units": ["u"]}
    assert finished([destroyed])["status"] == "empty"
