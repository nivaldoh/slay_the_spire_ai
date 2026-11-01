"""Canned model calls check author authority, public feedback, artifacts and budget accounting."""

import json
import sys
from copy import deepcopy

import pytest

from gameai.ledger import BudgetExhausted, Ledger
from gameai.llm import InvalidReply
from gameai.provenance import REPO_ROOT
from twwarhammer3.battle import configured, graph, graph_author, team

TEMPLATE = REPO_ROOT / "configs/twwarhammer3/graphs/contact-team.json"
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


def author(root, send, *, book=None, previous=None, evidence=None):
    return graph_author.generate(TEMPLATE, "Line engages; cavalry waits for contact then charges.",
                                 root / "artifact", book or ledger(root), model="claude-haiku-5-5",
                                 send=send, previous=previous, evidence=evidence)


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


def test_multi_llm_artifact_loads_with_frozen_library_and_counts_every_call(tmp_path):
    send, book = Canned(replies()), ledger(tmp_path)
    result = author(tmp_path, send, book=book)
    artifact = tmp_path / "artifact"
    assert result["status"] == "ready" and result["totals"]["calls"] == 3
    specialist = json.loads(send.requests[1]["input"][0]["content"])
    assert specialist["library"]["graph_version"] == graph.VERSION
    assert result["totals"]["usd"] == book.spent > 0
    exchanges = [json.loads(row) for row in (artifact / "calls.jsonl").read_text().splitlines()]
    assert [row["role"] for row in exchanges] == ["coordinator", "line", "cavalry"]
    assert sum(a["usd"] for row in exchanges for a in row["attempts"]) == book.spent
    for path in (artifact, artifact / "controller.json"):
        policy = configured.factory(path, {})()
        try:
            assert policy.card["artifact"]["library_sha256"] == result["library_sha256"]
            assert all(member.policy.spec == END for member in policy.members.values())
        finally:
            policy.close()


def test_revision_changes_graphs_from_only_permitted_member_evidence(tmp_path):
    author(tmp_path / "initial", Canned(replies()))
    previous = tmp_path / "initial/artifact"
    plain = completed(tmp_path / "plain", previous)
    poisoned = completed(tmp_path / "poisoned", previous, poison=True, outcome="won")
    a, b = Canned(replies(WAIT, WAIT)), Canned(replies(WAIT, WAIT))
    ra = author(tmp_path / "a", a, previous=previous, evidence=plain)
    rb = author(tmp_path / "b", b, previous=previous, evidence=poisoned)
    assert ra["status"] == rb["status"] == "ready"
    assert [r["input"] for r in a.requests] == [r["input"] for r in b.requests]
    assert "HIDDEN_" not in json.dumps(b.requests)
    assert "LINE_PRIVATE_FEEDBACK" not in json.dumps(b.requests[2])
    assert "LINE_PRIVATE_FEEDBACK" in json.dumps(b.requests[1])
    candidate = json.loads((tmp_path / "b/artifact/controller.json").read_text())
    assert all(m["controller"]["graph"] == WAIT for m in candidate["members"].values())
    original = json.loads((previous / "controller.json").read_text())
    assert graph_author.authority(candidate) == graph_author.authority(original)
    assert all(m["controller"]["graph"] == END for m in original["members"].values())
    assert rb["parent"]["controller_sha256"] == ra["parent"]["controller_sha256"]


def test_rejected_graph_attempts_are_retained_and_charged(tmp_path):
    bad = deepcopy(END)
    bad["nodes"]["end"]["op"] = "exec"
    attempts = replies(line=bad)
    send = Canned([attempts[0], attempts[1], attempts[1]])
    book = ledger(tmp_path)
    with pytest.raises(InvalidReply):
        author(tmp_path, send, book=book)
    output = tmp_path / "artifact"
    manifest = json.loads((output / "manifest.json").read_text())
    rows = [json.loads(row) for row in (output / "calls.jsonl").read_text().splitlines()]
    assert manifest["status"] == "failed" and manifest["totals"]["calls"] == 3
    assert len(rows) == 2 and len(rows[-1]["attempts"]) == 2
    assert all("unknown operation" in a["error"] for a in rows[-1]["attempts"])
    assert manifest["totals"]["usd"] == book.spent > 0
    assert not (output / "controller.json").exists()


