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


@pytest.mark.parametrize("battle,outcome,status", [
    (False, "done", 0), (True, "done", 0), (False, "failed", 1),
    (True, "failed", 1), (False, "foreign", 1), (False, "timeout", 1),
])
def test_menu_waits_for_its_own_completion_and_returns_failure_on_timeout(
        tmp_path, monkeypatch, capsys, battle, outcome, status):
    from twwarhammer3.engine import runtime
    from twwarhammer3.engine.mailbox import Mailbox

    monkeypatch.setattr(runtime, "BRIDGE_DIR", tmp_path)
    (tmp_path / "session.json").write_text(json.dumps({"job": "live"}))
    steps = tmp_path / "steps.json"
    steps.write_text('[{"log": "probe"}]')
    publish = Mailbox.write_menu

    def answer(box, steps):
        request = publish(box, steps)
        if outcome != "timeout":
            terminal = "done" if outcome == "foreign" else outcome
            identity = "unrelated" if outcome == "foreign" else request
            line = f"menu {identity}: {terminal}\n"
            (tmp_path / ("mod.log" if battle else "menu.log")).write_text(line)
        return request

    monkeypatch.setattr(Mailbox, "write_menu", answer)
    clock = iter([0, 0, 2])
    monkeypatch.setattr(cli.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    monkeypatch.setattr(sys, "argv", ["wh3", "menu", "--steps", str(steps), "--wait", "1",
                                      *(["--battle"] if battle else [])])
    assert main() == status
    if outcome in ("foreign", "timeout"):
        assert "timed out" in capsys.readouterr().err


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
    ("hold@gpt-6-luna", "only commander, llm, llm_rules, team_llm_rules take @MODEL"),
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


# Before LEDGERS, every provider but OpenRouter charged the OpenAI ledger.
@pytest.mark.parametrize("provider,model,ledger", [
    ("openrouter", "z-ai/glm-5.3", OPENROUTER_LEDGER_PATH),
    ("anthropic", "claude-haiku-5-5", LEDGER_PATH.with_name("anthropic-spend.jsonl")),
])
def test_cli_provider_selects_its_own_ledger_and_default_model(tmp_path, monkeypatch, capsys,
                                                               provider, model, ledger):
    from twwarhammer3.battle import controllers

    seen = {}
    monkeypatch.setattr(controllers, "api_key", lambda provider: "test-only")

    def fake_play(output, config, *, makers):
        seen.update(config)
        assert makers["llm"]().api.provider == provider
        return {"status": "completed"}

    monkeypatch.setattr(play, "play", fake_play)
    assert cli.LEDGERS[provider] == ledger
    ledger = tmp_path / ledger.name  # a stand-in for a fresh clone
    ledger.touch()
    monkeypatch.setitem(cli.LEDGERS, provider, ledger)
    monkeypatch.setattr(sys, "argv", ["wh3", "play", "--provider", provider,
        "--scenario", "kho5-dwf5", "--budget-usd", "50", "--output", str(tmp_path / "job")])
    assert main() == 0
    assert seen["ledger"] == str(ledger)
    assert seen["model"] == model and seen["provider"] == provider
    monkeypatch.setattr(sys, "argv", ["wh3", "spend", "--provider", provider])
    assert main() == 0
    assert capsys.readouterr().out.endswith(f" spent ({ledger})\n")


# A worktree has no runs/ and a typo names no file: both used to print $0.0000 spent.
@pytest.mark.parametrize("typed", [True, False])
def test_spend_refuses_a_ledger_that_does_not_exist(tmp_path, monkeypatch, capsys, typed):
    missing = tmp_path / "antropic-spend.jsonl"
    monkeypatch.setitem(cli.LEDGERS, "anthropic", missing)
    monkeypatch.setattr(sys, "argv", ["wh3", "spend", "--provider", "anthropic",
                                      *(["--ledger", str(missing)] if typed else [])])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert f"No spend ledger at {missing}" in captured.err and captured.out == ""
    assert not missing.exists()


@pytest.mark.parametrize("make_jobs", [
    pytest.param(lambda root: [
        make_job(root, "a", [("hold", -.1, "lost"), ("skills", .1, "won")]),
        make_job(root, "b", [("hold", -.2, "lost"), ("skills", .1, "won")]),
    ], id="scripted-pair"),
    pytest.param(lambda root: [configured_job(root, "a")], id="model"),
])
def test_report_command_collects_once_prints_text_and_saves_text_json_and_html(
        tmp_path, monkeypatch, capsys, make_jobs):
    jobs = make_jobs(tmp_path)
    source = report.collect(jobs)
    real_collect = report.collect
    calls = []

    def collect(jobs):
        calls.append(jobs)
        return real_collect(jobs)

    monkeypatch.setattr(report, "collect", collect)
    stem = tmp_path / "reports/nested/pair"
    monkeypatch.setattr(sys, "argv", ["twwarhammer3", "report", *map(str, jobs),
                                      "--output", str(stem)])
    assert main() == 0
    assert calls == [jobs]
    text = report.render(source)
    assert capsys.readouterr().out == text + "\n"
    assert stem.with_suffix(".txt").read_text() == text + "\n"
    assert json.loads(stem.with_suffix(".json").read_text()) == json.loads(json.dumps(source))
    html = stem.with_suffix(".html").read_text()
    assert "<html" in html
    assert [group["controllers"] for group in embedded(html)["report"]["groups"]] == [
        group["controllers"] for group in source["groups"]]


def test_stats_rejects_the_report_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["twwarhammer3", "stats", "--report", "a"])
    with pytest.raises(SystemExit):
        main()


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


