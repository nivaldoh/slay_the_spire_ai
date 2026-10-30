"""The siege case verdict requires each restore's spell witness, on a copy of the saved evidence.

test_wh3_siege_saved_evidence.py plants every other clause; this one plants a restore whose
spell target has a different armour at the checkpoint. compare_runs leaves units' cached stats
out, so the restore still matches its source there and only the spell witness can fail the
case. The plant "the spell witness is not required" passed every test until this one
(runs/agreed-planted-20261029/result-siege-after.txt). runs/ is local, so it skips without
the evidence.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_wh3_checkpoint_siege as siege  # noqa: E402

EVIDENCE = (Path(__file__).resolve().parents[3]
            / "runs/twwarhammer3/siege-final-20261025b/capital-attacker")


def verdict(case: Path) -> dict:
    state = case / "post-spell"
    return siege.assess_case(case / "source", [state / "restore-a", state / "restore-b"],
                             state / "changed", 1100, 1200, "capital-attacker", "post-spell")


def test_a_restore_whose_spell_target_differs_at_the_checkpoint_fails_the_case(tmp_path):
    if not EVIDENCE.is_dir():
        pytest.skip("needs the saved siege check evidence in runs/ (local only)")
    case = Path(shutil.copytree(EVIDENCE, tmp_path / "case"))
    log = case / "post-spell/restore-a/native/native.jsonl"
    rows = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    for row in rows:
        if row.get("event") == "reading" and row["tick"] == 1100:
            target = next(u for u in row["value"]["battle"]["units"]
                          if u["side"] == 1 and u["index"] == 2)
            target["stats"] = target["stats"].replace("stat_armour=", "stat_armour=1", 1)
    log.write_text("".join(json.dumps(row) + "\n" for row in rows))
    result = verdict(case)
    restore = result["runs"][1]
    assert restore["comparison"]["checksum_mismatches"] == 0
    assert not restore["comparison"]["readings_unequal"]  # the restore still matches its source
    assert not restore["spell_witness"]["checks"]["checkpoint_armour"]
    assert not result["pass"]
