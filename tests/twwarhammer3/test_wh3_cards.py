import json

from twwarhammer3.battle.cards import CARDS, battles, board, cycles, jobs, outcome, verdict


def _frame(second, melee):
    return {"time_ms": second * 1000,
            "friendly": [{"id": "f1", "state": ["melee"] if melee else ["moving"]}]}


def test_a_cycle_needs_an_applied_pull_out_during_melee_and_a_new_charge(tmp_path):
    # Engagements 10-15 s, 31-35 s (1 s flicker at 33 s merges) and 51-53 s.
    melee = set(range(10, 16)) | {31, 32, 34, 35} | set(range(51, 54))
    frames = [_frame(second, second in melee) for second in range(60)]
    (tmp_path / "replay.jsonl").write_text("".join(json.dumps(f) + "\n" for f in frames))
    records = [
        {"kind": "decision", "request": "r1", "orders": [{"unit": "f1", "type": "move"}]},
        {"kind": "ack", "request": "r1",
         "ack": {"applied_ms": 13000, "results": [{"index": 1, "ok": True}]}},
        # An attack on another unit inside the second engagement is not a pull-out, nor is
        # a refused move, nor a move in the last engagement (no charge follows it).
        {"kind": "decision", "request": "r2", "orders": [{"unit": "f1", "type": "attack"},
                                                         {"unit": "f1", "type": "move"}]},
        {"kind": "ack", "request": "r2", "ack": {"applied_ms": 32000, "results": [
            {"index": 1, "ok": True}, {"index": 2, "ok": False}]}},
        {"kind": "decision", "request": "r3", "orders": [{"unit": "f1", "type": "move"}]},
        {"kind": "ack", "request": "r3",
         "ack": {"applied_ms": 52000, "results": [{"index": 1, "ok": True}]}},
    ]
    (tmp_path / "trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    assert cycles(tmp_path) == 1


def test_controller_failures_forfeit_while_game_failures_and_operator_stops_are_rerun():
    assert outcome({"status": "won", "ended_by": "engine_result"}) == "won"
    assert outcome({"status": "won", "ended_by": "time_limit"}) == "lost"
    for status, error in [("policy_failure", "No valid reply after declared retries"),
                          ("policy_failure", "decide: KeyError: 'terrain'"),
                          ("truncated", "no observation after seq 8573")]:
        assert outcome({"status": status, "battle": "b", "error": error}) == "forfeit"
    for episode in [{"status": "policy_failure", "battle": "b",
                     "error": "decide: APIError: HTTP 402: credits"},
                    {"status": "policy_failure", "error": "controller construction: no key"},
                    {"status": "budget_exhausted", "battle": "b"},
                    {"status": "infrastructure_failure", "battle": "b"},
                    {"status": "interrupted", "battle": "b"}]:
        assert outcome(episode) == "excluded"


def test_one_foil_win_fails_the_card_whatever_the_witness_did():
    card = CARDS["chariot"]

    def rows(result, count):
        return [{"outcome": result, "cycles": 3, "setup": "s", "source": "x"}] * count
    cells = {(foil, 0, 0): rows("lost", 10) for foil in card["foils"]}
    cells.update({key: rows("won", 5) for key in card["witnesses"]})
    assert verdict(card, cells)[-1] == "Verdict: admitted"
    cells[("rush_nearest", 0, 0)] = rows("lost", 9) + rows("won", 1)
    assert "rush_nearest won 1 of 10" in verdict(card, cells)[-1]
    # A foil's forfeit is no launch.
    cells[("rush_nearest", 0, 0)] = rows("lost", 9) + rows("forfeit", 1)
    assert "rush_nearest has 9 of 10 launches" in verdict(card, cells)[-1]


def test_a_replacement_plan_naming_the_same_output_counts_its_job_once(tmp_path):
    for name in ("01-x.json", "01b-x.json"):
        (tmp_path / name).write_text(json.dumps({"jobs": [{"output": "runs/b/job-l1"}]}))
    (tmp_path / "01-x-state.json").write_text("{}")

    assert [str(path) for path in jobs([tmp_path])] == ["runs/b/job-l1"]


def _job(tmp_path, name, episodes, **manifest):
    job = tmp_path / name
    job.mkdir()
    (job / "manifest.json").write_text(json.dumps({
        "scenario": {"name": CARDS["chariot"]["scenario"], "map": "m"},
        "config": {"interval_ms": 0, "provider": "openrouter", "model": "gpt-6-sol",
                   "effort": "low"},
        "deployment": {"steam_build_id": "b", "pack": {"sha256": "p"}},
        "episodes": episodes, **manifest}))
    return job


def _episode(index, policy, status, **fields):
    return {"episode": f"episode-{index:04d}", "policy": policy, "status": status,
            "ended_by": "engine_result", "battle": "b", "card": {"source_sha256": "s"},
            **fields}


def test_a_launch_counts_each_controller_once_and_names_a_model_row_by_its_model(tmp_path):
    job = _job(tmp_path, "job-l1", [
        _episode(0, "attack_nearest", "lost"),
        _episode(1, "attack_nearest", "won"),  # the rematch replays the same instance
        _episode(2, "llm_rules", "lost", delays_ms=[2700, 300, 600]),
    ], llm_rules_prompt_sha256="prompt1")

    rows, skipped = battles(CARDS["chariot"], [job])

    assert skipped == 1
    assert [(row["controller"], row["outcome"]) for row in rows] == [
        ("attack_nearest", "lost"), ("llm_rules@gpt-6-sol/low", "lost")]
    assert rows[0]["source"] == ("s", None) and rows[1]["source"] == ("s", "prompt1")
    assert (rows[1]["age_p50_s"], rows[1]["age_p90_s"]) == (0.6, 2.7)


def test_the_board_lists_unrun_plans_and_judges_only_cells_with_controls(tmp_path):
    plans = tmp_path / "plans"
    plans.mkdir()
    model = _job(tmp_path, "glm-l1", [_episode(0, "llm_rules@z-ai/glm-5.3/low", "lost")])
    (plans / "01-glm.json").write_text(json.dumps({"jobs": [{"output": str(model)}]}))
    (plans / "02-foil.json").write_text(
        json.dumps({"jobs": [{"output": str(tmp_path / "foil-l1")}]}))

    text = board("chariot", [plans])

    assert "llm_rules@z-ai/glm-5.3/low" in text and "planned, not run: foil-l1" in text
    assert "Verdict" not in text
    _job(tmp_path, "foil-l1", [_episode(0, "attack_nearest", "lost")])
    assert "Verdict: not admitted: attack_nearest has 1 of 10 launches" in board("chariot", [plans])
