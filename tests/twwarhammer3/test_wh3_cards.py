import json
import re

from gameai.provenance import REPO_ROOT
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


def _rows(result, count, cycles=3, started=""):
    return [{"outcome": result, "cycles": cycles, "setup": "s", "source": "x",
             "started": started}] * count


def test_one_foil_win_fails_the_card_whatever_the_witness_did():
    card = CARDS["chariot"]
    cells = {(foil, 0, 0): _rows("lost", 10) for foil in card["foils"]}
    cells.update({key: _rows("won", 5) for key in card["witnesses"]})
    assert verdict(card, cells)[-1] == "Verdict: admitted"
    cells[("rush_nearest", 0, 0)] = _rows("lost", 9) + _rows("won", 1)
    assert "rush_nearest won 1 of 10" in verdict(card, cells)[-1]
    # A foil's forfeit is no launch.
    cells[("rush_nearest", 0, 0)] = _rows("lost", 9) + _rows("forfeit", 1)
    assert "rush_nearest has 9 of 10 launches" in verdict(card, cells)[-1]


def test_the_witness_is_judged_on_its_first_launches_and_a_win_needs_a_replay():
    card = CARDS["chariot"]
    cells = {(foil, 0, 0): _rows("lost", 10) for foil in card["foils"]}
    witness = next(iter(card["witnesses"]))
    # 4 wins among 20 launches is not 4 of 5: the first five to start (2 lost, 3 won)
    # decide, whatever order the jobs are listed in.
    cells[witness] = (_rows("won", 4, started="03:00") + _rows("lost", 2, started="01:00")
                      + _rows("lost", 14, started="05:00"))
    assert "won 3 of 5, needs 4" in verdict(card, cells)[-1]
    cells[witness] = _rows("won", 4, cycles=None) + _rows("lost", 1)
    assert "a win has no replay" in verdict(card, cells)[-1]
    cells[witness] = _rows("won", 4) + _rows("lost", 16)
    assert verdict(card, cells)[-1] == "Verdict: admitted"


def test_a_replacement_plan_naming_the_same_output_counts_its_job_once(tmp_path):
    for name in ("01-x.json", "01b-x.json"):
        (tmp_path / name).write_text(json.dumps({"jobs": [{"output": "runs/b/job-l1"}]}))
    (tmp_path / "01-x-state.json").write_text("{}")

    assert [str(path) for path in jobs([tmp_path])] == ["runs/b/job-l1"]


def _job(tmp_path, name, episodes, config=None, **manifest):
    job = tmp_path / name
    job.mkdir()
    (job / "manifest.json").write_text(json.dumps({
        "scenario": {"name": CARDS["chariot"]["scenario"], "map": "m"},
        "config": {"interval_ms": 0, "provider": "openrouter", "model": "gpt-6-sol",
                   "effort": "low", "observe_ms": 1000, "tick_ms": 250, **(config or {})},
        "deployment": {"steam_build_id": "b", "pack": {"sha256": "p"}},
        "episodes": episodes, **manifest}))
    return job


def _episode(index, policy, status, **fields):
    return {"episode": f"episode-{index:04d}", "policy": policy, "status": status,
            "ended_by": "engine_result", "battle": "b", "card": {"source_sha256": "s"},
            **fields}


def _served(job, index, model):
    """A trace whose one model call the provider reported serving with ``model``."""
    episode = job / f"episode-{index:04d}"
    episode.mkdir()
    (episode / "trace.jsonl").write_text(json.dumps(
        {"kind": "model_exchange", "attempts": [{"backend_model": model}]}) + "\n")


def test_a_launch_counts_each_controller_once_and_names_a_model_row_by_its_model(tmp_path):
    job = _job(tmp_path, "job-l1", [
        _episode(0, "attack_nearest", "lost"),
        _episode(1, "attack_nearest", "won"),  # the rematch replays the same instance
        _episode(2, "llm_rules", "lost", delays_ms=[2700, 300, 600], battle_s=200,
                 decisions=100),
    ], config={"model_routing": {"gpt-6-sol": {"only": ["x"]}}},
        llm_rules_prompt_sha256="prompt1")
    _served(job, 2, "gpt-6-sol-20261001")

    rows, skipped = battles(CARDS["chariot"], [job])

    assert skipped == 1
    assert [(row["controller"], row["outcome"]) for row in rows] == [
        ("attack_nearest", "lost"), ("llm_rules@gpt-6-sol/low", "lost")]
    assert rows[0]["source"] == ("s", None, "null", ())
    assert rows[1]["source"] == ("s", "prompt1", '{"only": ["x"]}', ("gpt-6-sol-20261001",))
    assert rows[0]["setup"][-2:] == (1000, 250)
    assert (rows[1]["age_p50_s"], rows[1]["age_p90_s"]) == (0.6, 2.7)
    assert rows[1]["info_age_s"] == 0.6 + 200 / 100 / 2 and rows[0]["info_age_s"] is None
    assert "2 controller/age rows from 1 launch (1 rematch" in board("chariot", [job])


