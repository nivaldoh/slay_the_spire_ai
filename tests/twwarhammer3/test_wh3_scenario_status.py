"""Each scenario entry's review state: its own status, split and version (setup.py docstring).

Owner, 2026-11-15: "Your four suggested scenario statuses are fine." and "Approve this mapping
(Recommended)"; evaluation-guidelines.md had proposed that ``setup.scenarios()`` stop inheriting
``split`` and ``status`` through ``base``. Offline; the declarations themselves are data the
owner approved, so only the rule is checked here.
"""
import json

import pytest

from twwarhammer3.battle import setup


def test_every_declared_entry_writes_its_own_status_and_no_harness_entry_has_one():
    written = setup.entries()
    for name, entry in setup.scenarios().items():
        if "expect" in entry:  # a declared benchmark scenario (benchmark.md, Scenarios)
            assert written[name].get("status") in setup.STATUSES, name
            assert "split" in written[name], name
            # JUDGEMENT?: Held-out tie — Claude, 2026-11-15: status held_out exactly when split is
            # held_out (export.py holds rows out by split). Letting them differ, as the scenario
            # guidelines' "separate facts" allow, changes which entries exports hold out.
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


def test_entries_come_from_every_file_of_the_directory_and_a_base_may_be_in_another(
        monkeypatch, tmp_path):
    """Owner, 2026-11-15: "Split the scenario file". Wrong version: only the first file is
    read, or a base in another file is not found."""
    (tmp_path / "b.json").write_text(json.dumps({"child": {"base": "parent", "map": "n"}}))
    (tmp_path / "a.json").write_text(json.dumps({"parent": {"map": "m", "expect": {"funds": 1}}}))
    (tmp_path / "notes.txt").write_text("not a scenario file")
    (tmp_path / "deeper").mkdir()  # only the directory's own files are read
    (tmp_path / "deeper" / "c.json").write_text(json.dumps({"nested": {"map": "o"}}))
    monkeypatch.setattr(setup, "SCENARIOS_PATH", tmp_path)
    assert list(setup.entries()) == ["parent", "child"]  # files in name order
    assert setup.scenarios()["child"] == {"map": "n", "expect": {"funds": 1}}


def test_a_name_written_in_two_files_is_refused(monkeypatch, tmp_path):
    """Wrong version: the later file's entry silently replaces the earlier one."""
    (tmp_path / "a.json").write_text(json.dumps({"twice": {"map": "m"}}))
    (tmp_path / "b.json").write_text(json.dumps({"twice": {"map": "n"}}))
    monkeypatch.setattr(setup, "SCENARIOS_PATH", tmp_path)
    with pytest.raises(ValueError, match="twice is declared twice"):
        setup.entries()


def test_a_name_or_field_written_twice_in_one_file_is_refused(monkeypatch, tmp_path):
    """Wrong version: json.loads alone, which keeps the last of two members with one name."""
    monkeypatch.setattr(setup, "SCENARIOS_PATH", tmp_path)
    (tmp_path / "a.json").write_text('{"twice": {"map": "m"}, "twice": {"map": "n"}}')
    with pytest.raises(ValueError, match="a.json writes twice twice"):
        setup.entries()
    (tmp_path / "a.json").write_text('{"one": {"status": "current", "status": "retired"}}')
    with pytest.raises(ValueError, match="a.json writes status twice"):
        setup.entries()
