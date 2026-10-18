"""The command line in twwarhammer3/__main__.py: argument checks and what each command passes
on. The commands' work is tested beside its module."""
import argparse
import json
import sys

import pytest
from wh3_fixtures import configured_job, embedded, make_job

import twwarhammer3.__main__ as cli
from twwarhammer3.__main__ import add_session_arguments, main
from twwarhammer3.battle import play, report
from twwarhammer3.battle.llm import LEDGER_PATH, OPENROUTER_LEDGER_PATH
from twwarhammer3.battle.scripted import Hold
from twwarhammer3.battle.stats import RESULTS_PATH


@pytest.mark.parametrize("arguments", [["--pause"], ["--speed", "0.5"], ["--speed", "2"]])
def test_cli_cannot_request_paused_or_changed_speed_battles(arguments):
    parser = argparse.ArgumentParser()
    add_session_arguments(parser)
    default = parser.parse_args([])
    assert default.speed == 1 and not default.pause
    with pytest.raises(SystemExit):
        parser.parse_args(arguments)


def test_recorder_defaults_on_and_can_be_disabled_independently_of_stills():
    parser = argparse.ArgumentParser()
    add_session_arguments(parser)
    assert parser.parse_args([]).record_replay is True
    args = parser.parse_args(["--no-record-replay", "--stills"])
    assert args.record_replay is False and args.stills is True


@pytest.mark.parametrize("option", [["--model", "gpt-6-lunar"], ["--effort", "minimal"]])
def test_cli_rejects_an_unknown_model_or_effort_before_launch(tmp_path, monkeypatch, capsys,
                                                               option):
    output = tmp_path / "job"
    monkeypatch.setattr(sys, "argv", [
        "twwarhammer3", "play", "--scenario", "random", "--output", str(output), *option])
    with pytest.raises(SystemExit):
        main()
    assert "invalid choice" in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize("policy,error", [
    ("hold@gpt-6-luna", "only commander, llm, llm_rules take @MODEL"),
    ("llm_rules@gpt-6-luna/minimal", "an effort in none, low, medium, high"),
    ("llm_rules,llm_rules@gpt-6-luna", "duplicate controller"),
])
def test_cli_rejects_a_bad_model_suffix_before_launch(tmp_path, monkeypatch, capsys, policy,
                                                      error):
    output = tmp_path / "job"
    monkeypatch.setattr(sys, "argv", ["twwarhammer3", "play", "--scenario", "kho5-dwf5",
                                      "--policy", policy, "--output", str(output)])
    with pytest.raises(SystemExit):
        main()
    assert error in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize("path", [[], ["runs/twwarhammer3/battle/job/episode-0000"]])
def test_watch_next_needs_the_job_directory(monkeypatch, capsys, path):
    monkeypatch.setattr(sys, "argv", ["twwarhammer3", "watch", *path, "--next"])
    with pytest.raises(SystemExit):
        main()
    assert "--next needs the job directory" in capsys.readouterr().err


def test_cli_play_config_has_no_wait_and_the_fixed_ledger_and_register(tmp_path, monkeypatch):
    seen = {}

    def fake_play(output, config, *, makers):
        seen.update(output=output, config=config, makers=makers)
        return {"status": "completed"}

    monkeypatch.setattr(play, "play", fake_play)
    monkeypatch.setattr(sys, "argv", ["twwarhammer3", "play", "--scenario", "kho5-dwf5",
                                      "--policy", "hold", "--output", str(tmp_path / "job")])
    assert main() == 0
    config = seen["config"]
    assert config["interval_ms"] == 0 and config["episodes"] == 1
    assert (config["ledger"], config["results"]) == (str(LEDGER_PATH), str(RESULTS_PATH))
    assert config["episode_timeout"] is None and config["run_timeout"] is None  # derived later
    assert not {"menu", "autostart", "no_menu", "no_autostart", "enabled"} & set(config)
    assert seen["makers"] == {"hold": Hold} and seen["output"] == tmp_path / "job"


