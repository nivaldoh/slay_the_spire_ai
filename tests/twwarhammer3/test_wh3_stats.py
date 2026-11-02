import csv
import json

import pytest

from gameai.llm import PRICES
from twwarhammer3.battle import digest, stats


@pytest.mark.parametrize("name,harness", [
    ("llm-luna-v15-kho-20261014", "15"),
    ("bench-b1-20261015", ""),
])
def test_a_row_rounds_the_active_shares_and_takes_the_harness_from_the_name(tmp_path, name,
                                                                           harness):
    job = tmp_path / name
    (job / "episode-0000").mkdir(parents=True)
    (job / "manifest.json").write_text(json.dumps({
        "created_at": "2026-10-15T00:00:00", "source_revision": "abc1234def",
        "config": {"policy": "llm", "model": "gpt-6-luna", "effort": "low"}}))
    (job / "episode-0000/result.json").write_text(json.dumps({"status": "won", "final": {
        "friendly": {"men": 60, "men0": 197, "active_men": 59},
        "enemy": {"men": 0, "men0": 90, "active_men": 0}, "objectives": []}}))
    row = stats.row(job, job / "episode-0000")
    assert (row["harness"], row["model"], row["own_left"], row["own_active"]) == (
        harness, "gpt-6-luna", 0.3, 0.299)
    assert row["enemy_active"] == 0.0 and row["victory_held"] == ""


def test_a_rotated_model_is_the_base_policy_with_its_model_and_effort_in_the_register(
        tmp_path, request):
    # Restore the whole table in its order: monkeypatch.delitem would put the price back last,
    # and the Spire CLI lists models in this order.
    request.addfinalizer(lambda saved=dict(PRICES): (PRICES.clear(), PRICES.update(saved)))
    del PRICES["gpt-6-luna"]  # retired since: readers never check prices
    job = tmp_path / "bench-b1-20261015"
    job.mkdir()
    (job / "manifest.json").write_text(json.dumps({
        "created_at": "2026-10-15T00:00:00", "source_revision": "abc1234def", "status": "done",
        "config": {"policy": "llm_rules,llm_rules@gpt-6-luna/medium,hold", "model": "gpt-6-sol",
                   "effort": "low", "scenario": "s"}}))
    register = tmp_path / "results.csv"
    for index, policy in enumerate(("llm_rules", "llm_rules@gpt-6-luna/medium", "hold")):
        episode = job / f"episode-{index:04d}"
        episode.mkdir()
        (episode / "result.json").write_text(json.dumps({"status": "won", "policy": policy}))
        stats.record(register, job, episode)
    with register.open() as handle:
        assert handle.readline().strip() == ",".join(stats.FIELDS)
    rows = [stats.row(job, job / f"episode-{index:04d}") for index in range(3)]
    assert [(row["policy"], row["model"], row["effort"]) for row in rows] == [
        ("llm_rules", "gpt-6-sol", "low"), ("llm_rules", "gpt-6-luna", "medium"), ("hold", "", "")]
    table = stats.summary(register)
    assert "| s | llm_rules | gpt-6-luna | medium |" in table
    assert "| s | llm_rules | gpt-6-sol | low |" in table
    assert digest.job_digest(job).startswith(
        "bench-b1-20261015: done, policy llm_rules gpt-6-sol/low,"
        "llm_rules@gpt-6-luna/medium gpt-6-luna/medium,hold, scenario s")


def test_the_summary_keeps_arms_of_different_added_age_and_interval_apart(tmp_path):
    register = tmp_path / "results.csv"
    for name, interval_ms, delays in (("bench-b1-20261015", 0, (0, 6000, 0)),
                                      ("bench-b1-20261016", 2000, (0,))):
        job = tmp_path / name
        job.mkdir()
        (job / "manifest.json").write_text(json.dumps({
            "created_at": "2026-10-15T00:00:00", "source_revision": "abc1234def",
            "config": {"policy": "hold", "scenario": "s", "interval_ms": interval_ms}}))
        for index, delay_ms in enumerate(delays):
            episode = job / f"episode-{index:04d}"
            episode.mkdir()
            (episode / "result.json").write_text(json.dumps(
                {"status": "won", "policy": "hold", "delay_ms": delay_ms}))
            stats.record(register, job, episode)
    header, _, *rows = stats.summary(register).splitlines()
    column = [cell.strip() for cell in header.split("|")].index("Episodes")
    assert sorted(row.split("|")[column].strip() for row in rows) == ["1", "1", "2"]


def test_a_blank_added_age_joins_the_zero_age_arm(tmp_path):
    # Rows before b1 leave added age blank and their episodes added none (stats.py's summary
    # comment), so a blank row and a 0 s row of one condition are one group.
    register = tmp_path / "results.csv"
    blank = dict.fromkeys(stats.FIELDS, "")
    rows = [{**blank, "scenario": "s", "policy": "hold", "outcome": "won", "interval_s": "0",
             "added_age_s": age} for age in ("", "0.0")]
    with register.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, stats.FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    header, _, *body = stats.summary(register).splitlines()
    assert len(body) == 1 and "| 0/0 | 2 | 2 |" in body[0]


