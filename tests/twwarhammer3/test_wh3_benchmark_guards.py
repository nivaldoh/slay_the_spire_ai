"""Guards of the benchmark profiles (battle/benchmark.py) that no other test exercised.

Each test feeds the case its refusal names. The 2026-11-13 refusal sweep found these refusals
uncaught (runs/overnight-20261113/); each test fails when its refusal is removed.
"""

import json
import signal

import pytest

from gameai.llm import APIError
from twwarhammer3.battle import benchmark
from twwarhammer3.battle.setup import scenarios

# The frozen profile: one fresh launch and battle, no added waits, 900/1320 s caps and
# 1000/250 ms observation/tick (benchmark.validate_config).
FROZEN = {"policy": "hold", "episodes": 1, "start_timeout": 900, "episode_timeout": 1320,
          "observe_ms": 1000, "tick_ms": 250}


def mirror():
    return scenarios()[benchmark.SCENARIO]


@pytest.mark.parametrize("change", [
    {"policy": "hold,attack_nearest"}, {"policy": "llm"}, {"episodes": 2}, {"attach": True},
    {"interval_ms": 500}, {"delay_seconds": "2"}, {"start_timeout": 600},
    {"episode_timeout": 2000}, {"observe_ms": 500}, {"tick_ms": 100},
], ids=lambda change: next(iter(change)))
def test_a_mirror_job_off_the_frozen_profile_is_refused(change):
    benchmark.validate_config(mirror(), FROZEN)
    with pytest.raises(ValueError, match="requires one fresh launch/battle"):
        benchmark.validate_config(mirror(), {**FROZEN, **change})


def test_the_suite_admits_its_own_controllers_and_still_refuses_others():
    suite_scenario = scenarios()["coord-relief"]
    benchmark.validate_config(suite_scenario, {**FROZEN, "policy": "llm"})
    with pytest.raises(ValueError, match="requires one fresh launch/battle"):
        benchmark.validate_config(suite_scenario, {
            **FROZEN, "policy": "twwarhammer3.battle.calibration:SnapHitAndRun"})


def test_an_unknown_benchmark_version_is_refused_rather_than_read_as_the_mirror():
    with pytest.raises(ValueError, match="unknown benchmark version"):
        benchmark.validate_config({**mirror(), "benchmark": "mirror-v2"}, FROZEN)


def test_a_request_is_not_sent_while_another_deadline_timer_runs(monkeypatch):
    """send_once owns SIGALRM for its total deadline. Without the refusal it would replace the
    other owner's handler and timer, send, and then cancel that timer."""
    sent = []
    monkeypatch.setattr(benchmark, "post", lambda *args, **kwargs: sent.append(kwargs))
    before = signal.getsignal(signal.SIGALRM)

    def other(signum, frame):
        pass

    signal.signal(signal.SIGALRM, other)
    signal.setitimer(signal.ITIMER_REAL, 30)
    try:
        with pytest.raises(APIError, match="unused request deadline timer"):
            benchmark.send_once("dummy", {}, provider="anthropic")
        remaining, _ = signal.getitimer(signal.ITIMER_REAL)
        assert sent == [] and 0 < remaining <= 30
        assert signal.getsignal(signal.SIGALRM) is other
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, before)


@pytest.mark.parametrize("version", ["mirror-v0", None], ids=["other-version", "queue-plan"])
def test_only_a_benchmark_plan_is_collected(tmp_path, monkeypatch, version):
    """A plan of another version, or an ordinary queue plan, is never read as the mirror's
    attempts. Without the refusal the first is collected row by row as a mirror plan, and the
    second fails later as a KeyError."""
    monkeypatch.setattr(benchmark.subprocess, "check_output", lambda *a, **k: "abc\n")
    path = tmp_path / "pilot.json"
    plan = benchmark.make_plan(path, "pilot", 2)
    if version is None:
        del plan["benchmark"]
    else:
        plan["benchmark"] = version
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="not a benchmark plan"):
        benchmark.collect(path)