def test_cli_openrouter_selects_its_own_ledger_and_default_model(tmp_path, monkeypatch):
    from twwarhammer3.battle import controllers

    seen = {}
    monkeypatch.setattr(controllers, "api_key", lambda provider: "test-only")

    def fake_play(output, config, *, makers):
        seen.update(config)
        assert makers["llm"]().api.provider == "openrouter"
        return {"status": "completed"}

    monkeypatch.setattr(play, "play", fake_play)
    ledger = tmp_path / OPENROUTER_LEDGER_PATH.name  # a stand-in for a fresh clone
    ledger.touch()
    monkeypatch.setattr(cli, "OPENROUTER_LEDGER_PATH", ledger)
    monkeypatch.setattr(sys, "argv", ["wh3", "play", "--provider", "openrouter",
        "--scenario", "kho5-dwf5", "--budget-usd", "50", "--output", str(tmp_path / "job")])
    assert main() == 0
    assert seen["ledger"] == str(ledger)
    assert seen["model"] == "z-ai/glm-5.3" and seen["provider"] == "openrouter"


def test_report_command_prints_the_text_and_saves_text_json_and_html(tmp_path, monkeypatch,
                                                                    capsys):
    a = make_job(tmp_path, "a", [("hold", -.1, "lost"), ("skills", .1, "won")])
    b = make_job(tmp_path, "b", [("hold", -.2, "lost"), ("skills", .1, "won")])
    stem = tmp_path / "reports/nested/pair"
    monkeypatch.setattr(sys, "argv", ["twwarhammer3", "report", str(a), str(b),
                                      "--output", str(stem)])
    assert main() == 0
    text = report.render(report.collect([a, b]))
    assert capsys.readouterr().out == text + "\n"
    assert (tmp_path / "reports/nested/pair.txt").read_text() == text + "\n"
    assert json.loads((tmp_path / "reports/nested/pair.json").read_text()) == json.loads(
        json.dumps(report.collect([a, b])))
    assert "<html" in (tmp_path / "reports/nested/pair.html").read_text()
    monkeypatch.setattr(sys, "argv", ["twwarhammer3", "stats", "--report", str(a)])
    with pytest.raises(SystemExit):
        main()


def test_report_command_collects_once_and_writes_json_text_and_html(tmp_path, monkeypatch,
                                                                    capsys):
    source = report.collect([configured_job(tmp_path, "a")])
    calls = []

    def collect(jobs):
        calls.append(jobs)
        return source

    monkeypatch.setattr(report, "collect", collect)
    stem = tmp_path / "nested/report"
    monkeypatch.setattr("sys.argv", ["wh3", "report", "a", "--output", str(stem)])
    assert main() == 0
    assert len(calls) == 1
    assert json.loads(stem.with_suffix(".json").read_text()) == source
    text = report.render(source)
    assert capsys.readouterr().out == text + "\n"
    assert stem.with_suffix(".txt").read_text().strip() == text
    assert embedded(stem.with_suffix(".html").read_text())["report"]["groups"][0][
        "controllers"] == source["groups"][0]["controllers"]


def test_report_explicit_job_list_includes_failures_and_rejects_an_empty_selection(
        tmp_path, monkeypatch):
    jobs = [make_job(tmp_path, "played", [("hold", 0, "lost")]),
            make_job(tmp_path, "setup-failure", [])]
    selection = tmp_path / "jobs.json"
    selection.write_text(json.dumps([str(path) for path in jobs]))
    stem = tmp_path / "benchmark"
    monkeypatch.setattr(sys, "argv", ["wh3", "report", "--jobs-file", str(selection),
                                      "--output", str(stem)])
    assert main() == 0
    data = json.loads(stem.with_suffix(".json").read_text())
    assert [job["instance"] for job in data["jobs"]] == [str(path) for path in jobs]
    selection.write_text('[]')
    with pytest.raises(SystemExit):
        main()
    selection.write_text('{"jobs": []}')
    with pytest.raises(SystemExit):
        main()
