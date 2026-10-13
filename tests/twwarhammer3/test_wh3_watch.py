import json

from test_wh3_llm import observation

from twwarhammer3.battle.play import caption
from twwarhammer3.battle.watch import Feed, follow

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
        {"kind": "ack", "request": "r7", "ack": {"applied_ms": 30300, "results": [
            {"index": 1, "unit": "f1", "ok": False, "error": "unavailable_ability"}]}},
        {"kind": "observation", "observation": observation(61000)},
        {"kind": "result", "observation": dict(observation(90000), result="won", final={
            "friendly": {"men": 60, "men0": 120}, "enemy": {"men": 10, "men0": 100}})},
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


def test_captions_show_what_a_model_saw_and_decided():
    state = observation(36000)
    plan = {"type": "commander", "model": "gpt-6-luna", "reason": "Wait.", "plan_age_s": 6.0,
            "plan": [{"unit": "f1", "skill": "charge", "target": None, "x": None, "z": None}]}
    assert caption(state, plan, []) == (
        "36 s: gpt-6-luna plan from the state at 30 s\nWait.\nf1 charge")
    direct = {"type": "llm", "model": "gpt-6-luna", "reason": "Go."}
    order = {"unit": "f2", "type": "attack", "target": "e1", "mode": "melee", "run": False}
    assert caption(state, direct, [order]) == (
        "36 s: gpt-6-luna saw us 2/2u 111m  seen 1/2u 90m\nGo.\nf2 attack e1 melee")
    assert caption(state, {"type": "commander"}, []) is None


def test_a_killed_job_without_a_result_ends_the_watch(tmp_path):
    episode = tmp_path / "job" / "episode-0000"
    episode.mkdir(parents=True)
    (episode / "trace.jsonl").write_text(json.dumps(records()[0]) + "\n")
    (tmp_path / "job" / "manifest.json").write_text(json.dumps({"status": "interrupted"}))
    lines = []
    follow(tmp_path / "job", out=lines.append)
    assert lines[0] == "== episode-0000"
