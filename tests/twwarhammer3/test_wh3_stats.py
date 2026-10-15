import json

import pytest

from twwarhammer3.battle import stats


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
