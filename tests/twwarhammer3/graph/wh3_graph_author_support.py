"""Canned model replies and synthetic episode files for graph author tests."""

import json
from copy import deepcopy

from gameai.ledger import Ledger
from twwarhammer3.battle import graph, team

END = {"version": graph.VERSION, "entry": "end", "nodes": {
    "end": {"op": "end", "inputs": {}, "next": {}}}}


WAIT = {"version": graph.VERSION, "entry": "contact", "nodes": {
    "contact": {"op": "contact", "inputs": {}, "next": {"yes": "end", "no": "contact"}},
    "end": {"op": "end", "inputs": {}, "next": {}}}}


class Canned:
    def __init__(self, replies):
        self.replies, self.requests = list(replies), []

    def __call__(self, body):
        self.requests.append(deepcopy(body))
        assert self.replies, "unexpected model call"
        text = self.replies.pop(0)
        return {"id": f"canned-{len(self.requests)}", "status": "completed",
                "usage": {"input_tokens": 100, "output_tokens": 100},
                "output": [{"type": "message", "content": [
                    {"type": "output_text", "text": text}]}]}


def replies(line=END, cavalry=END):
    return [json.dumps({"tasks": [{"member": "line", "task": "Engage visible targets."},
                                   {"member": "cavalry", "task": "Wait, then charge in melee."}]}),
            json.dumps({"graph_json": json.dumps(line)}),
            json.dumps({"graph_json": json.dumps(cavalry)})]


def ledger(root, budget=5):
    root.mkdir(parents=True, exist_ok=True)
    path = root / "synthetic-spend.jsonl"
    path.touch()
    return Ledger(path, budget, must_exist=True)


def completed(root, artifact, *, poison=False, outcome="lost"):
    root.mkdir(parents=True)
    candidate = json.loads((artifact / "controller.json").read_text())
    manifest = json.loads((artifact / "manifest.json").read_text())
    result = {"status": outcome, "engine_ending": {"result": outcome}, "card": {"disclosure": {
        "configuration_sha256": graph.digest(candidate),
        "artifact": {"library_sha256": manifest["library_sha256"]}}}}
    raw = {"battle": "b", "seq": 1, "time_ms": 10000, "phase": "Deployed",
           "friendly": [
               {"id": "line-unit", "type": team.SWORD, "men": 90, "x": 0, "z": 0,
                "state": [], "command_queue": [{"type": "move", "x": 10, "z": 0}]},
               {"id": "cav-unit", "type": team.KNIGHT, "men": 45, "x": 10, "z": 0,
                "state": [], "command_queue": [{"type": "move", "x": 20, "z": 0}]}],
           "enemy": [{"id": "enemy", "type": team.SWORD, "men": 90, "x": 30, "z": 0,
                      "state": ["melee"]}]}
    if poison:
        for key in ("evaluation", "final", "setup", "native"):
            raw[key] = {"secret": f"HIDDEN_{key}"}
        raw["friendly"][0].update(target="invisible", target_dead="HIDDEN_target")
        result["final"] = {"secret": "HIDDEN_result"}
    events = [{"kind": "team", "event": "input", "member": name,
               "observation": team.project(raw, {uid})}
              for name, uid in (("line", "line-unit"), ("cavalry", "cav-unit"))]
    # Poison already-projected views too, so the author cannot trust a saved projection blindly.
    if poison:
        for event in events:
            event["observation"]["evaluation"] = {"secret": "HIDDEN_projected"}
            event["observation"]["allies"][0]["command_queue"] = "HIDDEN_ally_queue"
    events.extend([
        {"kind": "decision", "seq": 2, "behavior": {"member": "cavalry", "source_seq": 1},
         "orders": [{"type": "attack", "unit": "cav-unit", "target": "enemy"}]},
        {"kind": "team", "event": "feedback", "member": "line", "ack": {
            "results": [{"index": 1, "unit": "line-unit", "ok": False,
                         "error": "LINE_PRIVATE_FEEDBACK"}]}},
        {"kind": "team", "event": "feedback", "member": "cavalry", "ack": {
            "results": [{"index": 1, "unit": "cav-unit", "ok": True}]}}])
    (root / "result.json").write_text(json.dumps(result))
    (root / "trace.jsonl").write_text("\n".join(json.dumps(row) for row in events) + "\n")
    return root
