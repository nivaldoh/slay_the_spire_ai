import json

import pytest
from wh3_fixtures import observation

from twwarhammer3.battle.digest import decision_at, digest, units_digest

ARMY = {"subculture": "wh3_main_sc_kho_khorne", "units": None}


def write_job(job, config, scenario, results):
    job.mkdir(parents=True)
    (job / "manifest.json").write_text(json.dumps({
        "status": "completed", "created_at": "2026-10-15T00:00:00", "source_revision": "abc1234def",
        "config": {"model": "gpt-6-luna", "effort": "low", "seed": None, **config},
        "scenario": scenario}))
    for index, result in enumerate(results):
        episode = job / f"episode-{index:04d}"
        episode.mkdir()
        (episode / "result.json").write_text(json.dumps(result))


@pytest.mark.parametrize("enemy,draw", [
    (None, "(seed 7: wh3_main_sc_kho_khorne on survival_map)"),
    ([{"subculture": "dwarfs"}, {"subculture": "empire"}],
     "(seed 7: wh3_main_sc_kho_khorne vs dwarfs vs empire on survival_map)"),
])
def test_job_digest_draws_every_side_and_names_no_seed_for_a_named_scenario(tmp_path, enemy,
                                                                            draw):
    scenario = {"player": ARMY, "enemy": enemy, "map": "survival_map"}
    write_job(tmp_path / "random", {"policy": "skills", "scenario": "random", "seed": 7},
              scenario, [])
    assert draw in digest(tmp_path / "random").splitlines()[0]
    write_job(tmp_path / "named", {"policy": "skills", "scenario": "survival-kho5"}, scenario, [])
    assert "seed" not in digest(tmp_path / "named")


def test_job_digest_shows_each_episode_controller_and_the_model_of_a_rotation(tmp_path):
    write_job(tmp_path / "job", {"policy": "rush_nearest,llm_rules", "scenario": "kho5-dwf5"},
              {"player": ARMY, "enemy": ARMY, "map": "m"},
              [{"status": "lost", "policy": "rush_nearest"},
               {"status": "won", "policy": "llm_rules", "llm": {"usd": 0.02}}])
    lines = digest(tmp_path / "job").splitlines()
    assert lines[0] == ("job: completed, policy rush_nearest,llm_rules gpt-6-luna/low,"
                        " scenario kho5-dwf5, source abc1234")
    assert lines[1].startswith("| episode | policy | outcome |")
    assert lines[3].startswith("| episode-0000 | rush_nearest | lost |")
    assert lines[4].startswith("| episode-0001 | llm_rules | won |")


def decision(seconds, orders=(), reason="Wait.", **behavior):
    return {"kind": "decision", "time_ms": seconds * 1000, "request": f"r{seconds}",
            "orders": list(orders), "behavior": {"reason": reason, **behavior}}


def ack(seconds, results):
    return {"kind": "ack", "request": f"r{seconds}", "latency": {"delay_ms": 400},
            "ack": {"applied_ms": seconds * 1000 + 400, "results": results}}


