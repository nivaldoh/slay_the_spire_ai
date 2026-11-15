"""Each scenario entry's review state: its own status, split and version (setup.py docstring).

Owner, 2026-11-15: "Your four suggested scenario statuses are fine." and "Approve this mapping
(Recommended)"; evaluation-guidelines.md had proposed that ``setup.scenarios()`` stop inheriting
``split`` and ``status`` through ``base``. Offline; the declarations themselves are data the
owner approved, so only the rule is checked here.
"""
import json

from twwarhammer3.battle import setup


def test_every_declared_entry_writes_its_own_status_and_no_harness_entry_has_one():
    written = json.loads(setup.SCENARIOS_PATH.read_text())
    for name, entry in setup.scenarios().items():
        if "expect" in entry:  # a declared benchmark scenario (benchmark.md, Scenarios)
            assert written[name].get("status") in setup.STATUSES, name
            assert "split" in written[name], name
            # JUDGEMENT?: Held-out tie — Claude, 2026-11-15: status held_out exactly when split is
            # held_out, because export.py holds rows out by split. The owner's answers named the
            # four statuses, not this tie, and scenario-guidelines.md calls split and status
            # separate facts; letting them differ would let a held-out entry reach an export.
            assert (entry["status"] == "held_out") == (entry["split"] == "held_out"), name
        else:
            assert not any(key in entry for key in setup.OWN), name


def test_an_entry_takes_its_battle_from_its_base_and_never_its_review_state(monkeypatch, tmp_path):
    """Wrong version: the base's status, split or version reaches an entry that wrote none."""
    path = tmp_path / "scenarios.json"
    path.write_text(json.dumps({
        "parent": {"status": "current", "split": "held_out", "scenario_version": 3, "map": "m",
                   "expect": {"funds": 1}},
        "child": {"base": "parent", "expect": {"timer": 2}},
        "grandchild": {"base": "child", "status": "candidate"}}))
    monkeypatch.setattr(setup, "SCENARIOS_PATH", path)
    resolved = setup.scenarios()
    assert resolved["child"] == {"map": "m", "expect": {"funds": 1, "timer": 2}}
    assert resolved["grandchild"] == {"map": "m", "expect": {"funds": 1, "timer": 2},
                                      "status": "candidate"}
    assert resolved["parent"]["status"] == "current"
