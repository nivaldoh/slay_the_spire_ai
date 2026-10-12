"""Pricing, key loading and transport retries for the OpenAI client; no network."""

import io
import urllib.error

import pytest

from spire.fullrun import api

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
    client = api.ResponsesClient(api.api_key())
    assert client.create({}) == {"id": "ok"}
    with pytest.raises(api.APIError) as error:
        client.create({})
    assert "sk-test-secret" not in str(error.value) and "<key>" in str(error.value)
