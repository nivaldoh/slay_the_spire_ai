"""Caller-selected read limits, leaving the existing shared transport default intact."""

import io

import pytest

from gameai import llm


@pytest.mark.parametrize("chosen", [None, 7.5])
def test_per_call_timeout_preserves_the_shared_default(monkeypatch, chosen):
    seen = []

    def urlopen(request, timeout):
        seen.append(timeout)
        return io.BytesIO(b'{"id":"offline-reply"}')

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    original = llm.READ_TIMEOUT_S
    assert llm.post("test-key", {}, timeout_s=chosen) == {"id": "offline-reply"}
    assert seen == [original if chosen is None else chosen]
    assert llm.READ_TIMEOUT_S == original


def test_existing_callers_keep_using_the_current_shared_limit(monkeypatch):
    seen = []
    monkeypatch.setattr(llm, "READ_TIMEOUT_S", 11)
    monkeypatch.setattr(llm.urllib.request, "urlopen", lambda request, timeout: (
        seen.append(timeout) or io.BytesIO(b'{}')))
    assert llm.post("test-key", {}) == {}
    assert seen == [11]
