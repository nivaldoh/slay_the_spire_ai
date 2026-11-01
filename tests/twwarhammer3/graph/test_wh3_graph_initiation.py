"""Owner-approved temporary initiation check: start the fight, allow waiting roles."""
import json
import sys
from copy import deepcopy

import pytest
from test_wh3_graph_author import END, WAIT, Canned, completed, ledger, replies

from gameai.llm import InvalidReply
from gameai.provenance import REPO_ROOT
from twwarhammer3 import __main__ as cli
from twwarhammer3.battle import graph, graph_author, graph_initiation, team

TEMPLATE = REPO_ROOT / "configs/twwarhammer3/graphs/contact-team.json"
GOOD = json.loads((TEMPLATE.parent / "contact-line.json").read_text())
STALLED = deepcopy(GOOD)
STALLED["nodes"]["target"]["mode"] = "engaged"


def public_start():
    return {"schema": "wh3-v1", "battle": "start", "seq": 1, "phase": "Deployed",
            "time_ms": 5300, "speed": 1,
            "friendly": [{"id": "f1", "type": team.SWORD, "men": 90,
                          "x": 0, "z": 0, "state": []}],
            "allies": [{"id": "f2", "type": team.KNIGHT, "men": 45,
                        "x": 10, "z": 0, "state": []}],
            "enemy": [{"id": "e1", "men": 90, "x": 30, "z": 0, "state": []},
                      {"id": "e2", "men": 90, "x": 40, "z": 0, "state": []}]}


