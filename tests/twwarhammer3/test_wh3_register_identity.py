"""Register and report identity: one configuration and one reserve case per row or controller.

Jobs come from the real job loop (wh3_fixtures.played_job), so manifests, draws, cards and register
rows are the producers' own; only the battle is stubbed.
"""

import csv
import hashlib
import json
from pathlib import Path

from wh3_fixtures import played_job, team_job

from twwarhammer3.battle import cannae, report, setup, stats

WING_SUPPORT = "twwarhammer3.battle.cannae:WingSupport"


def register_rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def summary_rows(path):
    header, _, *body = stats.summary(path).splitlines()
    names = [cell.strip() for cell in header.split("|")]
    return [dict(zip(names, (cell.strip() for cell in line.split("|")))) for line in body]


def test_each_episode_of_a_reserve_job_records_its_own_draw(tmp_path, monkeypatch):
    # Root seed 106 draws these two cases first, as in the saved b3 jobs' manifests. Stamping
    # draws[0] on both rows would hide that WingSupport won one and lost the other.
    played_job(tmp_path / "b3-support-01", monkeypatch, [{"status": "won"}, {"status": "lost"}],
               policy=WING_SUPPORT, reserve_seed=106)
    assert [row["case"] for row in register_rows(tmp_path / "results.csv")] == [
        "outside/south/2", "centre/north/2"]
    assert [(row["Scenario"], row["Won"], row["Lost"])
            for row in summary_rows(tmp_path / "results.csv")] == [
        ("emp-envelopment-b-v3 centre/north/2", "0", "1"),
        ("emp-envelopment-b-v3 outside/south/2", "1", "0")]


def test_an_external_row_carries_the_hash_of_its_class_file(tmp_path, monkeypatch):
    played_job(tmp_path / "b3-support-01", monkeypatch, policy=WING_SUPPORT, reserve_seed=106)
    expected = hashlib.sha256(Path(cannae.__file__).read_bytes()).hexdigest()[:12]
    assert register_rows(tmp_path / "results.csv")[0]["configuration"] == expected


def test_a_configured_row_names_its_members_declarations_and_never_the_job_flags(
        tmp_path, monkeypatch):
    # Both jobs pass Haiku flags; only the smoke has model members. The digests are the two
    # saved jobs' (c-slow-probe-01, c-model-smoke-02). A summary keyed as before pooled these
    # two into one row: 2 battles, 1 won, $0.94, no model named.
    team_job(tmp_path / "c-slow-probe-01", monkeypatch, "cannae-local-slow-probe")
    team_job(tmp_path / "c-model-smoke-02", monkeypatch, "cannae-local-model", status="lost",
             llm={"usd": .9382})
    register = tmp_path / "results.csv"
    assert [(row["job"], row["configuration"], row["model"], row["effort"], row["provider"],
             row["case"]) for row in register_rows(register)] == [
        ("c-slow-probe-01", "798ff9dca844", "", "", "", ""),
        ("c-model-smoke-02", "dcea16e551ab", "claude-haiku-5-5", "low", "anthropic", "")]
    assert sorted((row["Policy"], row["Model"], row["USD"]) for row in summary_rows(register)) == [
        ("configured 798ff9dca844", "", "0.00"),
        ("configured dcea16e551ab", "claude-haiku-5-5", "0.94")]


def test_a_team_of_two_models_names_both(tmp_path, monkeypatch):
    # Naming one member's model would let this team pool with a one-model team in the summary.
    spec = json.loads((setup.SCENARIOS_PATH.parent / "controllers/cannae-local-model.json")
                      .read_text())
    spec["members"]["centre"]["type"] = "llm_rules@claude-sonnet-5-5/medium"
    (tmp_path / "two-models.json").write_text(json.dumps(spec))
    team_job(tmp_path / "c-two-models", monkeypatch, tmp_path / "two-models")
    row, = register_rows(tmp_path / "results.csv")
    assert (row["model"], row["effort"], row["provider"]) == (
        "claude-haiku-5-5+claude-sonnet-5-5", "low+medium", "anthropic")


def test_a_model_row_keeps_the_jobs_model_effort_and_provider(tmp_path, monkeypatch):
    # Only configured rows read member cards; every other row has no member to read.
    ledger = tmp_path / "spend.jsonl"
    ledger.touch()
    played_job(tmp_path / "b3-haiku-01", monkeypatch, policy="llm_rules", reserve_seed=106,
               model="claude-haiku-5-5", effort="low", provider="anthropic", ledger=str(ledger),
               budget_usd=1)
    row, = register_rows(tmp_path / "results.csv")
    assert (row["model"], row["effort"], row["provider"]) == (
        "claude-haiku-5-5", "low", "anthropic")


def test_configured_rows_from_before_the_column_stay_apart_by_job(tmp_path):
    # The two committed rows are the pool this change exists for, and no old row is rewritten.
    lines = stats.RESULTS_PATH.read_text().splitlines()
    register = tmp_path / "results.csv"
    register.write_text("\n".join([lines[0], *(
        line for line in lines if ",c-slow-probe-01," in line or ",c-model-smoke-02," in line)])
        + "\n")
    assert [(row["Policy"], row["Won"], row["Lost"]) for row in summary_rows(register)] == [
        ("configured c-model-smoke-02", "0", "1"), ("configured c-slow-probe-01", "1", "0")]


def test_the_next_row_changes_no_committed_register_line(tmp_path, monkeypatch):
    # record() rewrites the whole file when line 1 differs from FIELDS, which would put two
    # commas on all 766 old lines, so a new column edits line 1 in the same commit.
    committed = stats.RESULTS_PATH.read_bytes()
    assert committed.split(b"\n", 1)[0].decode().split(",") == stats.FIELDS
    register = tmp_path / "results.csv"
    register.write_bytes(committed)
    played_job(tmp_path / "b3-hold-01", monkeypatch, policy="hold", reserve_seed=106)
    after = register.read_bytes()
    assert after.startswith(committed) and after[len(committed):].count(b"\n") == 1


def test_two_compositions_with_equal_flags_stay_two_controllers(tmp_path, monkeypatch):
    # Equal flags and revision put both jobs in one group, so only the label keeps a free probe's
    # win from pooling with a paid smoke's loss. The digests are the saved jobs'.
    jobs = [team_job(tmp_path / "c-slow-probe-01", monkeypatch, "cannae-local-slow-probe"),
            team_job(tmp_path / "c-model-smoke-02", monkeypatch, "cannae-local-model",
                     status="lost")]
    group, = report.collect(jobs)["groups"]
    assert {row["controller"]: row["trials"] for row in group["controllers"]} == {
        "configured / +0s / 798ff9dca844": 1, "configured / +0s / dcea16e551ab": 1}


def test_two_versions_of_an_external_class_stay_two_controllers(tmp_path, monkeypatch):
    # Equal flags put both jobs in one group, so only the label keeps the versions apart.
    old = played_job(tmp_path / "b3-support-00", monkeypatch, [{"card": {
        "kind": "external", "source_sha256": "357cc9fa63f5" + "0" * 52}}],
                     policy=WING_SUPPORT, reserve_seed=106)
    new = played_job(tmp_path / "b3-support-01", monkeypatch, policy=WING_SUPPORT, reserve_seed=106)
    current = hashlib.sha256(Path(cannae.__file__).read_bytes()).hexdigest()[:12]
    group, = report.collect([old, new])["groups"]
    assert {row["controller"]: row["trials"] for row in group["controllers"]} == {
        f"{WING_SUPPORT} / +0s / 357cc9fa63f5": 1, f"{WING_SUPPORT} / +0s / {current}": 1}
