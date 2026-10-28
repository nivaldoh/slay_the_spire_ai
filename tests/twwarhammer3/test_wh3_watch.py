"""The live job follower in twwarhammer3/battle/watch.py."""
import json
import os
import time

from wh3_fixtures import observation

from twwarhammer3.battle import watch
from twwarhammer3.battle.watch import Feed, check, follow, next_event

PROMPT = ("Battle notes:\n(none)\n\nDropped or rejected since your last plan:\n"
          "engine rejected f1 ability roar at self: unavailable_ability\n\nState: ...")


def records():
    state = observation(30000)
    plan = [{"unit": "f2", "skill": "engage", "target": "e1", "x": None, "z": None}]
    ability = {"unit": "f1", "type": "ability", "ability": "roar", "target": None}
    attempt = {"seconds": 5.5, "usd": 0.0004}
    return [
        {"kind": "roster", "observation": state},
        {"kind": "observation", "observation": state},
        {"kind": "decision", "time_ms": 30000, "request": "r7", "orders": [ability],
         "behavior": {"type": "commander", "model": "gpt-6-luna", "plan": plan,
                      "abilities": [ability], "reason": "Hold the line.", "notes": "e2 hides",
                      "dropped": [], "plan_age_s": 6.0, "attempts": [attempt],
                      "prompt": PROMPT}},
        {"kind": "model_exchange", "id": "m1", "prompt": PROMPT, "attempts": [attempt]},
        {"kind": "ack", "request": "r7", "latency": {"delay_ms": 300}, "ack": {
            "applied_ms": 30300,
            "results": [{"index": 1, "unit": "f1", "ok": False, "error": "unavailable_ability"}]}},
        {"kind": "observation", "observation": observation(61000)},
        # Lua sends an empty table as []: here, a battle without capture points.
        {"kind": "result", "observation": dict(observation(90000), result="won", final={
            "friendly": {"men": 60, "men0": 120}, "enemy": {"men": 10, "men0": 100},
            "objectives": []})},
    ]


def test_the_feed_summarizes_requests_replies_rejections_and_the_result():
    feed = Feed("episode-0002")
    lines = [line for record in records() for line in feed.lines(record)]
    assert lines[0] == "== episode-0002"
    assert lines[1].startswith("   us (wh3_main_kho_khorne): herald_of_khorne_0, chaos_warriors_0")
    assert lines[3:] == [
        "   30s <- plan 6.0 s old (5.5 s think): Hold the line.",
        "         f2 engage e1; f1 ability roar at self",
        "         notes: e2 hides",
        "   30s -> gpt-6-luna: us 2/2u 111m  seen 1/2u 90m; 136 chars",
        "         reported: engine rejected f1 ability roar at self: unavailable_ability",
        "   30s x engine rejected f1 ability roar at self: unavailable_ability",
        "   61s   us 2/2u 111m  seen 1/2u 90m  $0.0004",
        "== episode-0002: won at 90 s; friendly 50% left, enemy 10% left; $0.0004",
    ]


def test_follow_prints_a_finished_job_and_returns(tmp_path):
    job = tmp_path / "job"
    for index in range(2):
        episode = job / f"episode-{index:04d}"
        episode.mkdir(parents=True)
        (episode / "trace.jsonl").write_text(
            "".join(json.dumps(record) + "\n" for record in records()))
        (episode / "result.json").write_text("{}")
    (job / "manifest.json").write_text(json.dumps({"status": "completed"}))
    lines = []
    follow(job, out=lines.append)
    assert [line for line in lines if line.startswith("== episode")] == [
        "== episode-0000", "== episode-0000: won at 90 s; friendly 50% left, enemy 10% left;"
        " $0.0004", "== episode-0001", "== episode-0001: won at 90 s; friendly 50% left,"
        " enemy 10% left; $0.0004"]
    prompts = []
    follow(job / "episode-0001", prompts=True, out=prompts.append)
    assert "         Dropped or rejected since your last plan:" in prompts


def test_a_killed_job_without_a_result_ends_the_watch(tmp_path):
    episode = tmp_path / "job" / "episode-0000"
    episode.mkdir(parents=True)
    (episode / "trace.jsonl").write_text(json.dumps(records()[0]) + "\n")
    (tmp_path / "job" / "manifest.json").write_text(json.dumps({"status": "interrupted"}))
    lines = []
    follow(tmp_path / "job", out=lines.append)
    assert lines[0] == "== episode-0000"


def test_next_returns_once_per_episode_stall_or_job_end(tmp_path, monkeypatch):
    job = tmp_path / "job"
    episode = job / "episode-0000"
    episode.mkdir(parents=True)
    (episode / "trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records()))
    manifest = {"status": "running", "episodes": []}
    (job / "manifest.json").write_text(json.dumps(manifest))
    assert check(job, 0) is None
    for path, age in ((job / "manifest.json", 400), (episode / "trace.jsonl", 300)):
        os.utime(path, (time.time() - age, time.time() - age))
    assert check(job, 0).startswith("STALL: episode-0000/trace.jsonl unchanged for 30")
    assert check(job, 0, stall_s=600) is None
    (episode / "result.json").write_text(json.dumps({"status": "won", "battle_s": 90,
                                                     "policy": "commander"}))
    manifest = {"status": "completed", "episodes": [{"episode": "episode-0000"}]}
    (job / "manifest.json").write_text(json.dumps(manifest))
    lines = check(job, 0).splitlines()
    assert lines[0].startswith("episode-0000: won at 90 s battle time;")
    assert lines[0].endswith("; policy commander")
    assert lines[1] == "final at 90 s: us 2/2u 111m  seen 1/2u 90m"
    assert lines[-2:] == ["notes: e2 hides", "job completed"]
    assert next_event(job) == check(job, 1) == "job completed"
    monkeypatch.setattr(watch, "START_S", 0)
    (tmp_path / "refused.log").write_text("starting\nRuntimeError: uncommitted changes\n")
    assert next_event(tmp_path / "refused", poll=0) == (
        "NOT STARTED: starting | RuntimeError: uncommitted changes")


def test_an_updated_game_build_is_announced_by_watch_and_digest(tmp_path):
    # Steam may update the game (owner, 2026-10-18): the job records it and the tools say so.
    from twwarhammer3.battle.digest import job_digest

    job = tmp_path / "job"
    episode = job / "episode-0000"
    episode.mkdir(parents=True)
    (episode / "trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records()))
    (episode / "result.json").write_text(json.dumps({"status": "won", "policy": "hold"}))
    manifest = {"status": "completed", "episodes": [{"episode": "episode-0000"}],
                "deployment": {"steam_build_id": "99", "steam_build_pinned": True},
                "config": {"policy": "hold", "scenario": "kho5-dwf5", "model": None,
                           "effort": None, "seed": None},
                "created_at": "2026-10-18T00:00:00", "source_revision": "abc1234"}
    (job / "manifest.json").write_text(json.dumps(manifest))
    lines = []
    follow(job, out=lines.append)
    assert not any("WARNING" in line for line in lines)
    assert "WARNING" not in check(job, 0) and "WARNING" not in job_digest(job)
    manifest["deployment"]["steam_build_pinned"] = False
    (job / "manifest.json").write_text(json.dumps(manifest))
    warning = "WARNING: game build 99 is not the pinned build; tell the owner"
    lines = []
    follow(job, out=lines.append)
    assert lines[0].startswith(warning) and sum("WARNING" in line for line in lines) == 1
    assert check(job, 0).startswith(warning) and job_digest(job).startswith(warning)
