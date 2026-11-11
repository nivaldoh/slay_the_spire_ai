"""Graph inputs and on-disk configuration shared by live-goal component tests."""

import json
from copy import deepcopy

from twwarhammer3.battle import graph


def state(seq=1, ms=1000):
    return {"battle": "battle-A", "seq": seq, "time_ms": ms, "phase": "Deployed",
            "friendly": [{"id": "u", "type": "foot", "x": 0, "z": 0,
                          "men": 10, "state": []}],
            "enemy": [{"id": "near", "x": 10, "z": 0, "men": 10, "state": []},
                      {"id": "far", "x": 50, "z": 0, "men": 10, "state": []}]}


def spec(mode="nearest"):
    return {"version": graph.VERSION, "entry": "owned", "nodes": {
        "owned": {"op": "owned", "inputs": {},
                  "next": {"succeeded": "pick", "empty": "owned"}},
        "pick": {"op": "select_target", "mode": mode,
                 "inputs": {"units": {"ref": "owned.units"}},
                 "next": {"succeeded": "act", "empty": "owned"}},
        "act": {"op": "engage", "inputs": {"units": {"ref": "owned.units"},
                                               "target": {"ref": "pick.target"}},
                "next": {"succeeded": "owned", "failed": "owned", "cancelled": "owned"}}}}


def configuration(tmp_path, *, team=False):
    leaf = {"type": "graph_llm", "graph": spec(), "model": "claude-haiku-5-5",
            "effort": "low", "task": "Prefer a useful public target.", "max_requests": 1}
    value = {"type": "team", "members": {
        "line": {"unit_types": ["foot"], "controller": leaf},
        "cavalry": {"unit_types": None, "controller": {"type": "llm"}}}} if team else leaf
    path = tmp_path / "controller.json"
    path.write_text(json.dumps(value))
    ledger = tmp_path / "test-ledger.jsonl"
    ledger.touch()
    config = {"policy": "configured", "controller_config": str(path), "provider": "anthropic",
              "model": "claude-haiku-5-5", "effort": "low", "budget_usd": 5, "ledger": str(ledger)}
    return path, config, value


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
