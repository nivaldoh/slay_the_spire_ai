"""The branch audit's table, from attempt records alone (checkpoint-rl-plan.md, stage 2)."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from twwarhammer3.battle import audit, checkpoint
from twwarhammer3.battle.candidates import candidates

CONTEXT = {"phase": "Deployed", "time_ms": 210100, "terrain": {"bounds": {
    "min_x": -512, "max_x": 512, "min_z": -512, "max_z": 512}},
    "friendly": [{"id": "f1", "class": "infantry", "range": 0, "ammo": 0, "men": 90, "x": 0,
                  "z": 0, "state": []},
                 {"id": "f2", "class": "missile", "range": 145, "ammo": 900, "men": 68, "x": 10,
                  "z": 0, "state": []}],
    "enemy": [{"id": "e1", "men": 80, "x": 40, "z": 0, "state": []}]}


def write_audit(tmp_path: Path, outcomes: dict, repeat_ending="won", refused=()):
    tmp_path.mkdir(parents=True, exist_ok=True)
    record = tmp_path / "record.json"
    record.write_text(json.dumps({"root": "root", "tick": 2100}))
    output = tmp_path / "audit"
    output.mkdir()
    plan = {"name": "a", "rungs": [{"record": str(record)}], "repeat": ["attack_nearest"]}
    (output / "plan.json").write_text(json.dumps(plan))
    listed = candidates(CONTEXT)["candidates"]
    jobs = [(None, 0)] + [(c, 0) for c in listed] + [(listed[1], 1)]
    for index, (candidate, repeat) in enumerate(jobs):
        run = output / f"attempt-{index:04d}"
        (run / "native").mkdir(parents=True)
        result = "won" if candidate is None else outcomes[candidate["id"]]
        if repeat:
            result = repeat_ending
        attempt = {"plan": {"record": str(record)}, "status": result,
                   "engine_ending": {"result": result, "battle_ms": 298000}}
        if candidate is not None:
            attempt["plan"].update(candidate=candidate["id"], repeat=repeat, injection={
                "orders": candidate["orders"], "context": CONTEXT, "context_hash": "h"})
            attempt["attribution"] = {"applied_ms": 210400, "status": None}
            if candidate["id"] in refused:
                attempt.update(status="injection_failed", attribution={
                    "clause": "results", "reason": {"refused": [{"ok": False}]}})
        attempt["reward"] = checkpoint.reward(attempt) if attempt["status"] != (
            "injection_failed") else None
        (run / "attempt.json").write_text(json.dumps(attempt))
        rows = [{"event": "tick", "tick": t, "checksum": t + (result == "lost")}
                for t in range(2101, 2990)]
        (run / "native/native.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        (run / "observations.jsonl").write_text("")
    return output


OUTCOMES = {"noop": "won", "attack_nearest": "won", "rush_nearest": "lost",
            "fall_back_f2": "lost", "charge_f1": "won"}


def test_a_rung_with_winners_and_losers_and_a_matching_repeat_passes(tmp_path):
    table = audit.table(write_audit(tmp_path, OUTCOMES))
    rung = table["rungs"][0]
    assert table["pass"] and rung["rewards"] == [1, 1, 0, 0, 1]
    assert [c["id"] for c in rung["candidates"]] == list(OUTCOMES)
    assert rung["launches"] == 7 and rung["statuses"] == {"won": 4, "lost": 2}
    assert rung["repeats"][0]["match"] and rung["reference"].endswith("attempt-0000")


def test_a_flat_rung_a_repeat_that_differs_and_a_refusal_are_reported(tmp_path):
    flat = audit.table(write_audit(tmp_path / "flat", {k: "won" for k in OUTCOMES}))
    assert not flat["pass"] and not flat["rungs"][0]["verdict"]["winner_and_loser"]
    differs = audit.table(write_audit(tmp_path / "differs", OUTCOMES, repeat_ending="lost"))
    assert not differs["rungs"][0]["verdict"]["repeats_match"]
    refused = audit.table(write_audit(tmp_path / "refused", OUTCOMES, refused=("charge_f1",)))
    rung = refused["rungs"][0]
    assert rung["refused"] == ["charge_f1"] and len(rung["candidates"]) == 4
    assert rung["verdict"]["applied_or_refused"] and refused["pass"]


# Pattern: Gymnasium tests/vector/test_async_vector_env.py, test_async_vector_subenv_error:
# inject a controlled failure and check the caller-visible error.
def launcher_case(tmp_path, monkeypatch, *, reference_status="won", attempt_status="won"):
    record, reference = tmp_path / "record.json", tmp_path / "reference"
    record.write_text(json.dumps({"root": "root", "tick": 2100}))
    reference.mkdir()
    (reference / "attempt.json").write_text(json.dumps({
        "status": reference_status,
        "engine_ending": ({"result": reference_status}
                          if reference_status in ("won", "lost", "draw") else None),
    }))
    plan = {"name": "a", "rungs": [{"record": str(record), "reference": str(reference)}],
            "repeat": [], "limits": {}}
    calls = []

    def inject(reference, record, orders, request, tick):
        calls.append(("inject", request))
        return {"context": CONTEXT, "orders": orders}

    def restore(record, settings, directory):
        calls.append(("restore", settings, directory))
        return {"status": attempt_status, "reason": "controlled restore result"}

    def rebuild(output):
        calls.append(("table", output))
        return {"table": "opaque reconstruction result"}

    def no_live_restore():
        raise AssertionError("offline test reached the live restore lock")

    monkeypatch.setattr(checkpoint.runtime, "RuntimeLock", no_live_restore)
    monkeypatch.setattr(checkpoint, "injection_for", inject)
    monkeypatch.setattr(checkpoint, "restore_episode", restore)
    monkeypatch.setattr(audit, "table", rebuild)
    return plan, tmp_path / "output", calls


def test_launcher_refuses_an_unscored_reference_before_any_attempt(tmp_path, monkeypatch):
    plan, output, calls = launcher_case(tmp_path, monkeypatch, reference_status="infrastructure")

    with pytest.raises(RuntimeError, match="reference.*has no engine ending"):
        audit.audit(plan, output)

    assert calls == []
    assert not (output / "table.json").exists()


@pytest.mark.parametrize("status", ["restore_failure", "restore_fault", "infrastructure",
                                    "interrupted"])
def test_launcher_stops_after_its_first_restore_failure(tmp_path, monkeypatch, status):
    plan, output, calls = launcher_case(tmp_path, monkeypatch, attempt_status=status)

    with pytest.raises(RuntimeError, match=f"{status}.*controlled restore result") as error:
        audit.audit(plan, output)

    restores = [call for call in calls if call[0] == "restore"]
    assert len(restores) == 1
    assert str(restores[0][2]) in str(error.value)
    assert calls[-1][0] == "restore"
    assert not (output / "table.json").exists()


# JUDGEMENT?: Scored-reference pairs — Codex, 2026-10-31: exercise every scored reference
# against scored attempts and injection failure; selected pairs are the alternative.
# Component evidence rests on this matrix; live restore and attribution remain unverified.
@pytest.mark.parametrize("reference_status", ["won", "lost", "draw"])
@pytest.mark.parametrize("status", ["won", "lost", "draw", "injection_failed"])
def test_launcher_completes_allowed_attempts_and_the_declared_repeat(
    tmp_path, monkeypatch, reference_status, status
):
    plan, output, calls = launcher_case(tmp_path, monkeypatch,
                                       reference_status=reference_status, attempt_status=status)
    listed = candidates(CONTEXT)["candidates"]
    plan["repeat"] = [listed[1]["id"]]

    result = audit.audit(plan, output)

    settings = [call[1] for call in calls if call[0] == "restore"]
    actual = [(s["candidate"], s["repeat"], json.dumps(s["injection"]["orders"], sort_keys=True))
              for s in settings]
    expected = [(c["id"], repeat, json.dumps(c["orders"], sort_keys=True))
                for c, repeat in ([(c, 0) for c in listed] + [(listed[1], 1)])]
    # Compare completeness, identity and multiplicity while permitting job reordering.
    assert sorted(actual) == sorted(expected)
    assert calls[-1] == ("table", output)
    assert sum(call[0] == "table" for call in calls) == 1
    assert result == {"table": "opaque reconstruction result"}
    assert json.loads((output / "table.json").read_text()) == result


# Gymnasium's controlled-failure pattern above; these cases keep audit.table real.
# Two distinct library paths share a tick to expose identity mistakes without testing a grid.
def reference_routing_case(
    tmp_path, monkeypatch, *, supplied, reference_status, later_reference_status=None
):
    records, rungs, references, reference_statuses = {}, [], {}, {}
    supplied_bytes, restores, injections = {}, [], []
    output = tmp_path / "audit"

    def write_attempt(record_path, settings, directory, status):
        directory.mkdir(parents=True)
        attempt = {"plan": {**settings, "record": str(record_path)}, "status": status,
                   "engine_ending": ({"result": status}
                                     if status in ("won", "lost", "draw") else None)}
        attempt["reward"] = checkpoint.reward(attempt) if attempt["engine_ending"] else None
        (directory / "attempt.json").write_text(json.dumps(attempt))
        return attempt

    for index in range(2):
        record_path = tmp_path / f"record-{index}.json"
        records[record_path] = {"root": "root", "tick": 2100, "name": f"save-{index}"}
        record_path.write_text(json.dumps(records[record_path]))
        reference_statuses[record_path] = (later_reference_status
            if index and later_reference_status is not None else reference_status)
        rung = {"record": str(record_path)}
        if supplied:
            reference = tmp_path / f"reference-{index}"
            write_attempt(record_path, {}, reference, reference_statuses[record_path])
            references[record_path] = reference
            supplied_bytes[reference] = (reference / "attempt.json").read_bytes()
            rung["reference"] = str(reference)
        rungs.append(rung)
    by_name = {record["name"]: path for path, record in records.items()}

    def restore(record_path, settings, directory):
        assert not directory.exists(), "attempt directory must be fresh"
        if "injection" in settings:
            assert record_path in references, "candidate started before its reference"
            assert settings["reference"] == str(references[record_path]), "wrong restore reference"
            status = "won"
        else:
            assert record_path not in references, "unnecessary reference restore"
            references[record_path] = directory
            status = reference_statuses[record_path]
        restores.append((record_path, directory, "injection" in settings))
        return write_attempt(record_path, settings, directory, status)

    def inject(reference, record, orders, request, tick):
        record_path = by_name[record["name"]]
        assert record_path in references, "reference was not created before its probe"
        assert reference == references[record_path], "wrong injection/probe reference"
        assert record == records[record_path]
        injections.append((record_path, reference, request))
        return {"context": CONTEXT, "context_hash": checkpoint.digest(CONTEXT), "orders": orders}

    def no_live_restore():
        raise AssertionError("offline reference test reached the live restore lock")

    monkeypatch.setattr(checkpoint.runtime, "RuntimeLock", no_live_restore)
    monkeypatch.setattr(checkpoint, "restore_episode", restore)
    monkeypatch.setattr(checkpoint, "injection_for", inject)
    return SimpleNamespace(plan={"name": "routing", "rungs": rungs, "repeat": [], "limits": {}},
                           output=output, records=records, references=references,
                           supplied_bytes=supplied_bytes, restores=restores, injections=injections)


@pytest.mark.parametrize("supplied", [False, True], ids=["generated", "supplied"])
@pytest.mark.parametrize("reference_status", ["won", "lost", "draw"])
def test_each_rung_uses_its_own_reference_without_overwriting_attempts(
    tmp_path, monkeypatch, supplied, reference_status
):
    case = reference_routing_case(tmp_path, monkeypatch, supplied=supplied,
                                  reference_status=reference_status)

    result = audit.audit(case.plan, case.output)

    rungs = {Path(rung["record"]): rung for rung in result["rungs"]}
    assert len(result["rungs"]) == len(rungs) == len(case.records) == 2
    assert len(set(case.references.values())) == 2
    assert len({directory for _, directory, _ in case.restores}) == len(case.restores)
    listed = candidates(CONTEXT)["candidates"]
    for record_path in case.records:
        reference = case.references[record_path]
        assert Path(rungs[record_path]["reference"]) == reference
        reference_runs = [d for p, d, injected in case.restores
                          if p == record_path and not injected]
        assert reference_runs == ([] if supplied else [reference])
        candidate_runs = {d for p, d, injected in case.restores if p == record_path and injected}
        assert {Path(row["attempt"]) for row in rungs[record_path]["attempts"]} == candidate_runs
        assert len(candidate_runs) == len(listed)
        calls = [request for p, _, request in case.injections if p == record_path]
        assert calls[0] == "probe" and calls.count("probe") == 1
        assert len(calls) == len(listed) + 1
    for reference, original in case.supplied_bytes.items():
        assert (reference / "attempt.json").read_bytes() == original
    assert json.loads((case.output / "table.json").read_text()) == result


@pytest.mark.parametrize("supplied", [False, True], ids=["generated", "supplied"])
@pytest.mark.parametrize("status", ["restore_failure", "restore_fault", "infrastructure",
                                    "interrupted", "stopped", "injection_failed"])
def test_bad_reference_stops_before_candidates_or_the_next_rung(
    tmp_path, monkeypatch, supplied, status
):
    case = reference_routing_case(tmp_path, monkeypatch, supplied=supplied, reference_status=status)

    with pytest.raises(RuntimeError, match="reference.*has no engine ending"):
        audit.audit(case.plan, case.output)

    assert case.injections == []
    assert len(case.restores) == (0 if supplied else 1)
    assert all(not injected for _, _, injected in case.restores)
    assert not (case.output / "table.json").exists()
    for reference, original in case.supplied_bytes.items():
        assert (reference / "attempt.json").read_bytes() == original


@pytest.mark.parametrize("supplied", [False, True], ids=["generated", "supplied"])
def test_a_bad_later_reference_is_checked_after_the_first_rung(tmp_path, monkeypatch, supplied):
    case = reference_routing_case(tmp_path, monkeypatch, supplied=supplied,
                                  reference_status="won", later_reference_status="infrastructure")
    first, second = case.records

    with pytest.raises(RuntimeError, match="reference.*has no engine ending") as error:
        audit.audit(case.plan, case.output)

    listed = candidates(CONTEXT)["candidates"]
    assert str(case.references[second]) in str(error.value)
    assert {path for path, _, _ in case.injections} == {first}
    assert len(case.injections) == len(listed) + 1
    candidate_runs = [path for path, _, injected in case.restores if injected]
    assert candidate_runs == [first] * len(listed)
    assert sum(path == second for path, _, _ in case.restores) == (0 if supplied else 1)
    assert not (case.output / "table.json").exists()
