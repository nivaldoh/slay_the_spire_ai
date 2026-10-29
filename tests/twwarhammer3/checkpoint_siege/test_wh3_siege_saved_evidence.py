"""The siege check's whole pass rule on a copy of its saved passing evidence.

The other siege tests cover the comparison and the witnesses; this one runs assess_case, which
combines them, on the capital-attacker post-spell runs of runs/twwarhammer3/siege-final-20261025b
(the agreed check's passing evidence, docs/agreed-checks.md), then plants one wrong value per
case in a copy. runs/ is local, so the test skips without that evidence.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_wh3_checkpoint_siege import assess_case  # noqa: E402

EVIDENCE = (Path(__file__).resolve().parents[3]
            / "runs/twwarhammer3/siege-final-20261025b/capital-attacker")


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def rewrite(run: Path, change) -> None:
    log = run / "native/native.jsonl"
    log.write_text("".join(json.dumps(row) + "\n" for row in change(rows(log))))


def reading_at(tick, edit):
    def change(events):
        for row in events:
            if row.get("event") == "reading" and row["tick"] == tick:
                edit(row["value"]["battle"]["units"])
        return events
    return change


def no_morale_getter(units):
    next(u for u in units if u.get("men", 0) > 0 and u.get("hp", 0) > 0)["morale_percent"] = None


def assess(case: Path, restores=("restore-a", "restore-b")) -> dict:
    state = case / "post-spell"
    return assess_case(case / "source", [state / name for name in restores], state / "changed",
                       1100, 1200, "capital-attacker", "post-spell")


@pytest.fixture
def case(tmp_path):
    if not EVIDENCE.is_dir():
        pytest.skip("needs the saved siege check evidence in runs/ (local only)")
    return Path(shutil.copytree(EVIDENCE, tmp_path / "capital-attacker"))


def test_the_saved_evidence_passes(case):
    assert assess(case)["pass"]


def plant(case: Path, name: str) -> None:
    state = case / "post-spell"
    if name == "changed_reading_before_its_order":
        rewrite(state / "changed", reading_at(1150, lambda units: units[0].update(
            hp=units[0]["hp"] + 1)))
    elif name == "changed_order_unrecorded":
        rewrite(state / "changed", lambda events: [
            e for e in events if e.get("label") != "changed_flyer_move"])
    elif name == "live_getter_missing":
        for run in (case / "source", state / "restore-a", state / "restore-b", state / "changed"):
            rewrite(run, reading_at(1300, no_morale_getter))
    elif name == "other_agent":
        manifest = json.loads((state / "restore-b/manifest.json").read_text())
        manifest["agent_sha256"] = "0" * 64
        (state / "restore-b/manifest.json").write_text(json.dumps(manifest))
    elif name == "different_seed":
        rewrite(state / "restore-a", lambda events: [
            {**e, "lua_seed_matches": False} if e.get("event") == "restored" else e
            for e in events])


@pytest.mark.parametrize("name", ["changed_reading_before_its_order", "changed_order_unrecorded",
                                  "live_getter_missing", "other_agent", "different_seed",
                                  "one_restore"])
def test_one_planted_wrong_value_fails_the_case(case, name):
    plant(case, name)
    restores = ("restore-a",) if name == "one_restore" else ("restore-a", "restore-b")
    assert not assess(case, restores)["pass"]
