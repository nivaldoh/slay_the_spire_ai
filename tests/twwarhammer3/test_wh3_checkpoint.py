"""The checkpoint check's comparison and pass rule, on synthetic agent logs (no game)."""
import importlib.util
import json
from pathlib import Path

import pytest

from twwarhammer3.battle import checkpoint

spec = importlib.util.spec_from_file_location(
    "check_wh3_checkpoint", Path(__file__).with_name("check_wh3_checkpoint.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def battle(seed=0, changed_from=None, restored=True, reading_change=None):
    """Agent events: per-tick checksums, readings every 100 ticks, a restore record at 1200."""
    rows = []
    for tick in range(1, check.STOP + 1):
        diverged = changed_from is not None and tick >= changed_from
        checksum = tick * 7 + seed + (1 if diverged else 0)
        rows.append({"event": "tick", "tick": tick, "checksum": checksum})
        if tick % 100 == 0:
            value = {"units": [{"x": tick / 10, "hp": 0.9 if diverged else 1.0}],
                     "script": {"draws": [5]}}
            if reading_change == tick:
                value["units"][0]["hp"] = 0.5
            rows.append({"event": "reading", "tick": tick, "value": value})
    if restored:
        rows.append({"event": "restored", "tick": check.CHECKPOINT, "lua_seed_matches": True})
    rows.append({"event": "done", "tick": check.STOP})
    return rows


def write(output: Path, runs: dict) -> Path:
    for name, rows in runs.items():
        (output / name / "native").mkdir(parents=True)
        lines = "\n".join(json.dumps(r) for r in rows) + "\n"
        (output / name / "native/native.jsonl").write_text(lines)
        manifest = {"closed": True, "completed": True}
        (output / name / "manifest.json").write_text(json.dumps(manifest))
    return output


def source():
    return battle(restored=False) + [{"event": "saved", "tick": check.CHECKPOINT, "name": "x"}]


def test_compare_finds_the_first_diverging_tick_and_reading():
    result = checkpoint.compare(battle(), battle(changed_from=1304))
    assert (result["checksum_mismatches"], result["first_mismatch"]) == (check.STOP - 1303, 1304)
    assert result["readings_unequal"][0] == 1400
    same = checkpoint.compare(battle(), battle())
    assert same["checksum_mismatches"] == 0 and not same["readings_unequal"]


def test_check_passes_exact_restores_and_a_diverging_change(tmp_path):
    output = write(tmp_path, {"source": source(), "restore-a": battle(), "restore-b": battle(),
                              "changed": battle(changed_from=1304)})
    assert check.assess(output)["pass"]


def test_check_fails_on_one_wrong_tick_a_wrong_reading_or_a_change_that_does_not_diverge(tmp_path):
    one_tick = battle()
    next(r for r in one_tick if r["event"] == "tick" and r["tick"] == 1701)["checksum"] += 1
    cases = {"tick": {"restore-a": one_tick},
             "reading": {"restore-b": battle(reading_change=1800)},
             "changed": {"changed": battle()},
             "not_restored": {"restore-a": battle(restored=False)}}
    for name, override in cases.items():
        runs = {"source": source(), "restore-a": battle(), "restore-b": battle(),
                "changed": battle(changed_from=1304), **override}
        assert not check.assess(write(tmp_path / name, runs))["pass"], name


@pytest.mark.parametrize("run,event,problem", [
    ("source", "tick", "missing"), ("restore-a", "tick", "missing"),
    ("source", "reading", "missing"), ("restore-b", "reading", "missing"),
    ("restore-a", "tick", "duplicate"), ("restore-b", "reading", "duplicate"),
    ("changed", "done", "missing"),
    ("source", "error", "insert"), ("restore-a", "frida_error", "insert"),
    ("restore-b", "detached", "insert"),
])
def test_check_rejects_incomplete_or_failed_native_evidence(tmp_path, run, event, problem):
    runs = {"source": source(), "restore-a": battle(), "restore-b": battle(),
            "changed": battle(changed_from=1304)}
    rows = runs[run]
    if problem == "insert":
        rows.insert(0, {"event": event, "message": "test failure"})
    else:
        item = next(row for row in rows if row["event"] == event
                    and (event == "done" or row["tick"] == 1700))
        if problem == "missing":
            rows.remove(item)
        else:
            rows.append(dict(item))
    assert not check.assess(write(tmp_path, runs))["pass"]


def test_check_requires_manifest_completion_and_allows_normal_detach(tmp_path):
    runs = {"source": source(), "restore-a": battle(), "restore-b": battle(),
            "changed": battle(changed_from=1304)}
    for rows in runs.values():
        rows.append({"event": "detached", "reason": "application-requested"})
    output = write(tmp_path, runs)
    assert check.assess(output)["pass"]
    (output / "source/manifest.json").write_text(json.dumps({"closed": True, "completed": False}))
    assert not check.assess(output)["pass"]


@pytest.mark.parametrize("interrupt_after_move", [False, True])
@pytest.mark.parametrize("phase", ["aside", "return"])
def test_only_replay_finishes_returning_bystanders_after_interrupt(
        tmp_path, monkeypatch, interrupt_after_move, phase):
    replays = tmp_path / "replays"
    replays.mkdir()
    contents = {"checkpoint.replay": b"checkpoint", **{
        f"bystander-{i}.replay": f"original replay {i}".encode() for i in range(4)}}
    for name, data in contents.items():
        (replays / name).write_bytes(data)
    monkeypatch.setattr(checkpoint.runtime, "user_dir", lambda: tmp_path)
    aside = replays / "checkpoint-aside"
    original_move = checkpoint.shutil.move
    interruption = KeyboardInterrupt("interrupted returning replays")
    interrupted = False

    def move(source, destination):
        nonlocal interrupted
        in_phase = Path(destination if phase == "aside" else source).parent == aside
        if in_phase and not interrupted:
            interrupted = True
            if interrupt_after_move:
                original_move(source, destination)
            raise interruption
        return original_move(source, destination)

    monkeypatch.setattr(checkpoint.shutil, "move", move)
    body_entered = False
    with pytest.raises(KeyboardInterrupt) as raised:
        with checkpoint.only_replay("checkpoint"):
            body_entered = True
            assert list(replays.glob("*.replay")) == [replays / "checkpoint.replay"]
    assert body_entered is (phase == "return")
    assert raised.value is interruption
    assert {p.name: p.read_bytes() for p in replays.glob("*.replay")} == contents
    assert not aside.exists()
