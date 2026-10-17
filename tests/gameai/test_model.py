"""Pricing, key loading and transport retries for OpenAI calls; no network."""

import io
import json
import urllib.error

import pytest

from gameai import llm as api
from gameai.ledger import BudgetExhausted, Ledger

USAGE = {"input_tokens": 1000, "input_tokens_details": {"cached_tokens": 400},
         "output_tokens": 200, "output_tokens_details": {"reasoning_tokens": 150}}


def test_usage_cost_prices_uncached_cached_and_output_tokens():
    expected = (600 * 10 + 400 * 1 + 200 * 50) / 1e6
    assert api.usage_cost("gpt-6-astra", USAGE) == pytest.approx(expected)


def test_api_key_file_and_transient_retry_without_leaking_the_key(tmp_path, monkeypatch):
    key_file = tmp_path / "key"
    key_file.write_text("sk-test-secret\n")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("SPIRE_OPENAI_KEY_FILE", str(key_file))
    assert api.api_key() == "sk-test-secret"
    responses = [
        urllib.error.HTTPError("u", 503, "busy", {}, io.BytesIO(b"busy")),
        io.BytesIO(b'{"id": "ok"}'),
        urllib.error.HTTPError("u", 401, "no", {}, io.BytesIO(b"bad key sk-test-secret")),
    ]

    def urlopen(request, timeout):
        assert request.headers["Authorization"] == "Bearer sk-test-secret"
        value = responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(api.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(api.time, "sleep", lambda seconds: None)
    assert api.post(api.api_key(), {}) == {"id": "ok", "_uncertain_attempts": 1}
    with pytest.raises(api.APIError) as error:
        api.post(api.api_key(), {})
    assert "sk-test-secret" not in str(error.value) and "<key>" in str(error.value)


def test_ask_retries_rejected_replies_with_feedback_then_gives_up(tmp_path):
    texts, prompts = ["left", "jump", "up", "up"], []

    def send(body):
        prompts.append(body["input"][0]["content"])
        return {"id": "r", "usage": USAGE, "output": [{"type": "message", "content": [
            {"type": "output_text", "text": texts.pop(0)}]}]}

    def parse(text):
        if text not in ("up", "down"):
            raise ValueError(f"unknown key {text}")
        return text

    model = api.Model("gpt-6-luna", "none", Ledger(tmp_path / "spend.jsonl", 1.0), send=send,
                      instructions="Press a key.", max_output_tokens=200)
    value, attempts = model.ask("Wall ahead.", {}, parse, retries=2)
    assert value == "up" and [a.get("error") for a in attempts] == [
        "unknown key left", "unknown key jump", None]
    assert prompts[2].endswith("Your previous reply was invalid: unknown key jump. Reply again.")
    with pytest.raises(api.InvalidReply) as error:
        model.ask("Wall ahead.", {}, lambda text: parse("jump"), retries=0)
    assert len(error.value.attempts) == 1 and model.totals["calls"] == 4


def test_cut_off_reply_is_retried_with_a_neutral_notice(tmp_path):
    # A cut reply that still parses keeps the game's own rejection as feedback.
    replies, prompts = [("incomplete", '{"key": "u'), ("incomplete", '{"key": "jump"}'),
                        ("completed", '{"key": "up"}')], []

    def send(body):
        prompts.append(body["input"][0]["content"])
        status, text = replies.pop(0)
        return {"status": status, "usage": USAGE, "output": [{"type": "message", "content": [
            {"type": "output_text", "text": text}]}]}

    def parse(text):
        reply = json.loads(text)
        if reply["key"] not in ("up", "down"):
            raise ValueError(f"unknown key {reply['key']}")
        return reply

    model = api.Model("gpt-6-luna", "none", Ledger(tmp_path / "spend.jsonl", 1.0), send=send,
                      instructions="Press a key.", max_output_tokens=200)
    value, attempts = model.ask("Wall ahead.", {}, parse, retries=2)
    assert value == {"key": "up"} and attempts[0]["error"].startswith("Unterminated string")
    assert prompts[1] == ("Wall ahead.\n\nYour previous reply was cut off at the output limit"
                          " before the JSON ended. Reply again.")
    assert prompts[2] == ("Wall ahead.\n\nYour previous reply was invalid: unknown key jump."
                          " Reply again.")


@pytest.mark.parametrize("capture", [False, True])
def test_failed_response_is_resent_unchanged_and_kept_once(tmp_path, capture):
    # A Kimi decision ended on one upstream failure (bench-b23-s1-kimi-low-20261017 m28).
    bodies = []

    def send(body):
        bodies.append(body)
        failed = len(bodies) == 1
        return {"id": f"r{len(bodies)}", "status": "failed" if failed else "completed",
                "usage": USAGE, "output": [{"type": "message", "content": [
                    {"type": "output_text", "text": "down" if failed else "up"}]}],
                **({"error": {"code": "server_error"}} if failed else {})}

    model = api.Model("gpt-6-luna", "none", Ledger(tmp_path / "spend.jsonl", 1.0), send=send,
                      instructions="Press a key.", max_output_tokens=200,
                      record_exchanges=capture)
    value, attempts = model.ask("Wall ahead.", {}, lambda text: text, retries=1)
    assert value == "up" and bodies[1] == bodies[0]
    assert [a.get("error") for a in attempts] == ["openai returned a failed response r1", None]
    assert model.totals["calls"] == 2
    assert model.ledger.spent == pytest.approx(2 * attempts[1]["usd"])
    if capture:
        exchange, = model.drain_exchanges()
        assert exchange["attempts"] == attempts and "error" not in exchange


@pytest.mark.parametrize("retries", [1, 2])
def test_failed_response_after_a_rejected_reply_keeps_its_feedback(tmp_path, retries):
    # With retries left the failed request goes out again as it was; without, the APIError
    # carries every billed attempt even when exchanges are not captured.
    texts, bodies = ["left", "down", "up"], []

    def send(body):
        bodies.append(body)
        return {"id": f"r{len(bodies)}", "status": "failed" if len(bodies) == 2 else "completed",
                "usage": USAGE, "output": [{"type": "message", "content": [
                    {"type": "output_text", "text": texts.pop(0)}]}],
                **({"error": {"code": "server_error"}} if len(bodies) == 2 else {})}

    def parse(text):
        if text != "up":
            raise ValueError(f"unknown key {text}")
        return text

    model = api.Model("gpt-6-luna", "none", Ledger(tmp_path / "spend.jsonl", 1.0), send=send,
                      instructions="Press a key.", max_output_tokens=200)
    errors = ["unknown key left", "openai returned a failed response r2", None]
    if retries == 1:
        with pytest.raises(api.APIError) as failure:
            model.ask("Wall ahead.", {}, parse, retries)
        assert [a.get("error") for a in failure.value.attempts] == errors[:2]
        assert failure.value.attempt is failure.value.attempts[-1]
        return
    value, attempts = model.ask("Wall ahead.", {}, parse, retries)
    assert value == "up" and [a.get("error") for a in attempts] == errors
    assert bodies[2] == bodies[1] != bodies[0]
    assert bodies[1]["input"][0]["content"].endswith("invalid: unknown key left. Reply again.")


def test_ask_retries_a_reply_nested_too_deeply_to_parse(tmp_path):
    texts = ["[" * 100000, "[]"]

    def send(body):
        return {"id": "r", "usage": USAGE, "output": [{"type": "message", "content": [
            {"type": "output_text", "text": texts.pop(0)}]}]}

    model = api.Model("gpt-6-luna", "none", Ledger(tmp_path / "spend.jsonl", 1.0), send=send,
                      instructions="Reply.", max_output_tokens=200)
    value, attempts = model.ask("Go.", {}, json.loads, retries=1)
    assert value == [] and "recursion" in attempts[0]["error"]


FIELDS = {"properties": {"n": {"type": "integer"}, "x": {"type": "number"},
                         "s": {"type": ["string", "null"]},
                         "e": {"type": "string", "enum": ["up", "down"]}},
          "required": ["n", "x", "s"]}
GOOD = {"n": 1, "x": 1.5, "s": None, "extra": [1]}


def test_check_fields_passes_a_reply_with_the_fields_its_schema_allows():
    assert api.check_fields(GOOD, FIELDS) is GOOD  # extra fields pass; "e" is optional
    assert api.check_fields(dict(GOOD, x=2, s="a", e="up"), FIELDS)


@pytest.mark.parametrize(("value", "message"), [
    ([GOOD], "plan must be a JSON object"),
    ({"n": 1, "x": 1}, "plan has no 's' field"),
    (dict(GOOD, n=True), "plan field 'n' must be integer"),
    (dict(GOOD, n=1.0), "plan field 'n' must be integer"),
    (dict(GOOD, x=False), "plan field 'x' must be number"),
    (dict(GOOD, x=float("nan")), "plan field 'x' must be number"),
    (dict(GOOD, x=float("-inf")), "plan field 'x' must be number"),
    (dict(GOOD, x=10**400), "plan field 'x' must be number"),
    (dict(GOOD, s=0), "plan field 's' must be string or null"),
    (dict(GOOD, e="left"), "plan field 'e' must be one of up, down"),
    (dict(GOOD, e=None), "plan field 'e' must be string"),
])
def test_check_fields_rejects_what_its_schema_does_not_allow(value, message):
    with pytest.raises(ValueError) as error:
        api.check_fields(value, FIELDS, "plan")
    assert str(error.value) == message


def test_wh3_transport_opt_in_records_wall_time_header_and_actual_model(tmp_path, monkeypatch):
    class Response(io.BytesIO):
        headers = {"openai-processing-ms": "1234.5"}

    monkeypatch.setattr(api.urllib.request, "urlopen", lambda *a, **kw: Response(
        b'{"id":"r", "model":"actual-snapshot", "usage":{"input_tokens":1,"output_tokens":1}}'))
    ticks = iter([100., 102.])
    monkeypatch.setattr(api.time, "time", lambda: next(ticks))
    response = api.post("test-key", {}, record_transport=True)
    assert response["_transport"] == {
        "wall_seconds": 2., "provider_processing_ms": 1234.5,
        "actual_model": "actual-snapshot", "transport_attempts": 1,
    }
    model = api.Model("gpt-6-luna", "none", Ledger(tmp_path / "ledger", 1),
                      instructions="test", max_output_tokens=10, send=lambda body: response)
    attempt = model.call("test", {})
    assert attempt["seconds"] == 2 and attempt["actual_model"] == "actual-snapshot"
    assert attempt["provider_processing_ms"] == 1234.5


def test_exchange_capture_keeps_exact_retry_requests_and_returned_output(tmp_path):
    bodies = []
    output = [{"type": "reasoning", "summary": [{"type": "summary_text", "text": "summary"}],
               "content": [{"type": "reasoning_text", "text": "returned reasoning"}]}]

    def send(body):
        bodies.append(body)
        return {"usage": USAGE, "output": output + [{"type": "message", "content": [
            {"type": "output_text", "text": "bad" if len(bodies) == 1 else "good"}]}]}

    def parse(text):
        if text == "bad":
            raise ValueError("bad first reply")
        return text

    model = api.Model("gpt-6-luna", "low", Ledger(tmp_path / "ledger", 1), instructions="system\n",
                      max_output_tokens=200, send=send, record_exchanges=True)
    value, attempts = model.ask("exact user\n", {"type": "object"}, parse, 1)
    assert value == "good"
    assert attempts[0]["request"] == bodies[0] and attempts[1]["request"] == bodies[1]
    assert bodies[1]["input"][0]["content"] == (
        "exact user\n\n\nYour previous reply was invalid: bad first reply. Reply again.")
    assert bodies[0]["reasoning"] == {"effort": "low", "summary": "auto"}
    assert attempts[0]["output"][0] == output[0]
    assert attempts[1]["exchange_id"] == attempts[0]["exchange_id"] == "m1"
    exchange, = list(model.drain_exchanges())
    assert exchange == {"id": "m1", "prompt": "exact user\n", "attempts": attempts}
    assert list(model.drain_exchanges()) == []
    assert all("returned reasoning" not in str(body) for body in bodies)


@pytest.mark.parametrize("provider,model_name,effort", [
    ("openai", "gpt-6-luna", "none"), ("openrouter", "z-ai/glm-5.3", "low")])
def test_capture_does_not_add_summary_setting_to_no_reasoning_or_router_calls(
        tmp_path, provider, model_name, effort):
    bodies = []

    def send(body):
        bodies.append(body)
        return {"usage": dict(USAGE, cost=.0001), "output": []}

    model = api.Model(model_name, effort, Ledger(tmp_path / "ledger", 1), instructions="system",
                      max_output_tokens=200, send=send, provider=provider, record_exchanges=True)
    model.ask("user", {}, lambda text: text, 0)
    assert bodies[0]["reasoning"] == {"effort": effort}


def test_spire_default_does_not_capture_or_change_request_settings(tmp_path):
    bodies = []

    def send(body):
        bodies.append(body)
        return {"usage": USAGE, "output": []}

    model = api.Model("gpt-6-luna", "low", Ledger(tmp_path / "ledger", 1), instructions="system",
                      max_output_tokens=200, send=send)
    _, attempts = model.ask("user", {}, lambda text: text, 0)
    assert set(attempts[0]) == {"response_id", "status", "seconds", "usage", "usd", "text"}
    assert bodies[0]["reasoning"] == {"effort": "low"}
    assert list(model.drain_exchanges()) == []


@pytest.mark.parametrize("failure", ["transport", "response", "parse", "budget"])
def test_failed_exchanges_keep_all_available_attempts_and_errors(tmp_path, failure):
    def send(body):
        if failure == "transport":
            raise api.APIError("service failed", uncertain_attempts=1)
        return {"usage": USAGE, "output": [],
                **({"error": {"code": "failed"}} if failure == "response" else {})}

    def parse(text):
        raise ValueError("invalid")

    model = api.Model("gpt-6-luna", "low", Ledger(tmp_path / "ledger", 0 if failure == "budget"
                                                 else 1), instructions="system",
                      max_output_tokens=200, send=send, record_exchanges=True)
    with pytest.raises({"transport": api.APIError, "response": api.APIError,
                        "parse": api.InvalidReply, "budget": BudgetExhausted}[failure]) as error:
        model.ask("user", {}, parse, 1)
    exchange, = list(model.drain_exchanges())
    assert exchange["prompt"] == "user" and exchange["error"]["type"]
    assert len(exchange["attempts"]) == (0 if failure == "budget" else 1 if failure == "transport"
                                        else 2)
    if failure == "transport":
        attempt, = exchange["attempts"]
        assert attempt["transport_error"] == "service failed" and "text" not in attempt
        assert attempt["request"]["input"][0]["content"] == "user"
    if failure == "response":
        # Resent unchanged until retries ran out; the last failure stays infrastructure.
        assert exchange["error"]["type"] == "APIError" and error.value.retryable
        assert all(a["response_error"] == {"code": "failed"} and a["exchange_id"] == "m1"
                   and a["request"]["input"][0]["content"] == "user"
                   for a in exchange["attempts"])
        assert error.value.attempt is exchange["attempts"][-1]
