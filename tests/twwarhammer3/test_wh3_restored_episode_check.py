"""The checkpoint-RL step-run check's pass rule (check_wh3_restored_episode.assess) on its saved
passing evidence, runs/twwarhammer3/rl/stage1-20261026 (docs/agreed-checks.md), with one wrong
value planted per case through the check's own readers. runs/ is local, so the test skips
without that evidence; nothing is written to it."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "check_wh3_restored_episode", Path(__file__).with_name("check_wh3_restored_episode.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

EVIDENCE = Path(__file__).resolve().parents[2] / "runs/twwarhammer3/rl/stage1-20261026"


@pytest.fixture
def evidence():
    if not EVIDENCE.is_dir():
        pytest.skip("needs the saved step-run evidence in runs/ (local only)")
    return EVIDENCE.resolve()


def plant_load(monkeypatch, name, change):
    original = check.load

    def load(run_dir):
        attempt = original(run_dir)
        if Path(run_dir).name == name:
            change(attempt)
        return attempt
    monkeypatch.setattr(check, "load", load)


def plant_stream(monkeypatch, name, **fields):
    original = check.stream_evidence
    monkeypatch.setattr(check, "stream_evidence", lambda run_dir: {
        **original(run_dir), **(fields if Path(run_dir).name == name else {})})


def plant_pair(monkeypatch, a, b, **fields):
    original = check.checkpoint.compare_attempts

    def compare(first, second, after_ms):
        result = original(first, second, after_ms)
        return {**result, **fields} if (Path(first).name, Path(second).name) == (a, b) else result
    monkeypatch.setattr(check.checkpoint, "compare_attempts", compare)


def later(attempt):
    attempt["attribution"]["applied_ms"] += 100


PLANTS = {
    "late_fault": lambda m: plant_load(m, "attack-a", lambda a: a.update(late_fault="close")),
    "gap_after_handover": lambda m: plant_stream(m, "restore-b", gaps_after_handover=[[2101, 2]]),
    "unrecorded_save": lambda m: plant_load(m, "source", lambda s: s["plan"]["save_at"].append(
        {"tick": 601})),
    "attempt_observations_differ": lambda m: plant_pair(m, "attack-a", "attack-b",
                                                        observations_unequal=[210500]),
    "restore_endings_differ": lambda m: plant_pair(m, "restore-a", "restore-c",
                                                   endings_equal=False),
    "injection_applied_later": lambda m: plant_load(m, "attack-b", later),
    "move_without_witness": lambda m: plant_load(m, "move", lambda a: a["attribution"].update(
        witness={check.GUNS: "missing"})),
}


def test_each_planted_wrong_value_fails_the_check(evidence, monkeypatch):
    # Parse each log once for all plants: parsing is most of assess's time.
    parsed, original = {}, check.checkpoint.jsonl
    monkeypatch.setattr(check.checkpoint, "jsonl", lambda path: parsed[path] if path in parsed
                        else parsed.setdefault(path, original(path)))
    assert check.assess(evidence)["pass"]
    for name, plant in PLANTS.items():
        with monkeypatch.context() as patch:
            plant(patch)
            assert not check.assess(evidence)["pass"], name
    assert check.assess(evidence)["pass"]  # the shared rows are unchanged