@pytest.mark.parametrize("wrong", ["unfinished", "different_candidate", "different_library"])
def test_revision_refusals_happen_before_a_model_call(tmp_path, wrong):
    author(tmp_path / "initial", Canned(replies()))
    previous = tmp_path / "initial/artifact"
    episode = completed(tmp_path / "episode", previous)
    path = episode / "result.json"
    result = json.loads(path.read_text())
    if wrong == "unfinished":
        result.pop("engine_ending")
    elif wrong == "different_candidate":
        result["card"]["disclosure"]["configuration_sha256"] = "another"
    else:
        result["card"]["disclosure"]["artifact"]["library_sha256"] = "another"
    path.write_text(json.dumps(result))
    send = Canned([])
    with pytest.raises(ValueError):
        author(tmp_path / "revision", send, previous=previous, evidence=episode)
    assert send.requests == []


def test_artifact_tampering_or_library_change_refuses_both_play_and_revision(tmp_path, monkeypatch):
    author(tmp_path / "initial", Canned(replies()))
    output = tmp_path / "initial/artifact"
    path = output / "controller.json"
    original = path.read_bytes()
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="changed"):
        configured.factory(output, {})
    path.write_bytes(original)
    monkeypatch.setitem(graph_author.DESCRIPTIONS, "end", "Changed skill contract")
    with pytest.raises(ValueError, match="different frozen"):
        configured.factory(output / "controller.json", {})
    with pytest.raises(ValueError, match="different frozen"):
        graph_author.previous_artifact(output, graph_author.load_template(TEMPLATE),
                                      graph_author.frozen_library())


def test_budget_stop_sends_nothing_and_preserves_failed_artifact(tmp_path):
    send = Canned([])
    with pytest.raises(BudgetExhausted):
        author(tmp_path, send, book=ledger(tmp_path, 0))
    assert not send.requests
    manifest = json.loads((tmp_path / "artifact/manifest.json").read_text())
    assert manifest["status"] == "failed" and manifest["totals"].get("calls", 0) == 0


def test_coordinator_cannot_change_members_and_repairs_remain_in_the_record(tmp_path):
    wrong = json.dumps({"tasks": [{"member": "line", "task": "Do it"},
                                  {"member": "line", "task": "Twice"}]})
    good = replies()
    send = Canned([wrong, *good])
    result = author(tmp_path, send)
    assert result["status"] == "ready" and result["totals"]["calls"] == 4
    first = json.loads((tmp_path / "artifact/calls.jsonl").read_text().splitlines()[0])
    assert len(first["attempts"]) == 2 and "exactly once" in first["attempts"][0]["error"]
    assert "previous reply was invalid" in send.requests[1]["input"][0]["content"]


def test_foreign_feedback_is_refused_and_existing_artifacts_are_never_overwritten(tmp_path):
    author(tmp_path / "initial", Canned(replies()))
    previous = tmp_path / "initial/artifact"
    send = Canned([])
    with pytest.raises(FileExistsError):
        author(tmp_path / "initial", send)
    assert send.requests == []
    episode = completed(tmp_path / "episode", previous)
    path = episode / "trace.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[-2]["ack"]["results"][0]["unit"] = "cav-unit"  # line member's private recipient
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    with pytest.raises(ValueError, match="does not own"):
        author(tmp_path / "revision", send, previous=previous, evidence=episode)
    assert send.requests == []


@pytest.mark.parametrize("wrong", ["version", "library", "authority", "missing_pin"])
def test_artifact_manifest_tampering_cannot_bypass_the_file_loader(tmp_path, wrong):
    author(tmp_path, Canned(replies()))
    output = tmp_path / "artifact"
    path = output / "manifest.json"
    manifest = json.loads(path.read_text())
    if wrong == "version":
        manifest["version"] = "unsupported"
    elif wrong == "library":
        manifest["library"]["descriptions"]["end"] = "changed"
    elif wrong == "authority":
        manifest["authority"]["army_owner"] = "cavalry"
    else:
        manifest.pop("controller_sha256")
        manifest["status"] = "failed"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        configured.factory(output / "controller.json", {})


