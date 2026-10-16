"""Pricing, key loading and transport retries for OpenAI calls; no network."""

import io
import urllib.error

import pytest

from gameai import llm as api
from gameai.ledger import Ledger

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
