"""`spire play` and `spire spend` per provider: the ledger, the recorded config and the
model and effort checks. The play loop itself is tested in test_play.py."""

import json
import sys

import pytest

from gameai import llm
from spire.__main__ import main
from spire.fullrun import play
from spire.fullrun.llm import LEDGER_PATH, LEDGERS, OPENROUTER_LEDGER_PATH


def run(monkeypatch, *arguments):
    monkeypatch.setattr(sys, "argv", ["spire", *arguments])
    return main()


@pytest.mark.parametrize(("arguments", "provider", "ledger"), [
    (["--model", "gpt-6-luna"], "openai", LEDGER_PATH),
    (["--provider", "openrouter", "--model", "qwen/qwen3.6-35b-a3b", "--effort", "none"],
     "openrouter", OPENROUTER_LEDGER_PATH),
])
def test_play_charges_the_providers_ledger_and_records_the_provider(
        tmp_path, monkeypatch, arguments, provider, ledger):
    assert LEDGERS[provider] == ledger
    ledger = tmp_path / ledger.name  # a stand-in, so a fresh clone without runs/ passes
    ledger.touch()
    monkeypatch.setitem(LEDGERS, provider, ledger)
    seen = {}
    monkeypatch.setattr(llm, "api_key", lambda name: seen.setdefault("key", name))

    def fake_play(output, config, *, policy_factory):
        seen.update(output=output, config=config, api=policy_factory().api)
        return {"status": "completed"}

    monkeypatch.setattr(play, "play", fake_play)
    assert run(monkeypatch, "play", *arguments, "--seed", "ABC", "--budget-usd", "1",
               "--output", str(tmp_path / "job")) == 0
    config = seen["config"]
    assert seen["key"] == provider and seen["output"] == tmp_path / "job"
    assert config["provider"] == provider and config["ledger"] == str(ledger)
    assert "output" not in config and "command" not in config
    assert seen["api"].provider == provider and seen["api"].ledger.path == ledger


def test_play_ledger_override_and_spend_read_the_named_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(llm, "api_key", lambda name: "test-only")
    seen = {}
    monkeypatch.setattr(play, "play", lambda output, config, *, policy_factory: seen.update(
        config) or {"status": "completed"})
    path = tmp_path / "spend.jsonl"
    path.write_text(json.dumps({"usd": 0.25}) + "\n" + json.dumps({"usd": 0.5}) + "\n")
    assert run(monkeypatch, "play", "--provider", "openrouter", "--model",
               "qwen/qwen3.6-35b-a3b", "--effort", "medium", "--seed", "ABC", "--budget-usd",
               "1", "--ledger", str(path), "--output", str(tmp_path / "job")) == 0
    assert seen["ledger"] == str(path) and capsys.readouterr().out.startswith("Evidence: ")
    assert run(monkeypatch, "spend", "--provider", "openrouter", "--ledger", str(path)) == 0
    assert capsys.readouterr().out == f"$0.7500 spent ({path})\n"
    assert run(monkeypatch, "spend", "--provider", "openrouter") == 0
    assert capsys.readouterr().out.endswith(f" spent ({OPENROUTER_LEDGER_PATH})\n")


def test_play_refuses_a_missing_ledger_before_any_job(tmp_path, monkeypatch, capsys):
    # A mistyped --ledger, or a job started from a worktree, would otherwise start at $0.
    monkeypatch.setattr(llm, "api_key", lambda name: pytest.fail("read a key"))
    monkeypatch.setattr(play, "play", lambda *args, **kwargs: pytest.fail("started a job"))
    with pytest.raises(SystemExit) as error:
        run(monkeypatch, "play", "--model", "gpt-6-luna", "--seed", "ABC", "--budget-usd", "1",
            "--ledger", str(tmp_path / "typo.jsonl"), "--output", str(tmp_path / "job"))
    assert error.value.code == 2 and "No spend ledger at" in capsys.readouterr().err
    assert not (tmp_path / "typo.jsonl").exists() and not (tmp_path / "job").exists()


@pytest.mark.parametrize(("arguments", "message"), [
    (["--model", "qwen/qwen3.6-35b-a3b", "--effort", "none"],
     "invalid choice for openai: use a policy with a model in gpt-6-luna"),
    (["--provider", "openrouter", "--model", "gpt-6-luna"],
     "invalid choice for openrouter: use a policy with a model in z-ai/glm-5.3"),
    (["--provider", "openrouter", "--model", "qwen/qwen3.6-35b-a3b", "--effort", "low"],
     "invalid choice for openrouter qwen/qwen3.6-35b-a3b: use an effort in none, medium"),
    (["--model", "gpt-6-astra", "--effort", "none"],
     "invalid choice for openai gpt-6-astra: use an effort in low,"),
])
def test_play_refuses_a_model_or_effort_its_provider_lacks_before_any_job(
        tmp_path, monkeypatch, capsys, arguments, message):
    monkeypatch.setattr(llm, "api_key", lambda name: pytest.fail("read a key"))
    monkeypatch.setattr(play, "play", lambda *args, **kwargs: pytest.fail("started a job"))
    with pytest.raises(SystemExit) as error:
        run(monkeypatch, "play", *arguments, "--seed", "ABC", "--budget-usd", "1",
            "--output", str(tmp_path / "job"))
    assert error.value.code == 2 and message in capsys.readouterr().err
    assert not (tmp_path / "job").exists()
