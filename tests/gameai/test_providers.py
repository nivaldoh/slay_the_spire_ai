"""Provider isolation, structured responses and budget failures without network access."""

import http.client
import io
import json
import urllib.error
from functools import partial

import pytest

from gameai import llm
from gameai.ledger import BudgetExhausted, Ledger
from gameai.providers import ANTHROPIC, ANTHROPIC_WORKSPACE_ENV, OPENROUTER, routing, validate

SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}},
          "required": ["ok"], "additionalProperties": False}


def reply(**fields):
    return {"id": "gen-test", "model": "z-ai/glm-5.3", "status": "completed",
            "usage": {"input_tokens": 100, "output_tokens": 20, "cost": .0002},
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": '{"ok":true}'}]}], **fields}


def model(tmp_path, send, budget=1, name="z-ai/glm-5.3"):
    effort = OPENROUTER.efforts[name][-1]
    return llm.Model(name, effort, Ledger(tmp_path / "ledger.jsonl", budget),
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


def test_a_key_with_paste_debris_or_anthropic_without_a_workspace_fails_before_any_call(
        tmp_path, monkeypatch):
    # 2026-10-31: pasting into `read -s` left escape codes before the Anthropic key, and the
    # server answered HTTP 400 with an empty body, which WH3 would score as the model failing.
    path = tmp_path / "secret"
    path.write_text("\x1b[2~\x1b[2~\x1b[sk-ant-test\n")
    monkeypatch.delenv(ANTHROPIC.key_env, raising=False)
    monkeypatch.setenv(ANTHROPIC.key_file_env, str(path))
    monkeypatch.setenv(ANTHROPIC_WORKSPACE_ENV, "wrkspc_test")
    with pytest.raises(llm.APIError, match="unprintable") as failure:
        llm.api_key("anthropic")
    assert "sk-ant" not in str(failure.value)
    path.write_text("sk-ant-test\n")
    assert llm.api_key("anthropic") == "sk-ant-test"
    monkeypatch.setenv("OPENROUTER_API_KEY", "\x1b[2~router-secret")
    with pytest.raises(llm.APIError, match="unprintable"):
        llm.api_key("openrouter")
    monkeypatch.delenv(ANTHROPIC_WORKSPACE_ENV)
    with pytest.raises(llm.APIError, match=ANTHROPIC_WORKSPACE_ENV):
        llm.api_key("anthropic")


def test_http_error_redacts_a_key_crossing_the_display_limit(monkeypatch):
    key = "secret-key-that-crosses-the-boundary"

    def urlopen(*args, **kwargs):
        raise urllib.error.HTTPError("url", 401, "unauthorized", {},
                                     io.BytesIO(("x" * 490 + key).encode()))

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    with pytest.raises(llm.APIError) as failure:
        llm.post(key, {}, provider="openrouter")
    assert "secret" not in str(failure.value) and "<key>" in str(failure.value)


def test_reasoning_efforts_are_declared_per_model():
    validate("openrouter", "moonshotai/kimi-k3", "none")
    validate("openrouter", "z-ai/glm-5.3", "max")
    validate("openrouter", "stepfun/step-5-preview", "medium")
    validate("openai", "gpt-6-luna", "none")
    validate("openai", "gpt-6.1-sol", "max")
    with pytest.raises(ValueError, match="gpt-6.1-sol: use an effort in low"):
        validate("openai", "gpt-6.1-sol", "none")
    validate("openrouter", "qwen/qwen3.6-35b-a3b", "none")
    validate("openrouter", "qwen/qwen3.6-35b-a3b", "medium")
    for model, effort in [("z-ai/glm-5.3", "none"), ("z-ai/glm-5.3", "medium"),
                          ("stepfun/step-5-preview", "max"), ("qwen/qwen3.6-35b-a3b", "low"),
                          ("qwen/qwen3.6-35b-a3b", "high")]:
        with pytest.raises(ValueError, match=f"{model}: use an effort in"):
            validate("openrouter", model, effort)
    validate("anthropic", "claude-opus-5-5", "max")
    with pytest.raises(ValueError, match="claude-haiku-5-5: use an effort in low"):
        validate("anthropic", "claude-haiku-5-5", "none")


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


def test_missing_cost_preserves_valid_reported_token_totals(tmp_path):
    agent = model(tmp_path, lambda body: reply(usage={
        "input_tokens": 100, "output_tokens": 20, "cost": None,
        "input_tokens_details": {"cached_tokens": 30},
        "output_tokens_details": {"reasoning_tokens": 10},
    }))
    with pytest.raises(llm.APIError, match="charged reservation and stopped"):
        agent.call("test", SCHEMA)

    assert agent.totals["calls"] == 1
    assert agent.totals["input_tokens"] == 100 and agent.totals["output_tokens"] == 20
    assert agent.totals["cached_tokens"] == 30 and agent.totals["reasoning_tokens"] == 10


@pytest.mark.parametrize("cost", [None, 1.0])
def test_cost_failures_stop_without_retry_and_keep_the_billed_attempt(tmp_path, cost):
    # Even on a failed response, a missing or over-reservation cost is never resent.
    sent = []
    agent = model(tmp_path, lambda body: sent.append(body) or reply(
        status="failed", error={"code": "server_error"},
        usage={"input_tokens": 100, "output_tokens": 20, "cost": cost}))
    with pytest.raises(llm.APIError, match="and stopped") as failure:
        agent.ask("test", SCHEMA, json.loads, retries=2)
    assert len(sent) == 1 and not failure.value.retryable
    assert failure.value.attempt["usd"] == pytest.approx(agent.ledger.spent)


def test_failed_openrouter_response_at_zero_cost_is_resent(tmp_path):
    # The shape of bench-b23-s1-kimi-low-20261017 m28: a truncation reported as failed, unbilled.
    failed = reply(status="failed", error={
        "code": "server_error", "message": "Upstream error from Morph: Invalid structured"
        " output: output_truncated (schema #)."}, usage={
        "input_tokens": 2861, "output_tokens": 3664, "cost": 0,
        "output_tokens_details": {"reasoning_tokens": 3472}}, output=[
        {"type": "message", "content": [{"type": "output_text", "text": '{"ok":tr'}]}])
    replies, sent = [failed, reply()], []
    agent = model(tmp_path, lambda body: sent.append(body) or replies.pop(0))
    value, attempts = agent.ask("test", SCHEMA, json.loads, retries=1)
    assert value == {"ok": True} and sent[1] == sent[0]
    assert attempts[0]["error"] == "openrouter returned a failed response gen-test"
    assert agent.ledger.spent == pytest.approx(.0002)


def test_uncertain_transport_attempts_are_charged_on_success_and_failure(tmp_path, monkeypatch):
    class Response(io.BytesIO):
        headers = {}

    class Truncated(Response):
        def read(self, *args):
            raise http.client.IncompleteRead(b'{"id"', 100)

    # Undecodable and truncated bodies are uncertain transport too, never a raw traceback.
    outcomes = [TimeoutError("secret-key"), Response(json.dumps(reply()).encode()),
                Response(b"\xff"), TimeoutError("secret-key"), Truncated()]

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
    assert str(error.value).startswith("IncompleteRead") and not outcomes
    records = [json.loads(line) for line in agent.ledger.path.read_text().splitlines()]
    assert [r.get("attempts") for r in records] == [1, None, 3]
    assert records[2]["usd"] == pytest.approx(3 * records[0]["usd"])
    assert agent.ledger.spent == pytest.approx(agent.totals["usd"])


def test_router_metadata_records_the_selected_backend(tmp_path, monkeypatch):
    class Response(io.BytesIO):
        headers = {}

    payload = reply(openrouter_metadata={"attempt": 2, "endpoints": {"available": [
        {"provider": "unused", "selected": False},
        {"provider": "Z.AI", "model": "z-ai/glm-5.3-snapshot", "selected": True}]}})
    monkeypatch.setattr(llm.urllib.request, "urlopen",
                        lambda *a, **kw: Response(json.dumps(payload).encode()))
    agent = model(tmp_path, partial(llm.post, "key", provider="openrouter", record_transport=True))
    attempt = agent.call("test", SCHEMA)
    assert attempt["backend"] == "Z.AI" and attempt["router_attempts"] == 2
    assert attempt["provider"] == "openrouter" and attempt["actual_model"] == "z-ai/glm-5.3"
    assert attempt["backend_model"] == "z-ai/glm-5.3-snapshot"


def test_incomplete_empty_response_keeps_its_charge_and_failure_evidence(tmp_path):
    # Step's first live schema check spent its token allowance and returned no output.
    agent = model(tmp_path, lambda body: reply(status="incomplete", output=[],
        incomplete_details={"reason": "max_output_tokens"}))
    with pytest.raises(llm.InvalidReply) as failure:
        agent.ask("test", SCHEMA, json.loads, retries=0)
    attempt = failure.value.attempts[0]
    assert attempt["status"] == "incomplete" and attempt["text"] == ""
    assert attempt["usd"] == agent.ledger.spent == .0002


@pytest.mark.parametrize("budget", [float("nan"), float("inf"), -1])
def test_nonfinite_or_negative_budgets_cannot_disable_the_cap(tmp_path, budget):
    with pytest.raises(ValueError, match="finite and nonnegative"):
        Ledger(tmp_path / "ledger", budget)


def test_the_model_to_fine_tune_routes_at_fp8_or_better_with_explicit_sampling():
    route = routing("openrouter", "qwen/qwen3.6-35b-a3b")
    assert route["provider"]["quantizations"] == ["fp8", "bf16"]
    assert route["provider"]["only"] == ["parasail"] and not route["provider"]["allow_fallbacks"]
    assert route["provider"]["require_parameters"] is True
    assert (route["temperature"], route["top_p"]) == (1.0, 0.95)
    assert "quantizations" not in routing("openrouter", "z-ai/glm-5.3")["provider"]
    assert "temperature" not in routing("openrouter", "z-ai/glm-5.3")
    # OpenRouter's fields would otherwise reach Anthropic and every card's routing record.
    assert routing("anthropic", "claude-haiku-5-5") == {}


def test_an_unknown_provider_is_refused_with_the_known_names():
    # Removing this refusal passed every test (runs/refusal-sweep-20261029/gameai-providers.txt).
    with pytest.raises(ValueError, match="provider 'bogus'; use openai, openrouter"):
        llm.get_provider("bogus")


# Messages API replies shaped as its reference documents them (2026-10-31); values made up.
def message(text, stop="end_turn", thinking="", **usage):
    content = [{"type": "thinking", "thinking": thinking, "signature": "sig"}]
    content += [{"type": "text", "text": text}] if text is not None else []
    return {"id": "msg_test", "type": "message", "role": "assistant",
            "model": "claude-haiku-5-5", "content": content, "stop_reason": stop,
            "stop_sequence": None, "stop_details": None,
            "usage": {"input_tokens": 1000, "cache_creation_input_tokens": 0,
                      "cache_read_input_tokens": 0, "output_tokens": 40,
                      "output_tokens_details": {"thinking_tokens": 30},
                      "service_tier": "standard", **usage}}


def anthropic_model(tmp_path, monkeypatch, replies, **kwargs):
    """A Haiku model whose calls go through post() to a fake Messages endpoint."""
    sent = []

    class Response(io.BytesIO):
        headers = {}

    def urlopen(request, timeout):
        sent.append((request.full_url, {key.lower(): value for key, value in
                                        request.header_items()}, json.loads(request.data)))
        return Response(json.dumps(replies.pop(0)).encode())

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    monkeypatch.setenv(ANTHROPIC_WORKSPACE_ENV, "wrkspc_test")
    agent = llm.Model("claude-haiku-5-5", "high", Ledger(tmp_path / "ledger.jsonl", 1),
                      instructions="Reply with JSON.", max_output_tokens=256,
                      send=partial(llm.post, "test-key", provider="anthropic",
                                   record_transport=True), provider="anthropic", **kwargs)
    return agent, sent


def test_anthropic_calls_are_translated_both_ways_and_charged_from_usage(tmp_path, monkeypatch):
    # A reply cut at max_tokens gets the cut-off notice; the second completes.
    cut = message('{"ok":', stop="max_tokens", thinking="Check the field.", output_tokens=256,
                  input_tokens=1000, cache_read_input_tokens=200, cache_creation_input_tokens=50)
    agent, sent = anthropic_model(tmp_path, monkeypatch, [cut, message('{"ok":true}')],
                                  record_exchanges=True)
    value, attempts = agent.ask("Return ok=true.", SCHEMA, json.loads, retries=1)
    assert value == {"ok": True}
    url, headers, body = sent[0]
    assert url == ANTHROPIC.url and headers["authorization"] == "Bearer test-key"
    assert headers["anthropic-version"] == "2026-10-21"
    assert headers["anthropic-workspace-id"] == "wrkspc_test"
    assert body == {"model": "claude-haiku-5-5", "max_tokens": 256,
                    "system": "Reply with JSON.",
                    "messages": [{"role": "user", "content": "Return ok=true."}],
                    "output_config": {"effort": "high",
                                      "format": {"type": "json_schema", "schema": SCHEMA}},
                    "thinking": {"type": "adaptive", "display": "summarized"}}
    assert sent[1][2]["messages"][0]["content"] == "Return ok=true." + llm.CUT_OFF
    first = attempts[0]
    assert first["status"] == "incomplete" and first["text"] == '{"ok":'
    assert first["incomplete_details"] == {"reason": "max_output_tokens"}
    # Evidence keeps the Responses shape the exporters read.
    assert first["request"]["instructions"] == "Reply with JSON."
    assert [part["text"] for part in llm.reasoning_parts(first["output"])] == [
        "Check the field."]
    assert llm.reasoning_parts(attempts[1]["output"]) == []  # its thinking text was empty
    assert first["actual_model"] == "claude-haiku-5-5" and first["provider"] == "anthropic"
    assert "backend" not in first
    # Cache reads and writes are input too: 1,250 tokens, 200 of them at the cached price.
    assert first["usage"]["input_tokens"] == 1250
    assert first["usd"] == pytest.approx((1050 * .10 + 200 * .01 + 256 * .50) / 1e6)
    assert attempts[1]["usd"] == pytest.approx((1000 * .10 + 40 * .50) / 1e6)
    assert agent.ledger.spent == pytest.approx(first["usd"] + attempts[1]["usd"])
    assert agent.totals["reasoning_tokens"] == 60


def test_an_anthropic_refusal_is_charged_and_re_asked_as_an_invalid_reply(tmp_path, monkeypatch):
    refusal = message("I can't help with that.", stop="refusal")
    refusal["stop_details"] = {"type": "refusal", "category": None, "explanation": "declined"}
    agent, sent = anthropic_model(tmp_path, monkeypatch, [refusal, dict(refusal)],
                                  record_exchanges=True)
    with pytest.raises(llm.InvalidReply) as failure:
        agent.ask("test", SCHEMA, json.loads, retries=1)
    attempts = failure.value.attempts
    assert len(sent) == 2 and "fallbacks" not in sent[0][2]
    assert attempts[0]["status"] == "completed" and attempts[0]["text"] == ""
    assert attempts[0]["output"][-1]["content"] == [{
        "type": "refusal", "refusal": "I can't help with that.",
        "stop_details": refusal["stop_details"]}]
    assert agent.ledger.spent == pytest.approx(2 * (1000 * .10 + 40 * .50) / 1e6)


def test_an_anthropic_reply_without_usage_is_charged_the_reserved_worst_case(
        tmp_path, monkeypatch):
    bare = {"id": "msg_test", "model": "claude-haiku-5-5", "stop_reason": "pause_turn",
            "content": [{"type": "redacted_thinking", "data": "x"}, {"type": "unknown"}]}
    agent, sent = anthropic_model(tmp_path, monkeypatch, [bare])
    attempt = agent.call("test", SCHEMA)
    assert "thinking" not in sent[0][2]  # summaries only for recorded exchanges
    assert attempt["status"] == "incomplete" and attempt["text"] == ""
    assert attempt["incomplete_details"] == {"reason": "pause_turn"}
    assert attempt["usage"]["output_tokens"] == 256 and attempt["usd"] > 256 * .50 / 1e6


def test_untranslatable_anthropic_requests_are_refused_before_sending(monkeypatch):
    sent = []
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda request, timeout: sent.append(
        request) or io.BytesIO(json.dumps(message("{}")).encode()))
    request = {"model": "claude-haiku-5-5", "instructions": "x", "max_output_tokens": 10,
               "input": [{"role": "user", "content": "y"}]}
    with pytest.raises(ValueError, match="temperature"):
        llm.post("test-key", dict(request, temperature=1.0), provider="anthropic")
    long = dict(request, instructions="x" * 100_000)  # past Haiku's 100k-token price step
    with pytest.raises(ValueError, match="over 100000 bytes"):
        llm.post("test-key", long, provider="anthropic")
    assert not sent
    sonnet = llm.post("test-key", dict(long, model="claude-sonnet-5-5"), provider="anthropic")
    assert sonnet["status"] == "completed" and len(sent) == 1  # Sonnet's prices have no step


@pytest.mark.parametrize("provider,sends", [("anthropic", 2), ("openai", 1), ("openrouter", 1)])
def test_only_anthropic_resends_an_overloaded_529(provider, sends, monkeypatch):
    replies = [urllib.error.HTTPError("url", 529, "overloaded", {}, io.BytesIO(b"{}")),
               io.BytesIO(json.dumps(message("{}") if provider == "anthropic" else reply())
                          .encode())]
    sent = []

    def urlopen(request, timeout):
        sent.append(request)
        outcome = replies.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)
    body = {"model": "claude-haiku-5-5", "instructions": "x", "max_output_tokens": 10,
            "input": [{"role": "user", "content": "y"}]}
    if sends == 1:
        with pytest.raises(llm.APIError, match="HTTP 529") as failure:
            llm.post("test-key", body, provider=provider)
        assert failure.value.uncertain_attempts == 1
    else:
        assert llm.post("test-key", body, provider=provider)["_uncertain_attempts"] == 1
    assert len(sent) == sends