def test_the_summary_keeps_draws_providers_and_unrecorded_delays_apart(tmp_path):
    # Planted wrong versions (runs/readers-planted-20261029/) passed every test above.
    register = tmp_path / "results.csv"
    base = {**dict.fromkeys(stats.FIELDS, ""), "scenario": "s", "policy": "llm", "model": "m",
            "added_age_s": "0", "interval_s": "0"}
    rows = [{**base, "outcome": "draw", "delay_s": "2.0"}, {**base, "outcome": "won"},
            {**base, "outcome": "won", "provider": "openrouter"}]
    with register.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, stats.FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    header, _, *body = stats.summary(register).splitlines()
    names = [cell.strip() for cell in header.split("|")]
    table = {cells[names.index("Model")]: cells for cells in
             ([cell.strip() for cell in row.split("|")] for row in body)}
    assert sorted(table) == ["m", "m (OpenRouter)"]
    row = {name: table["m"][names.index(name)]
           for name in ("Episodes", "Won", "Lost", "Draw", "Mean delay s")}
    assert row == {"Episodes": "2", "Won": "1", "Lost": "0", "Draw": "1", "Mean delay s": "2.0"}


def test_a_timer_ending_keeps_the_engine_status_and_says_how_it_ended(tmp_path):
    # The register stores the engine's status; readers that score timer wins otherwise read
    # ended_by (cards.outcome, report.collect).
    job = tmp_path / "bench-b25-20261017"
    (job / "episode-0000").mkdir(parents=True)
    (job / "manifest.json").write_text(json.dumps({
        "created_at": "2026-10-17T00:00:00", "source_revision": "abc1234def",
        "config": {"policy": "hold"}}))
    (job / "episode-0000/result.json").write_text(json.dumps({
        "status": "won", "ended_by": "time_limit", "battle_ms": 1205200}))
    row = stats.row(job, job / "episode-0000")
    assert (row["outcome"], row["ended_by"], row["battle_s"]) == ("won", "time_limit", 1205)


def test_a_row_records_the_mean_order_delay_in_seconds(tmp_path):
    job = tmp_path / "bench-b1-20261015"
    (job / "episode-0000").mkdir(parents=True)
    (job / "manifest.json").write_text(json.dumps({
        "created_at": "2026-10-15T00:00:00", "source_revision": "abc1234def",
        "config": {"policy": "hold"}}))
    (job / "episode-0000/result.json").write_text(json.dumps(
        {"status": "won", "delays_ms": [400, 800, 1300]}))
    # Rests on JUDGEMENT src/twwarhammer3/battle/play.py Delay: delay_s is the mean of
    # delays_ms (a median would give 0.8).
    assert stats.row(job, job / "episode-0000")["delay_s"] == 0.83


def test_a_row_writes_the_date_short_source_and_seconds_columns_at_the_registers_precision(
        tmp_path):
    # Hand-worked against the committed register's format (docs/twwarhammer3/results.csv, e.g.
    # "2026-10-13,llm-luna-v1-20261013,...,b615830,realtime,1.0,5.0,won,446,,,44,0,4.23,0.0124"):
    # the manifest's date, a 7-character revision, seconds, whole battle seconds, delays to
    # 0.01 s and dollars to 0.0001.
    job = tmp_path / "llm-luna-v1-20261013"
    (job / "episode-0000").mkdir(parents=True)
    (job / "manifest.json").write_text(json.dumps({
        "created_at": "2026-10-13T21:04:05.123456+00:00",
        "source_revision": "b6158303f5a6c1e2d9b8a7f6e5d4c3b2a1f0e9d8",
        "config": {"policy": "llm", "model": "gpt-6-luna", "effort": "low",
                   "scenario": "kho5-dwf5", "speed": 1.0, "pause": False, "interval_ms": 2500}}))
    (job / "episode-0000/result.json").write_text(json.dumps({
        "episode": "episode-0000", "status": "won", "policy": "llm", "decisions": 44,
        "invalid": 0, "delays_ms": [8000, 9880], "delay_ms": 0, "battle_ms": 445600,
        "llm": {"calls": 44, "usd": 0.012449}}))
    row = stats.row(job, job / "episode-0000")
    assert {key: row[key] for key in ("date", "source", "interval_s", "battle_s", "delay_s",
                                      "usd")} == {
        "date": "2026-10-13", "source": "b615830", "interval_s": 2.5,
        "battle_s": 446,  # 445.6 s to the nearest second
        "delay_s": 8.94,  # (8000 + 9880) / 2 ms
        "usd": 0.0124,  # 0.012449 to four places
    }


def test_a_scripted_row_records_no_cost_and_the_registers_units(tmp_path):
    # A scripted controller's result has "llm": {} (play.py: its policy has no totals); the
    # register's scripted rows record usd 0 (results.csv, attack-m3-20261013). Active shares go
    # to 3 places, as own_active does: 2 / 7 = 0.2857 -> 0.286. delay_ms 6000 is
    # --delay-seconds 6 (controllers.rotation).
    job = tmp_path / "hold-b9-20261015"
    (job / "episode-0000").mkdir(parents=True)
    (job / "manifest.json").write_text(json.dumps({
        "created_at": "2026-10-15T00:00:00", "source_revision": "abc1234def",
        "config": {"policy": "hold", "interval_ms": 0}}))
    (job / "episode-0000/result.json").write_text(json.dumps({
        "status": "lost", "policy": "hold", "decisions": 3, "invalid": 0, "delay_ms": 6000,
        "llm": {}, "final": {"friendly": {"men": 4, "men0": 7, "active_men": 3},
                             "enemy": {"men": 5, "men0": 7, "active_men": 2}}}))
    row = stats.row(job, job / "episode-0000")
    assert (row["usd"], row["enemy_active"], row["added_age_s"]) == (0, 0.286, 6.0)