def test_compare_peers_prints_the_summary_and_reports_a_refusal_as_a_usage_error(
        tmp_path, monkeypatch, capsys):
    from twwarhammer3.battle import peers

    monkeypatch.setattr(peers, "compare", lambda path: {"attempt": str(path)})
    monkeypatch.setattr(sys, "argv", ["wh3", "compare-peers", str(tmp_path)])
    assert main() == 0
    assert json.loads(capsys.readouterr().out) == {"attempt": str(tmp_path)}

    def refuse(path):
        raise ValueError("client A's events hold more than one battle id")

    monkeypatch.setattr(peers, "compare", refuse)
    with pytest.raises(SystemExit) as stopped:
        main()
    assert stopped.value.code == 2
    assert "more than one battle id" in capsys.readouterr().err


@pytest.mark.parametrize("command", [["digest"], ["report", "--output", "out"]])
def test_a_mistyped_job_path_is_a_one_line_error(tmp_path, monkeypatch, capsys, command):
    """2026-11-08 audit U11. Wrong version: a FileNotFoundError traceback on manifest.json."""
    missing = tmp_path / "nosuchjob"
    argv = [command[0], str(missing), *command[1:]]
    monkeypatch.setattr(sys, "argv", ["wh3", *argv])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert f"no job or episode directory at {missing}" in captured.err
    assert "Traceback" not in captured.err and not (tmp_path / "out.html").exists()


def test_digest_and_report_still_take_an_existing_job_and_plan(tmp_path, monkeypatch, capsys):
    """The missing-path checks must not refuse real inputs (2026-11-13 review). Wrong versions:
    digest or report wanting a file, or --benchmark-plan wanting a directory."""
    from twwarhammer3.battle import digest, report_html
    job, plan = tmp_path / "job", tmp_path / "plan.json"
    job.mkdir()
    plan.write_text("{}")
    monkeypatch.setattr(digest, "digest", lambda path: f"digest of {path.name}")
    monkeypatch.setattr(sys, "argv", ["wh3", "digest", str(job)])
    assert main() == 0 and "digest of job" in capsys.readouterr().out
    seen = []
    monkeypatch.setattr(report, "collect", lambda jobs, **kw: seen.append((jobs, kw)) or {})
    monkeypatch.setattr(report, "render", lambda data: "rendered")
    monkeypatch.setattr(report_html, "write", lambda path, data: None)
    monkeypatch.setattr(sys, "argv", ["wh3", "report", str(job), "--benchmark-plan", str(plan),
                                      "--output", str(tmp_path / "out")])
    assert main() == 0 and seen == [([job], {"benchmark_plans": [plan]})]
