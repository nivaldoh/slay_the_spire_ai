"""scripts/wh3_reserve_cells.py: one row per episode and a tally per cell, from saved jobs."""

import importlib.util

import pytest
from wh3_fixtures import played_job

from gameai.provenance import REPO_ROOT

WING_SUPPORT = "twwarhammer3.battle.cannae:WingSupport"
SPEC = importlib.util.spec_from_file_location("wh3_reserve_cells_script",
                                              REPO_ROOT / "scripts/wh3_reserve_cells.py")
script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(script)


def test_each_episode_prints_its_own_case_launch_outcome_and_men(tmp_path, monkeypatch, capsys):
    # The saved b3-rush-01, as a recount of its raw trace read it (audit B-1).
    job = played_job(tmp_path / "b3-rush-01", monkeypatch, [
        {"status": "lost", "battle_ms": 334300, "invalid": 3,
         "final": {"friendly": {"men": 192}, "enemy": {"men": 502}}},
        {"status": "lost", "battle_ms": 498700,
         "final": {"friendly": {"men": 135}, "enemy": {"men": 398}}},
    ], policy="rush_nearest", reserve_seed=106, pid=27548)
    capsys.readouterr()  # the job loop's own progress lines
    script.main([str(job)])
    assert capsys.readouterr().out.splitlines() == [
        "| version | policy | model | effort | harness | mode | age/interval s | case | launch | "
        "outcome | seconds | invalid | own men | enemy men |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        "| emp-envelopment-b-v3 | rush_nearest |  |  | 3667fa3 | realtime | 0/0 | outside/south/2 "
        "| 27548 | lost | 334.3 | 3 | 192 | 502 |",
        "| emp-envelopment-b-v3 | rush_nearest |  |  | 3667fa3 | realtime | 0/0 | centre/north/2 "
        "| 27548 | lost | 498.7 | 0 | 135 | 398 |",
        "",
        "| version | policy | model | effort | harness | mode | age/interval s | case | attempts | "
        "outcomes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        "| emp-envelopment-b-v3 | rush_nearest |  |  | 3667fa3 | realtime | 0/0 | centre/north/2 "
        "| 1 | lost 1 |",
        "| emp-envelopment-b-v3 | rush_nearest |  |  | 3667fa3 | realtime | 0/0 | outside/south/2 "
        "| 1 | lost 1 |",
    ]


def test_the_tally_keeps_versions_apart_and_shows_how_the_timer_ended_a_battle(
        tmp_path, monkeypatch, capsys):
    # Hold won this case on v2 and lost it on v3. A tally by policy and case alone reads 1 of 2.
    # A timer win is an engine win (cannae-comparison.md) and a timer loss is not one.
    jobs = [played_job(tmp_path / name, monkeypatch, [changes], policy="hold", reserve_seed=106,
                       scenario=scenario)
            for name, scenario, changes in (
                ("b2", "emp-envelopment-b-v2", {"status": "won"}),
                ("b3", "emp-envelopment-b-v3", {"status": "lost"}),
                ("b3-timer-win", "emp-envelopment-b-v3",
                 {"status": "won", "ended_by": "time_limit"}),
                ("b3-timer-loss", "emp-envelopment-b-v3",
                 {"status": "lost", "ended_by": "time_limit"}))]
    script.main([str(job) for job in jobs])
    conditions = "hold |  |  | 3667fa3 | realtime | 0/0 | outside/south/2"
    assert capsys.readouterr().out.splitlines()[-2:] == [
        f"| emp-envelopment-b-v2 | {conditions} | 1 | won 1 |",
        f"| emp-envelopment-b-v3 | {conditions} | 3 "
        "| lost 1, lost (time_limit) 1, won (time_limit) 1 |"]


@pytest.mark.parametrize("name, options, changes", [
    ("second", {"model": "gpt-6-luna", "provider": "openai"}, {}),
    ("second", {"effort": "high"}, {}), ("second", {"interval_ms": 5000}, {}),
    ("second", {}, {"delay_ms": 2000}), ("second-v2-job", {}, {}),
], ids=["model", "effort", "interval", "added-age", "harness"])
def test_the_tally_keeps_apart_what_a_summary_row_keeps_apart(
        tmp_path, monkeypatch, capsys, name, options, changes):
    # A win under one condition and a loss under another are two cells, not one of 2.
    ledger = tmp_path / "spend.jsonl"
    ledger.touch()
    flags = dict(policy="llm_rules", model="claude-haiku-5-5", effort="low", provider="anthropic",
                 reserve_seed=106, ledger=str(ledger), budget_usd=1)
    jobs = [played_job(tmp_path / "first", monkeypatch, [{"status": "won"}], **flags),
            played_job(tmp_path / name, monkeypatch, [{"status": "lost", **changes}],
                       **{**flags, **options})]
    capsys.readouterr()  # the job loop's own progress lines
    script.main([str(job) for job in jobs])
    assert sorted(line.split(" | ", 8)[-1] for line in capsys.readouterr().out.splitlines()[-2:]
                  ) == ["1 | lost 1 |", "1 | won 1 |"]


def test_the_tally_keeps_two_versions_of_a_class_file_apart(tmp_path, monkeypatch, capsys):
    # Envelop's file hash moved mid-study; the class name alone would pool its two versions.
    jobs = [played_job(tmp_path / "old", monkeypatch, [{"status": "won", "card": {
                "kind": "external", "source_sha256": "010121d32bb8" + "0" * 52}}],
                       policy=WING_SUPPORT, reserve_seed=106),
            played_job(tmp_path / "new", monkeypatch, [{"status": "lost", "card": {
                "kind": "external", "source_sha256": "357cc9fa63f5" + "0" * 52}}],
                       policy=WING_SUPPORT, reserve_seed=106)]
    capsys.readouterr()  # the job loop's own progress lines
    script.main([str(job) for job in jobs])
    assert [line.split(" | ")[1] for line in capsys.readouterr().out.splitlines()[-2:]] == [
        "WingSupport 010121d32bb8", "WingSupport 357cc9fa63f5"]


def test_a_job_with_no_reserve_draws_stops_the_table_before_it_prints(
        tmp_path, monkeypatch, capsys):
    reserve = played_job(tmp_path / "b3-hold-01", monkeypatch, policy="hold", reserve_seed=106)
    plain = played_job(tmp_path / "a-rush-01", monkeypatch, policy="rush_nearest",
                       scenario="emp-envelopment-a-v1")
    capsys.readouterr()  # the job loop's own progress lines
    with pytest.raises(SystemExit, match="a-rush-01: no reserve_draws"):
        script.main([str(reserve), str(plain)])
    assert capsys.readouterr().out == ""
