"""Model preferences retain their own producer identity in the graph view."""

import json
from copy import deepcopy

import pytest
from test_wh3_graph_goals import spec, state

from twwarhammer3.battle import graph, graph_view


def recording(root):
    root.mkdir(parents=True)
    definition = spec()
    revision = graph.digest(definition)
    configuration = {"type": "team", "members": {
        "line": {"unit_types": ["foot"], "controller": {"type": "graph_llm", "graph": definition}},
        "other": {"unit_types": None, "controller": {"type": "hold"}}}}
    result = {"battle": "battle-A", "status": "synthetic test only", "card": {"disclosure": {
        "configuration": configuration, "configuration_sha256": graph.digest(configuration),
        "member_controllers": {"line": {"disclosure": {"goal_controller": "goal-L"}}}}}}
    source = {"battle": "battle-A", "seq": 1, "time_ms": 1000}
    goal = {**source, "producer": "goal_request", "controller": "goal-L",
            "graph_sha256": revision, "owned": ["u"], "node_run": 1}
    owned = {**source, "graph_sha256": revision, "producer": "owned", "node_run": 1,
             "value": ["u"]}

    def node(event, name, seq, ms, **fields):
        return {"kind": "team", "event": "member_event", "member": "line", "record": {
            "event": event, "node": name, "node_run": 1, "graph_sha256": revision,
            "source": {"battle": "battle-A", "seq": seq, "time_ms": ms}, **fields}}

    rows = [
        {"kind": "observation", "observation": state()},
        node("started", "owned", 1, 1000, inputs={}),
        node("transition", "owned", 1, 1000, status="succeeded", successor="pick",
             outputs={"units": ["u"]}),
        {"kind": "observation", "observation": state(2, 1100)},
        {"kind": "team", "event": "member_event", "member": "line", "record": {
            "event": "goal_adopted", "node": "goal_request", "node_run": 1,
            "graph_sha256": revision, "source": deepcopy(goal), "target": "far", "reason": "test"}},
        node("started", "pick", 2, 1100, inputs={"units": ["u"]}, input_sources={"units": owned}),
        node("transition", "pick", 2, 1100, status="succeeded", successor="act",
             outputs={"target": "far"}, selection={"preference": {
                 "target": "far", "reason": "test", "source": deepcopy(goal)}, "used": True}),
    ]
    write(root, result, rows)
    return root, result, rows


def write(root, result, rows):
    (root / "result.json").write_text(json.dumps(result))
    (root / "trace.jsonl").write_text("\n".join(map(json.dumps, rows)) + "\n")


def test_selection_matches_a_known_model_goal_and_its_recorded_scope(tmp_path):
    episode, _, _ = recording(tmp_path / "episode")
    data = graph_view.collect_episode(episode)
    selected = data["events"][-1]
    assert selected["node"] == "pick" and selected["outputs"]["target"] == "far"
    assert selected["selection"]["goal_line"] == 5
    assert selected["selection"]["preference"]["source"]["seq"] == 1
    assert selected["source"]["seq"] == 2  # selection rechecks a newer public view
    assert "line" in data["graphs"]


@pytest.mark.parametrize("change", ["controller", "battle", "graph", "clock", "goal", "target"])
def test_model_hint_cannot_be_reattributed_to_a_different_producer(tmp_path, change):
    episode, result, rows = recording(tmp_path / "episode")
    adopted = rows[4]["record"]
    selection = rows[6]["record"]["selection"]
    if change == "controller":
        adopted["source"]["controller"] = selection["preference"]["source"]["controller"] = "other"
    elif change == "battle":
        adopted["source"]["battle"] = selection["preference"]["source"]["battle"] = "other"
    elif change == "graph":
        adopted["source"]["graph_sha256"] = "foreign-graph"
        selection["preference"]["source"]["graph_sha256"] = "foreign-graph"
    elif change == "clock":
        adopted["source"]["time_ms"] = selection["preference"]["source"]["time_ms"] = 999
    elif change == "goal":
        rows.pop(4)
    else:
        selection["preference"]["target"] = "near"
    write(episode, result, rows)
    with pytest.raises(ValueError, match="recorded goal producer"):
        graph_view.collect_episode(episode)