def test_author_cli_refuses_missing_ledger_before_reading_an_api_key(tmp_path, monkeypatch):
    from gameai import llm, provenance
    from twwarhammer3.__main__ import main

    monkeypatch.setattr(provenance, "committed_revision", lambda purpose, sources: "test-revision")
    def no_key(provider):
        pytest.fail("CLI read an API key before refusing the missing ledger")

    monkeypatch.setattr(llm, "api_key", no_key)
    monkeypatch.setattr(graph_author, "api_key", no_key)
    monkeypatch.setattr(sys, "argv", ["twwarhammer3", "graph-author", "--task", "public task",
                                     "--output", str(tmp_path / "output"), "--budget-usd", "5",
                                     "--ledger", str(tmp_path / "missing.jsonl")])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2 and not (tmp_path / "output").exists()


@pytest.mark.parametrize("wrong", ["no_views", "no_source", "feedback_before_view"])
def test_missing_public_context_refuses_revision_before_any_model_call(tmp_path, wrong):
    author(tmp_path / "initial", Canned(replies()))
    previous = tmp_path / "initial/artifact"
    episode = completed(tmp_path / "episode", previous)
    path = episode / "trace.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    if wrong == "no_views":
        events = []
    elif wrong == "no_source":
        events = [e for e in events if not (e.get("event") == "input"
                                           and e.get("member") == "cavalry")]
    else:
        events.insert(0, events.pop(-1))
    path.write_text("\n".join(json.dumps(row) for row in events))
    send = Canned([])
    with pytest.raises(ValueError, match="public"):
        author(tmp_path / "revision", send, previous=previous, evidence=episode)
    assert send.requests == []


@pytest.mark.parametrize("wrong", ["empty_task", "evidence_only", "previous_only",
                                  "template_type", "authority"])
def test_invalid_author_request_refuses_before_any_model_call(tmp_path, wrong):
    send = Canned([])
    kwargs = {"template_path": TEMPLATE, "task": "public task", "output": tmp_path / "new",
              "ledger": ledger(tmp_path), "model": "claude-haiku-5-5", "send": send}
    if wrong == "empty_task":
        kwargs["task"] = "  "
    elif wrong == "evidence_only":
        kwargs["evidence"] = tmp_path / "anywhere"
    elif wrong == "previous_only":
        kwargs["previous"] = tmp_path / "anywhere"
    elif wrong == "template_type":
        path = tmp_path / "bad-template.json"
        path.write_text('{"type":"hold"}')
        kwargs["template_path"] = path
    else:
        author(tmp_path / "initial", Canned(replies()))
        previous = tmp_path / "initial/artifact"
        episode = completed(tmp_path / "episode", previous)
        spec = json.loads((previous / "controller.json").read_text())
        spec["army_owner"] = "cavalry"
        path = tmp_path / "changed-authority.json"
        path.write_text(json.dumps(spec))
        kwargs.update(template_path=path, previous=previous, evidence=episode)
    with pytest.raises(ValueError):
        graph_author.generate(**kwargs)
    assert send.requests == []


@pytest.mark.parametrize("bad_task", ["", "x" * (graph_author.TASK_LIMIT + 1)])
def test_bad_coordinator_task_is_repaired_before_sending_it_to_a_specialist(tmp_path, bad_task):
    good = replies()
    bad = json.loads(good[0])
    bad["tasks"][0]["task"] = bad_task
    author(tmp_path, Canned([json.dumps(bad), *good]))
    first = json.loads((tmp_path / "artifact/calls.jsonl").read_text().splitlines()[0])
    assert first["role"] == "coordinator" and len(first["attempts"]) == 2
    assert "empty or too long" in first["attempts"][0]["error"]
