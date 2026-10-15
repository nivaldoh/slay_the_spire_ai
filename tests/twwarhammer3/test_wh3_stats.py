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
        tmp_path, monkeypatch):
    monkeypatch.delitem(PRICES, "gpt-6-luna")  # retired since: readers never check prices
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
