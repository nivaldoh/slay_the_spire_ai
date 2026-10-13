"""OpenAI Responses transport, model prices and the default spend ledger's path.

Infrastructure, not scaffolding: the autoresearch loop does not tune this file. Standard
library only. The key comes from ``OPENAI_API_KEY`` or the file named by
``SPIRE_OPENAI_KEY_FILE`` and is never logged or written to evidence. Every call is priced
from its reported usage and charged to a ``gameai.ledger.Ledger``, which refuses a call
before sending when its total plus the call's worst-case cost would exceed the budget.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from gameai.provenance import REPO_ROOT

API_URL = "https://api.openai.com/v1/responses"
# USD per million tokens (input, cached input, output), standard tier, read 2026-10-12
# from https://developers.openai.com/api/docs/pricing. Prompts stay far below the
# 272K-token threshold where long-context rates apply.
PRICES = {
    "gpt-6-luna": (0.10, 0.01, 0.50),
    "gpt-6-sol": (2.00, 0.20, 10.00),
    "gpt-6.1-sol": (2.00, 0.10, 10.00),
    "gpt-6-astra": (10.00, 1.00, 50.00),
}
EFFORTS = ("none", "low", "medium", "high")
# Every job that names the same ledger shares one spend budget.
LEDGER_PATH = REPO_ROOT / "runs/llm-spend.jsonl"
TRANSIENT_HTTP = {408, 409, 429, 500, 502, 503, 504}


class APIError(RuntimeError):
    """Transport or service failure: infrastructure, never a gameplay outcome."""


def api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    path = os.environ.get("SPIRE_OPENAI_KEY_FILE")
    if not path:
        raise APIError("Set OPENAI_API_KEY or SPIRE_OPENAI_KEY_FILE")
    return Path(path).expanduser().read_text().strip()


def usage_cost(model: str, usage: dict) -> float:
    price_in, price_cached, price_out = PRICES[model]
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    return (
        (usage["input_tokens"] - cached) * price_in
        + cached * price_cached
        + usage["output_tokens"] * price_out
    ) / 1e6


class ResponsesClient:
    """Minimal POST client; retries only transient transport and service errors."""

    def __init__(self, key: str, *, timeout: float = 60, attempts: int = 3, url: str = API_URL):
        self._key, self.timeout, self.attempts, self.url = key, timeout, attempts, url

    def create(self, body: dict) -> dict:
        data = json.dumps(body).encode()
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        for attempt in range(1, self.attempts + 1):
            request = urllib.request.Request(self.url, data=data, headers=headers)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                detail = error.read(500).decode(errors="replace").replace(self._key, "<key>")
                if error.code not in TRANSIENT_HTTP or attempt == self.attempts:
                    raise APIError(f"HTTP {error.code}: {detail}") from None
            except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
                if attempt == self.attempts:
                    raise APIError(f"{type(error).__name__}: {error}") from None
            time.sleep(2**attempt)
        raise AssertionError("unreachable")
