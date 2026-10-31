"""Earlier jobs retain their share of the hard cap (AGENTS.md, Evidence)."""

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
