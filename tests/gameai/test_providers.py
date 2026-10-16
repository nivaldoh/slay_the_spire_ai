"""Provider isolation, structured responses and budget failures without network access."""

import io
import json
from functools import partial

import pytest

from gameai import llm
from gameai.ledger import BudgetExhausted, Ledger
from gameai.providers import OPENROUTER

SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}},
          "required": ["ok"], "additionalProperties": False}


def reply(**fields):
    return {"id": "gen-test", "model": "z-ai/glm-5.3", "status": "completed",
            "usage": {"input_tokens": 100, "output_tokens": 20, "cost": .0002},
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": '{"ok":true}'}]}], **fields}


def model(tmp_path, send, budget=1, name="z-ai/glm-5.3"):
    return llm.Model(name, "low", Ledger(tmp_path / "ledger.jsonl", budget),
                     instructions="Reply with JSON.", max_output_tokens=256,
                     send=send, provider="openrouter")


def test_credentials_are_selected_per_gateway_and_empty_files_are_rejected(tmp_path, monkeypatch):
    path = tmp_path / "secret"
    path.write_text("router-secret\n")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY_FILE", str(path))
    assert llm.api_key() == "openai-secret"
    assert llm.api_key("openrouter") == "router-secret"
    monkeypatch.setenv("OPENROUTER_API_KEY", "env-secret")
    assert llm.api_key("openrouter") == "env-secret"
    monkeypatch.delenv("OPENROUTER_API_KEY")
    path.write_text("\n")
    with pytest.raises(llm.APIError, match="Empty credential file"):
        llm.api_key("openrouter")


@pytest.mark.parametrize("name", OPENROUTER.prices)
def test_structured_calls_route_with_price_caps_and_charge_reported_cost(tmp_path, name):
    sent = []

    def send(body):
        sent.append(body)
        return reply(model=name)

    agent = model(tmp_path, send, name=name)
    parsed, attempts = agent.ask("Return ok=true.", SCHEMA, json.loads, retries=0)
    assert parsed == {"ok": True} and attempts[0]["usd"] == .0002
    assert sent[0]["model"] == name and sent[0]["store"] is False
    assert sent[0]["text"]["format"]["schema"] == SCHEMA
    route = sent[0]["provider"]
    assert route["require_parameters"] is True and route["max_price"]["request"] == 0
    assert agent.ledger.spent == .0002  # actual billed cost, not the conservative ceiling
    assert json.loads(agent.ledger.path.read_text())["provider"] == "openrouter"


def test_schema_overhead_and_all_transport_attempts_must_fit_before_sending(tmp_path):
    sent = []
    agent = model(tmp_path, lambda body: sent.append(body), budget=.01)
    with pytest.raises(BudgetExhausted):
        agent.call("tiny prompt", {"description": "x" * 10000})
    assert not sent and not agent.ledger.path.exists()


@pytest.mark.parametrize("cost", [None, -1, float("nan"), float("inf"), True, "0.001"])
def test_invalid_cost_is_charged_conservatively_and_stops(tmp_path, cost):
    agent = model(tmp_path, lambda body: reply(
        usage={"input_tokens": 100, "output_tokens": 20, "cost": cost}))
    with pytest.raises(llm.APIError, match="charged reservation and stopped"):
        agent.call("test", SCHEMA)
    record = json.loads(agent.ledger.path.read_text())
    assert record["estimated"] is True and record["usd"] > 0
    assert agent.totals["usd"] == record["usd"]


def test_uncertain_transport_attempts_are_charged_on_success_and_failure(tmp_path, monkeypatch):
    class Response(io.BytesIO):
        headers = {}

    outcomes = [TimeoutError("secret-key"), Response(json.dumps(reply()).encode()),
                TimeoutError("secret-key"), TimeoutError("secret-key"), TimeoutError("secret-key")]

    def urlopen(request, timeout):
        assert request.full_url == OPENROUTER.url
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)
    agent = model(tmp_path, partial(llm.post, "secret-key", provider="openrouter"))
    agent.call("test", SCHEMA)
    with pytest.raises(llm.APIError) as error:
        agent.call("test", SCHEMA)
    assert "secret-key" not in str(error.value)
    records = [json.loads(line) for line in agent.ledger.path.read_text().splitlines()]
    assert [r.get("attempts") for r in records] == [1, None, 3]
    assert records[2]["usd"] == pytest.approx(3 * records[0]["usd"])
    assert agent.ledger.spent == pytest.approx(agent.totals["usd"])


def test_router_metadata_records_the_selected_backend(tmp_path, monkeypatch):
    class Response(io.BytesIO):
        headers = {}

    payload = reply(openrouter_metadata={"attempt": 2, "endpoints": {"available": [
        {"provider": "unused", "selected": False}, {"provider": "Z.AI", "selected": True}]}})
    monkeypatch.setattr(llm.urllib.request, "urlopen",
                        lambda *a, **kw: Response(json.dumps(payload).encode()))
    agent = model(tmp_path, partial(llm.post, "key", provider="openrouter", record_transport=True))
    attempt = agent.call("test", SCHEMA)
    assert attempt["backend"] == "Z.AI" and attempt["router_attempts"] == 2
    assert attempt["provider"] == "openrouter" and attempt["actual_model"] == "z-ai/glm-5.3"


@pytest.mark.parametrize("budget", [float("nan"), float("inf"), -1])
def test_nonfinite_or_negative_budgets_cannot_disable_the_cap(tmp_path, budget):
    with pytest.raises(ValueError, match="finite and nonnegative"):
        Ledger(tmp_path / "ledger", budget)
