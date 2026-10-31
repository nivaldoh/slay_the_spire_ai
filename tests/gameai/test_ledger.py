"""Earlier jobs retain their share of the hard cap (AGENTS.md, Evidence)."""

import json

import pytest

from gameai.ledger import BudgetExhausted, Ledger
from gameai.llm import Model


def test_reopened_ledger_counts_all_earlier_charges_and_reserves_only_the_remainder(tmp_path):
    path = tmp_path / "spend.jsonl"
    history = b'{"usd":0.25,"job":"earlier-a"}\n{"usd":0.5,"job":"earlier-b"}\n'
    path.write_bytes(history)
    ledger = Ledger(path, 1.0, must_exist=True)

    assert ledger.spent == 0.75
    ledger.reserve(0.25)  # Exactly at the cap is permitted.
    with pytest.raises(BudgetExhausted, match="Spent"):
        ledger.reserve(0.125)

    assert ledger.spent == 0.75 and ledger.held == 0.25
    assert path.read_bytes() == history
    ledger.release(0.25)
    ledger.reserve(0.25)  # The failed reservation did not consume any allowance.
    ledger.release(0.25)
    assert ledger.held == 0


def test_earlier_jobs_at_the_cap_prevent_transport_and_preserve_the_ledger(tmp_path):
    path = tmp_path / "spend.jsonl"
    history = b'{"usd":0.25,"job":"earlier-a"}\n{"usd":0.5,"job":"earlier-b"}\n'
    path.write_bytes(history)
    ledger = Ledger(path, 0.75, must_exist=True)
    sent = []
    model = Model("gpt-6-luna", "none", ledger, instructions="Return an object.",
                  max_output_tokens=200, send=lambda body: sent.append(body) or {
                      "status": "completed", "usage": {"input_tokens": 0, "output_tokens": 0},
                      "output": []})

    with pytest.raises(BudgetExhausted, match="Spent"):
        model.call("test", {"type": "object", "properties": {}})

    assert sent == []
    assert ledger.spent == 0.75 and ledger.held == 0
    assert path.read_bytes() == history


@pytest.mark.parametrize("usd", [-0.25, float("nan"), float("inf"), -float("inf"),
                                 True, "0.25"])
def test_invalid_charge_preserves_spend_holds_and_history(tmp_path, usd):
    path = tmp_path / "spend.jsonl"
    history = b'{"usd":0.25,"job":"earlier"}\n'
    path.write_bytes(history)
    ledger = Ledger(path, 1.0, must_exist=True)
    ledger.reserve(0.125)

    with pytest.raises(ValueError, match="finite and nonnegative"):
        ledger.charge(usd, job="invalid")

    assert ledger.spent == 0.25 and ledger.held == 0.125
    assert path.read_bytes() == history
    with pytest.raises(BudgetExhausted):
        ledger.reserve(1.0)
    ledger.release(0.125)
    assert Ledger(path, 1.0, must_exist=True).spent == 0.25


@pytest.mark.parametrize("usd", [-0.25, float("nan"), float("inf"), -float("inf"),
                                 True, "0.25"])
def test_invalid_prior_charge_refuses_reopen_without_rewriting_evidence(tmp_path, usd):
    path = tmp_path / "spend.jsonl"
    history = b'{"usd":0.25,"job":"earlier"}\n' + (
        json.dumps({"usd": usd, "job": "malformed"}) + "\n").encode()
    path.write_bytes(history)

    with pytest.raises(ValueError, match="finite and nonnegative"):
        Ledger(path, 1.0, must_exist=True)

    assert path.read_bytes() == history


def test_zero_and_positive_charges_remain_usable_after_reopening(tmp_path):
    path = tmp_path / "spend.jsonl"
    ledger = Ledger(path, 1.0)
    ledger.charge(0, job="free")
    ledger.charge(0.25, job="paid")

    assert [json.loads(line)["usd"] for line in path.read_text().splitlines()] == [0, 0.25]
    reopened = Ledger(path, 1.0, must_exist=True)
    assert ledger.spent == reopened.spent == 0.25
    reopened.reserve(0.75)
    with pytest.raises(BudgetExhausted):
        reopened.reserve(0.125)