def starting_episode(root, *, poison=False):
    root.mkdir(parents=True)
    view = public_start()
    if poison:
        view["evaluation"] = {"enemy": [{"id": "secret", "state": ["melee"]}]}
        view["setup"] = {"secret": "HIDDEN_setup"}
        view["final"] = {"result": "HIDDEN_result"}
        view["allies"][0]["command_queue"] = "HIDDEN_ally_queue"
    later = deepcopy(view)
    later["enemy"][0]["state"] = ["melee"]
    later["seq"] = 2
    rows = [{"kind": "team", "event": "input", "member": "line", "observation": v}
            for v in (view, later)]
    (root / "trace.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    return root


def generate(root, send, start, *, previous=None, evidence=None, initiators=("line",)):
    return graph_author.generate(TEMPLATE, "Line engages; cavalry waits for contact then charges.",
                                 root / "artifact", ledger(root), model="claude-haiku-5-5",
                                 starting_episode=start, initiators=initiators, send=send,
                                 previous=previous, evidence=evidence)


@pytest.mark.parametrize("spec", [STALLED, WAIT, END])
def test_initiator_rejects_existing_melee_selection_contact_wait_and_end(spec):
    with pytest.raises(ValueError, match="no attack route before contact"):
        graph_initiation.check(spec, public_start())


def test_nearest_selection_supplies_an_owned_visible_attack_before_contact():
    report = graph_initiation.check(GOOD, public_start())
    assert len(report["attack_orders"]) == 1
    assert {key: report["attack_orders"][0][key] for key in ("unit", "type", "target", "mode")} == {
        "unit": "f1", "type": "attack", "target": "e1", "mode": "melee"}
    assert [row["node"] for row in report["path"]] == ["owned", "target", "engage"]
    assert report["graph_sha256"] == graph.digest(GOOD)


def test_contact_no_branch_can_lead_to_attack_while_yes_branch_waits():
    spec = deepcopy(GOOD)
    spec["entry"] = "contact"
    spec["nodes"]["contact"] = {"op": "contact", "inputs": {},
                                 "next": {"no": "owned", "yes": "contact"}}
    assert graph_initiation.check(spec, public_start())["attack_orders"]


def test_move_before_attack_is_a_possible_route_not_a_completion_witness():
    spec = deepcopy(GOOD)
    spec["nodes"]["owned"]["next"]["succeeded"] = "move"
    spec["nodes"]["move"] = {"op": "move", "inputs": {
        "units": {"ref": "owned.units"}, "point": {"x": 10, "z": 0}},
        "next": {"succeeded": "target", "failed": "owned", "cancelled": "owned"}}
    report = graph_initiation.check(spec, public_start())
    assert any(row["node"] == "move" for row in report["path"])
    assert "witness" not in report and "completion" not in report


@pytest.mark.parametrize("op", ["charge", "shoot"])
def test_charge_before_melee_and_shoot_without_ammo_cannot_start(op):
    spec = deepcopy(GOOD)
    spec["nodes"]["engage"]["op"] = op
    with pytest.raises(ValueError, match="no attack route"):
        graph_initiation.check(spec, public_start())


def test_shooting_out_of_range_has_an_attack_route_without_claiming_a_shot():
    spec, view = deepcopy(GOOD), public_start()
    spec["nodes"]["engage"]["op"] = "shoot"
    view["friendly"][0].update(ammo=10, range=10)
    report = graph_initiation.check(spec, view)
    assert report["attack"]["op"] == "shoot"
    assert "witness" not in report and "completion" not in report


@pytest.mark.parametrize("wrong", ["not_owned", "hidden_target"])
def test_literal_foreign_unit_or_hidden_target_is_not_an_attack_route(wrong):
    spec = deepcopy(END)
    spec["entry"] = "attack"
    spec["nodes"]["attack"] = {"op": "engage", "inputs": {
        "units": ["f2" if wrong == "not_owned" else "f1"],
        "target": "secret" if wrong == "hidden_target" else "e1"},
        "next": {status: "end" for status in ("succeeded", "failed", "cancelled")}}
    with pytest.raises(ValueError, match="no attack route"):
        graph_initiation.check(spec, public_start())


@pytest.mark.parametrize("wrong", ["contact", "no_enemy", "no_owned", "not_deployed"])
def test_unusable_starting_view_is_rejected_before_authors_run(tmp_path, wrong):
    start = starting_episode(tmp_path / "start")
    rows = [json.loads(line) for line in (start / "trace.jsonl").read_text().splitlines()]
    view = rows[0]["observation"]
    if wrong == "contact":
        view["enemy"][0]["state"] = ["melee"]
    elif wrong == "not_deployed":
        view["phase"] = "Deployment"
    else:
        view["enemy" if wrong == "no_enemy" else "friendly"] = []
    (start / "trace.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    send = Canned([])
    with pytest.raises(ValueError, match="starting view|active owned"):
        generate(tmp_path / "author", send, start)
    assert not send.requests


@pytest.mark.parametrize("names", [("missing",), ("line", "line"), ("cavalry",)])
def test_bad_declarations_and_missing_first_member_input_refuse_before_api(tmp_path, names):
    start = starting_episode(tmp_path / "start")
    send = Canned([])
    with pytest.raises(ValueError, match="distinct|missing an initiator"):
        generate(tmp_path / "author", send, start, initiators=names)
    assert not send.requests


@pytest.mark.parametrize("with_episode", [True, False])
def test_starting_episode_and_initiator_are_required_together(tmp_path, with_episode):
    start = starting_episode(tmp_path / "start") if with_episode else None
    send = Canned(replies(GOOD, WAIT))
    with pytest.raises(ValueError, match="together"):
        graph_author.generate(TEMPLATE, "Start combat", tmp_path / "author", ledger(tmp_path),
                              model="claude-haiku-5-5", starting_episode=start,
                              initiators=() if with_episode else ("line",), send=send)
    assert not send.requests


def test_stalled_specialist_is_repaired_once_and_waiting_cavalry_is_allowed(tmp_path):
    first, corrected = replies(STALLED, WAIT), replies(GOOD, WAIT)
    send = Canned([first[0], first[1], corrected[1], corrected[2]])
    result = generate(tmp_path / "author", send, starting_episode(tmp_path / "start"))
    assert result["status"] == "ready" and result["totals"]["calls"] == 4
    specialist = send.requests[2]["input"][0]["content"]
    assert "no attack route before contact" in specialist
    assert "must_initiate_before_contact" not in send.requests[3]["input"][0]["content"]
    output = tmp_path / "author/artifact"
    candidate, _ = graph_author.load_artifact(output)
    assert candidate["members"]["line"]["controller"]["graph"] == GOOD
    assert candidate["members"]["cavalry"]["controller"]["graph"] == WAIT
    assert set(result["initiation_check"]["reports"]) == {"line"}
    rows = [json.loads(line) for line in (output / "calls.jsonl").read_text().splitlines()]
    assert len(rows[1]["attempts"]) == 2
    assert sum(a["usd"] for row in rows for a in row["attempts"]) == result["totals"]["usd"]


def test_stalled_repair_is_not_ready_and_does_not_get_an_extra_retry(tmp_path):
    first = replies(STALLED, WAIT)
    send = Canned([first[0], first[1], first[1]])
    with pytest.raises(InvalidReply):
        generate(tmp_path / "author", send, starting_episode(tmp_path / "start"))
    path = tmp_path / "author/artifact"
    assert not (path / "controller.json").exists()
    manifest = json.loads((path / "manifest.json").read_text())
    assert manifest["status"] == "failed" and manifest["totals"]["calls"] == 3


def test_first_view_is_projected_and_private_changes_do_not_change_model_inputs(tmp_path):
    plain, poisoned = Canned(replies(GOOD, WAIT)), Canned(replies(GOOD, WAIT))
    a = generate(tmp_path / "a", plain, starting_episode(tmp_path / "plain"))
    b = generate(tmp_path / "b", poisoned, starting_episode(tmp_path / "poison", poison=True))
    assert [r["input"] for r in plain.requests] == [r["input"] for r in poisoned.requests]
    assert "HIDDEN_" not in json.dumps(poisoned.requests)
    assert a["initiation_check"]["views"] == b["initiation_check"]["views"]
    assert b["initiation_check"]["views"]["line"]["seq"] == 1
    assert all("melee" not in u["state"] for u in b["initiation_check"]["views"]["line"]["enemy"])


@pytest.mark.parametrize("wrong", ["report", "version", "checker", "members", "duplicates",
                                   "foreign_view"])
def test_modified_initiation_proof_refuses_artifact_load(tmp_path, wrong):
    generate(tmp_path / "author", Canned(replies(GOOD, WAIT)), starting_episode(tmp_path / "start"))
    output = tmp_path / "author/artifact"
    path = output / "manifest.json"
    manifest = json.loads(path.read_text())
    proof = manifest["initiation_check"]
    if wrong == "report":
        proof["reports"]["line"]["graph_sha256"] = "wrong"
    elif wrong == "version":
        proof["version"] = "unknown"
    elif wrong == "checker":
        proof["checker_sha256"] = "unknown"
    elif wrong == "members":
        proof["initiators"] = []
    elif wrong == "duplicates":
        proof["initiators"].append("line")
    else:
        view = proof["views"]["line"]
        view["friendly"] += view.pop("allies")
        view["allies"] = []
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="initiation"):
        graph_author.load_artifact(output)


def test_proof_recomputation_itself_refuses_misowned_views(tmp_path):
    composition = graph_author.load_template(TEMPLATE)
    record = graph_initiation.starting_views(starting_episode(tmp_path / "start"),
                                            composition, ("line",))
    view = record["views"]["line"]
    view["friendly"] += view.pop("allies")
    view["allies"] = []
    with pytest.raises(ValueError, match="misowned"):
        graph_initiation.reports(composition, record)


def test_revision_rechecks_the_declared_initiator_and_preserves_the_parent(tmp_path):
    start = starting_episode(tmp_path / "start")
    generate(tmp_path / "initial", Canned(replies(GOOD, WAIT)), start)
    parent = tmp_path / "initial/artifact"
    before = (parent / "controller.json").read_bytes()
    evidence = completed(tmp_path / "whole", parent)
    first, fixed = replies(STALLED, WAIT), replies(GOOD, WAIT)
    result = generate(tmp_path / "revision", Canned([first[0], first[1], fixed[1], fixed[2]]),
                      start, previous=parent, evidence=evidence)
    assert result["status"] == "ready" and result["totals"]["calls"] == 4
    assert (parent / "controller.json").read_bytes() == before
    assert result["parent"]["controller_sha256"]


def test_revision_cannot_drop_initiation_check_by_omitting_flags(tmp_path):
    generate(tmp_path / "initial", Canned(replies(GOOD, WAIT)),
             starting_episode(tmp_path / "start"))
    parent = tmp_path / "initial/artifact"
    evidence = completed(tmp_path / "whole", parent)
    first = replies(STALLED, WAIT)
    send = Canned([first[0], first[1], first[1]])
    with pytest.raises(InvalidReply):
        graph_author.generate(TEMPLATE, "Same task", tmp_path / "revision", ledger(tmp_path),
                              model="claude-haiku-5-5", previous=parent,
                              evidence=evidence, send=send)
    manifest = json.loads((tmp_path / "revision/manifest.json").read_text())
    assert manifest["initiation_check"]["initiators"] == ["line"]
    assert manifest["status"] == "failed"


def test_revision_cannot_reassign_the_initiator_to_the_waiting_member(tmp_path):
    start = starting_episode(tmp_path / "start")
    generate(tmp_path / "initial", Canned(replies(GOOD, WAIT)), start)
    parent = tmp_path / "initial/artifact"
    evidence = completed(tmp_path / "whole", parent)
    with (start / "trace.jsonl").open("a") as stream:
        stream.write(json.dumps({"kind": "team", "event": "input", "member": "cavalry",
                                 "observation": public_start()}) + "\n")
    send = Canned(replies(GOOD, WAIT))
    with pytest.raises(ValueError, match="preserve.*initiators"):
        generate(tmp_path / "revision", send, start, previous=parent,
                 evidence=evidence, initiators=("cavalry",))
    assert not send.requests


def test_member_starting_views_from_different_battles_are_not_combined(tmp_path):
    start = starting_episode(tmp_path / "start")
    raw = public_start()
    raw["battle"] = "other-battle"
    with (start / "trace.jsonl").open("a") as stream:
        stream.write(json.dumps({"kind": "team", "event": "input", "member": "cavalry",
                                 "observation": raw}) + "\n")
    send = Canned(replies(GOOD, WAIT))
    with pytest.raises(ValueError, match="same battle"):
        generate(tmp_path / "author", send, start, initiators=("line", "cavalry"))
    assert not send.requests


def test_cli_forwards_the_public_start_and_explicit_initiator(tmp_path, monkeypatch):
    start, book = starting_episode(tmp_path / "start"), ledger(tmp_path)
    captured = {}

    def fake_generate(*args, **kwargs):
        captured.update(kwargs)
        return {"status": "ready", "totals": {}}

    monkeypatch.setattr(graph_author, "generate", fake_generate)
    monkeypatch.setattr("gameai.provenance.committed_revision", lambda *args: "test")
    monkeypatch.setattr(sys, "argv", ["wh3", "graph-author", "--task", "Start combat",
                                     "--output", str(tmp_path / "artifact"), "--budget-usd", "5",
                                     "--ledger", str(book.path), "--starting-episode", str(start),
                                     "--initiator", "line"])
    assert cli.main() == 0
    assert captured["starting_episode"] == start and captured["initiators"] == ["line"]


def test_rejects_artillery_wait_without_an_attack_order():
    spec, view = deepcopy(GOOD), public_start()
    spec["nodes"]["engage"]["op"] = "shoot"
    view["friendly"][0].update(ammo=10, range=10, **{"class": "artillery"})
    with pytest.raises(ValueError, match="no attack route"):
        graph_initiation.check(spec, view)


def test_rejects_missing_time_before_any_author_call(tmp_path):
    start = starting_episode(tmp_path / "start")
    rows = [json.loads(line) for line in (start / "trace.jsonl").read_text().splitlines()]
    del rows[0]["observation"]["time_ms"]
    (start / "trace.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    send = Canned(replies(GOOD, WAIT))
    with pytest.raises(ValueError, match="time_ms"):
        generate(tmp_path / "author", send, start)
    assert not send.requests


@pytest.mark.parametrize("remove", [True, False])
def test_removed_initiation_proof_cannot_disable_revision_requirement(tmp_path, remove):
    generate(tmp_path / "initial", Canned(replies(GOOD, WAIT)),
             starting_episode(tmp_path / "start"))
    parent = tmp_path / "initial/artifact"
    evidence = completed(tmp_path / "whole", parent)
    path = parent / "manifest.json"
    value = json.loads(path.read_text())
    if remove:
        del value["initiation_check"]
    else:
        value["initiation_check"] = None
    path.write_text(json.dumps(value))
    send = Canned(replies(STALLED, WAIT))
    with pytest.raises(ValueError, match="initiation"):
        graph_author.generate(TEMPLATE, "Same task", tmp_path / "revision", ledger(tmp_path),
                              model="claude-haiku-5-5", previous=parent,
                              evidence=evidence, send=send)
    assert not send.requests


def test_changed_start_source_cannot_keep_an_old_proof(tmp_path):
    generate(tmp_path / "author", Canned(replies(GOOD, WAIT)),
             starting_episode(tmp_path / "start"))
    output = tmp_path / "author/artifact"
    path = output / "manifest.json"
    value = json.loads(path.read_text())
    value["initiation_check"]["source"]["trace_sha256"] = "fabricated"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="initiation proof"):
        graph_author.load_artifact(output)


@pytest.mark.parametrize(("field", "bad"), [("battle", ""), ("seq", -1), ("time_ms", -1)])
def test_invalid_start_identity_refuses_before_authors(tmp_path, field, bad):
    start = starting_episode(tmp_path / "start")
    rows = [json.loads(line) for line in (start / "trace.jsonl").read_text().splitlines()]
    rows[0]["observation"][field] = bad
    (start / "trace.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    send = Canned(replies(GOOD, WAIT))
    with pytest.raises(ValueError, match="battle identity, seq and time_ms"):
        generate(tmp_path / "author", send, start)
    assert not send.requests


def test_downgrading_version_cannot_hide_new_initiation_fields(tmp_path):
    generate(tmp_path / "author", Canned(replies(GOOD, WAIT)),
             starting_episode(tmp_path / "start"))
    output = tmp_path / "author/artifact"
    path = output / "manifest.json"
    value = json.loads(path.read_text())
    value["version"] = graph_author.LEGACY_VERSION
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="legacy artifact"):
        graph_author.load_artifact(output)


@pytest.mark.parametrize(("field", "bad"), [("x", "not-a-coordinate"), ("x", float("nan")),
    ("z", float("inf")), ("ammo", "many"), ("range", "far")])
def test_invalid_start_geometry_refuses_before_authors(tmp_path, field, bad):
    start = starting_episode(tmp_path / "start")
    rows = [json.loads(line) for line in (start / "trace.jsonl").read_text().splitlines()]
    rows[0]["observation"]["friendly"][0][field] = bad
    (start / "trace.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    send = Canned(replies(GOOD, WAIT))
    with pytest.raises(ValueError, match="starting unit data"):
        generate(tmp_path / "author", send, start)
    assert not send.requests


def test_proof_recomputation_itself_refuses_repeated_members(tmp_path):
    composition = graph_author.load_template(TEMPLATE)
    record = graph_initiation.starting_views(starting_episode(tmp_path / "start"),
                                            composition, ("line",))
    record["initiators"].append("line")
    with pytest.raises(ValueError, match="repeated members"):
        graph_initiation.reports(composition, record)


def test_direct_checker_refuses_invalid_unit_data_even_for_melee_route():
    view = public_start()
    view["friendly"][0]["ammo"] = "many"
    with pytest.raises(ValueError, match="starting unit data"):
        graph_initiation.check(GOOD, view)


def test_invalid_unit_identity_refuses_before_public_projection(monkeypatch):
    composition, raw = graph_author.load_template(TEMPLATE), public_start()
    raw["friendly"][0]["target"] = []

    def forbidden_projection(*args, **kwargs):
        raise AssertionError("invalid unit identity reached public projection")

    monkeypatch.setattr(team, "project", forbidden_projection)
    with pytest.raises(ValueError, match="starting unit data"):
        graph_initiation.member_view(raw, composition, "line")