def write_episode(episode, records, result=None):
    episode.mkdir(parents=True)
    (episode / "trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    (episode / "result.json").write_text(json.dumps(result or {"status": "won"}))


def test_runs_without_new_orders_fold_into_one_line_but_a_refusal_does_not(tmp_path):
    attack = {"unit": "f1", "type": "attack", "target": "e1", "run": False}
    write_episode(tmp_path / "episode-0000", [
        {"kind": "observation", "observation": observation(1000)},
        decision(1, [attack], reason="Go."), ack(1, [{"index": 1, "unit": "f1", "ok": True}]),
        decision(4), ack(4, []), decision(7), decision(10, reason="Still waiting."),
        {"kind": "invalid", "error": "f9 is not a friendly unit", "orders": []},
        decision(13), decision(16),
    ], {"status": "won", "policy": "llm", "objectives": {"victory_held": 0.5, "build": 2}})
    lines = digest(tmp_path / "episode-0000").splitlines()
    assert lines[0].endswith("; policy llm; victory points held 50%, built 2")
    state = "us 2/2u 111m  seen 1/2u 90m"
    assert lines[1:6] == [
        f"     1s  {state}  f1 attack e1 | Go.  [delay 0.4s]",
        f"     4s  {state}  no new orders x3 until 10s | Still waiting.",
        "        invalid: f9 is not a friendly unit",
        f"    13s  {state}  no new orders | Wait.",
        f"    16s  {state}  no new orders | Wait.",
    ]


def test_units_digest_tracks_each_unit_from_first_to_last_sight_and_counts_refusals(tmp_path):
    first, later = observation(1000), observation(9000, visible=("e1", "e2"))
    later["friendly"][1].update(men=60, state=["melee"])
    later["enemy"][0].update(men=40, state=["routing"])
    for episode in ("episode-0000", "episode-0001"):
        write_episode(tmp_path / episode, [
            {"kind": "observation", "observation": first},
            ack(2, [{"index": 1, "unit": "f2", "ok": False, "error": "unreachable"},
                    {"index": 2, "unit": "f2", "ok": False, "error": "unreachable"},
                    {"index": 3, "unit": "f1", "ok": True}]),
            {"kind": "observation", "observation": later}])
    lines = units_digest(tmp_path).splitlines()
    assert lines[0] == "episode-0000 units:" and "episode-0001 units:" in lines
    assert "| friendly | f2 | chaos_warriors_0 | 110 → 60 |  | 9.0 |  |" in lines
    assert "| enemy | e1 | dwarf_warriors_0 | 90 → 40 |  |  | 9.0 |" in lines
    assert "| enemy | e2 | grudge_thrower | 4 → 4 |  |  |  |" in lines
    assert lines[lines.index("episode-0001 units:") - 2] == "engine refusals: unreachable 2"
    assert units_digest(tmp_path / "episode-0001") == "\n".join(
        lines[lines.index("episode-0001 units:"):])


def test_decision_at_prints_the_prompt_reply_orders_and_verdicts(tmp_path):
    move = {"unit": "f1", "type": "move", "x": 10, "z": 20, "run": True}
    reply = {"text": '{"orders": []}', "seconds": 2.0, "usd": 0.001, "status": "completed"}
    write_episode(tmp_path / "llm", [
        decision(5, [move], prompt="State at 5 s", attempts=[reply], type="llm", model="m",
                 dropped=["f9 halt: unknown order type"]),
        ack(5, [{"index": 1, "unit": "f1", "ok": False, "error": "unreachable"}]),
        decision(9, [], prompt="State at 9 s", attempts=[reply], type="llm", model="m"),
    ])
    assert decision_at(tmp_path / "llm", 6).splitlines() == [
        "llm r5: state at 5.0 s, decided at 5.0 s, m/None", "-- prompt (state at 5.0 s):",
        "State at 5 s", "-- reply (completed, 2.0 s, $0.0010):", '{"orders": []}',
        "   dropped f9 halt: unknown order type", "-- orders: f1 move (10, 20) run",
        "-- engine applied at 5.4 s (delay 0.4 s):",
        "   1. f1 move (10, 20) run: REJECTED unreachable"]
    plan = [{"unit": "f1", "skill": "charge", "target": None, "x": None, "z": None}]
    write_episode(tmp_path / "commander", [
        decision(5, [], prompt="State at 5 s", type="commander"),
        decision(6, [], reason=None, type="commander"),
        decision(12, [move], prompt="State at 12 s", attempts=[reply], plan=plan,
                 plan_age_s=7.0, type="commander"),
    ])
    text = decision_at(tmp_path / "commander", 6)
    assert "-- prompt (state at 5.0 s):\nState at 5 s\n-- reply" in text
    assert "-- plan (7.0 s old): f1 charge" in text
    assert text.endswith("-- engine: no acknowledgement in the trace")


def test_an_episode_line_shows_the_engine_status_of_a_timer_win(tmp_path):
    write_episode(tmp_path / "episode-0000", [
        {"kind": "observation", "observation": observation(1000)}, decision(1)],
        {"status": "won", "ended_by": "time_limit", "battle_s": 1205})
    assert digest(tmp_path / "episode-0000").splitlines()[0].startswith(
        "episode-0000: won at 1205 s battle time;")
