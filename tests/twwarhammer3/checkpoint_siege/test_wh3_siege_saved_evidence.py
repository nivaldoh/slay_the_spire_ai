"""The siege check's case verdict (assess_case) on a copy of its saved passing evidence.

The other siege tests cover the comparison and the witnesses; this one runs assess_case, which
combines them, on the capital-attacker post-spell runs of runs/twwarhammer3/siege-final-20261025b
(the agreed check's passing evidence, docs/agreed-checks.md), then plants one wrong value per
case in a fresh copy. It covers the clauses planted below, not the spell witness. runs/ is
local, so the test skips without that evidence.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_wh3_checkpoint_siege as siege  # noqa: E402

from gameai.provenance import sha256  # noqa: E402

EVIDENCE = (Path(__file__).resolve().parents[3]
            / "runs/twwarhammer3/siege-final-20261025b/capital-attacker")


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def rewrite(run: Path, change) -> None:
    log = run / "native/native.jsonl"
    log.write_text("".join(json.dumps(row) + "\n" for row in change(rows(log))))


def at(event, tick, edit):
    def change(events):
        for row in events:
            if row.get("event") == event and row["tick"] == tick:
                edit(row)
        return events
    return change


def no_morale_getter(row):
    units = row["value"]["battle"]["units"]
    next(u for u in units if u.get("men", 0) > 0 and u.get("hp", 0) > 0)["morale_percent"] = None


def manifest(run: Path, **fields) -> None:
    path = run / "manifest.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), **fields}))


def changed_like_restore_b(state: Path) -> None:
    """The changed control replaced by restore-b's log, keeping its changed-order record."""
    order = [r for r in rows(state / "changed/native/native.jsonl")
             if r.get("label") == "changed_flyer_move"]
    rewrite(state / "changed", lambda _: rows(state / "restore-b/native/native.jsonl") + order)


def plant(case: Path, name: str) -> None:
    state = case / "post-spell"
    if name == "changed_reading_before_its_order":
        rewrite(state / "changed", at("reading", 1150, lambda row: row["value"]["battle"][
            "units"][0].update(hp=row["value"]["battle"]["units"][0]["hp"] + 1)))
    elif name == "changed_order_unrecorded":
        rewrite(state / "changed", lambda events: [
            e for e in events if e.get("label") != "changed_flyer_move"])
    elif name == "changed_does_not_diverge":
        changed_like_restore_b(state)
    elif name == "restore_differs":
        rewrite(state / "restore-a", at("tick", 1500, lambda row: row.update(
            checksum=row["checksum"] + 1)))
    elif name == "restore_tick_missing":
        rewrite(state / "restore-b", lambda events: [
            e for e in events if not (e.get("event") == "tick" and e["tick"] == 1700)])
    elif name == "live_getter_missing":
        for run in (case / "source", state / "restore-a", state / "restore-b", state / "changed"):
            rewrite(run, at("reading", 1300, no_morale_getter))
    elif name == "source_save_unrecorded":
        rewrite(case / "source", lambda events: [e for e in events if e.get("event") != "saved"])
    elif name == "other_agent":
        manifest(state / "restore-b", agent_sha256="0" * 64)
    elif name == "not_closed":
        manifest(state / "restore-a", closed=False)
    elif name == "different_seed":
        rewrite(state / "restore-a", lambda events: [
            {**e, "lua_seed_matches": False} if e.get("event") == "restored" else e
            for e in events])


PLANTS = ["changed_reading_before_its_order", "changed_order_unrecorded",
          "changed_does_not_diverge", "restore_differs", "restore_tick_missing",
          "live_getter_missing", "source_save_unrecorded", "other_agent", "not_closed",
          "different_seed", "one_restore"]


def test_the_saved_case_passes_and_each_planted_wrong_value_fails_it(tmp_path, monkeypatch):
    if not EVIDENCE.is_dir():
        pytest.skip("needs the saved siege check evidence in runs/ (local only)")
    # compare_runs is a pure function of two logs and most of the time (it deep-copies every
    # reading): reuse its result while both logs' bytes are unchanged.
    real_events, real_compare, compared = siege.checkpoint.events, siege.compare_runs, {}

    class Log(list):
        digest = None

    def events(path):
        log = Log(real_events(path))
        log.digest = sha256(Path(path) / "native/native.jsonl")
        return log

    def compare(source, restore):
        key = (source.digest, restore.digest)
        if key not in compared:
            compared[key] = real_compare(source, restore)
        return compared[key]
    monkeypatch.setattr(siege.checkpoint, "events", events)
    monkeypatch.setattr(siege, "compare_runs", compare)

    def verdict(name: str) -> bool:
        case = Path(shutil.copytree(EVIDENCE, tmp_path / name))
        plant(case, name)
        state = case / "post-spell"
        restores = ["restore-a"] if name == "one_restore" else ["restore-a", "restore-b"]
        return siege.assess_case(case / "source", [state / r for r in restores],
                                 state / "changed", 1100, 1200, "capital-attacker",
                                 "post-spell")["pass"]
    assert verdict("clean")
    for name in PLANTS:
        assert not verdict(name), name