def test_launch_identity_uses_the_directory_not_its_basename_or_alias(tmp_path):
    # Each directory is a launch, as in report.collect. Two imported evidence roots can
    # contain the same job name; passing another path to one launch must not add a trial.
    first_root, second_root = tmp_path / "first", tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    first = _job(first_root, "job", [_episode(0, "attack_nearest", "lost"),
                                     _episode(1, "attack_nearest", "won")])
    second = _job(second_root, "job", [_episode(0, "attack_nearest", "won")])
    alias = tmp_path / "alias"
    alias.symlink_to(first, target_is_directory=True)

    rows, skipped = battles(CARDS["chariot"], [first, second, first, alias])

    assert [row["outcome"] for row in rows] == ["lost", "won"]
    assert skipped == 1  # one actual rematch, not duplicate input paths
    assert {row["instance"] for row in rows} == {str(first.resolve()), str(second.resolve())}


def test_a_cell_served_by_two_model_versions_is_starred_but_an_excluded_launch_is_not(tmp_path):
    jobs_ = [_job(tmp_path, f"glm-l{i}", [_episode(0, "llm_rules", "lost")]) for i in (1, 2)]
    _served(jobs_[0], 0, "v-20260816")
    # A launch excluded before its first model call has no served string to compare.
    (jobs_[1] / "manifest.json").write_text(json.dumps({**json.loads(
        (jobs_[1] / "manifest.json").read_text()), "episodes": [
            _episode(0, "llm_rules", "interrupted")]}))
    assert "llm_rules@gpt-6-sol/low*" not in board("chariot", jobs_)
    _served(jobs_[1], 0, "v-20261101")
    (jobs_[1] / "manifest.json").write_text(json.dumps({**json.loads(
        (jobs_[1] / "manifest.json").read_text()), "episodes": [
            _episode(0, "llm_rules", "lost")]}))
    assert "llm_rules@gpt-6-sol/low*" in board("chariot", jobs_)


def test_cells_sort_by_information_age_after_the_foils(tmp_path):
    slow = _job(tmp_path, "slow", [_episode(0, "llm_rules", "lost", delays_ms=[5000],
                                           battle_s=100, decisions=20)])
    fast = _job(tmp_path, "fast", [_episode(
        0, "twwarhammer3.battle.calibration:SnapHitAndRun", "won", delays_ms=[300],
        battle_s=300, decisions=500)])
    foil = _job(tmp_path, "foil", [_episode(0, "rush_nearest", "lost", delays_ms=[300],
                                           battle_s=100, decisions=300)])
    lines = board("chariot", [slow, fast, foil]).splitlines()[3:6]
    assert [line.split()[0] for line in lines] == ["rush_nearest", "SnapHitAndRun",
                                                   "llm_rules@gpt-6-sol/low"]
    assert "0.3/0.3" in lines[1] and lines[1].split()[-1] == "0.6"
    assert "5.0/5.0" in lines[2] and lines[2].split()[-1] == "7.5"


def test_the_board_lists_unrun_plans_and_judges_only_named_directories(tmp_path, monkeypatch):
    plans = tmp_path / "plans"
    plans.mkdir()
    model = _job(tmp_path, "glm-l1", [_episode(0, "llm_rules@z-ai/glm-5.3/low", "lost")])
    later = _job(tmp_path, "glm-v21-l1", [_episode(0, "llm_rules@z-ai/glm-5.3/low", "lost", card={
        "source_sha256": "s", "version": "v21"})])  # another prompt version: its own row
    (plans / "01-glm.json").write_text(json.dumps({"jobs": [{"output": str(model)},
                                                            {"output": str(later)}]}))
    (plans / "02-foil.json").write_text(
        json.dumps({"jobs": [{"output": str(tmp_path / "foil-l1")}]}))

    text = board("chariot", [plans])

    assert "llm_rules@z-ai/glm-5.3/low " in text and "llm_rules v21@z-ai/glm-5.3/low " in text
    assert "*" not in text.split("\n", 3)[3] and "planned, not run: foil-l1" in text
    assert "Verdict" not in text
    _job(tmp_path, "foil-l1", [_episode(0, "attack_nearest", "lost")])
    assert "Verdict: not admitted: attack_nearest has 1 of 10 launches" in board("chariot", [plans])
    # The default board pools every job of the scenario, exploration rounds included, so it
    # is a reading of the evidence, never the pre-registered verdict.
    monkeypatch.setattr("twwarhammer3.battle.cards.JOBS_ROOT", tmp_path)
    assert "attack_nearest" in board("chariot") and "Verdict" not in board("chariot")


def test_the_rules_prompt_withholds_the_card_tactics():
    # The rules prompt (llm_rules) gives objectives and interface, no tactics (empire.md
    # decision 5); the chariot card's knowledge row says it states neither charge bonuses nor
    # cycle charging. A prompt that tells a tactic changes what its card measures.
    # Rests on JUDGEMENT docs/twwarhammer3/controllers.md Scored model arm.
    text = (REPO_ROOT / "configs/twwarhammer3/rules_prompt.md").read_text().lower()
    for stem in ("charg", "cycl", "pull out", "pulls out", "pull-out", "pull back", "withdr",
                 "disengag", "sacrific", "expendab", "tarpit", "flank", "kite", "kiting"):
        assert not re.search(rf"\b{stem}", text), stem  # word starts; "recharge" is ability state
