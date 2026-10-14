"""OpenAI model calls for any game: transport, prices, spend and the reply-retry loop.

Standard library only. The key comes from ``OPENAI_API_KEY`` or the file named by
``SPIRE_OPENAI_KEY_FILE`` (named after the first game, shared by every game) and is never
logged or written to evidence. A ``Model`` reserves each call's worst-case cost on its
ledger before sending, so a call that could exceed the budget is never sent, and charges
the reported cost after. The game supplies the instructions, the prompt, the reply
schema and a parser.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from functools import partial
from pathlib import Path

from gameai.ledger import Ledger

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
TRANSIENT_HTTP = {408, 409, 429, 500, 502, 503, 504}


class APIError(RuntimeError):
    """Transport or service failure: infrastructure, never a gameplay outcome."""


class InvalidReply(RuntimeError):
    """Every attempt's reply failed the game's parser."""

    def __init__(self, attempts: list[dict]):
        super().__init__("No valid reply after declared retries")
        self.attempts = attempts


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


def post(key: str, body: dict, attempts: int = 3, *, record_transport: bool = False) -> dict:
    """One Responses API call; retries only transient transport and service errors."""
    data = json.dumps(body).encode()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    started = time.time()
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(API_URL, data=data, headers=headers)
            with urllib.request.urlopen(request, timeout=60) as response:
                value = json.load(response)
                if record_transport:
                    processing = response.headers.get("openai-processing-ms")
                    try:
                        processing = float(processing) if processing else None
                    except ValueError:
                        processing = None
                    value["_transport"] = {
                        "wall_seconds": time.time() - started,
                        "provider_processing_ms": processing,
                        "actual_model": value.get("model"), "transport_attempts": attempt,
                    }
                return value
        except urllib.error.HTTPError as error:
            detail = error.read(500).decode(errors="replace").replace(key, "<key>")
            if error.code not in TRANSIENT_HTTP or attempt == attempts:
                raise APIError(f"HTTP {error.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if attempt == attempts:
                raise APIError(f"{type(error).__name__}: {error}") from None
        time.sleep(2**attempt)


def _output_text(response: dict) -> str:
    return "".join(
        part.get("text", "")
        for item in response.get("output", []) if item.get("type") == "message"
        for part in item.get("content", []) if part.get("type") == "output_text"
    )


class Model:
    """One model at one reasoning effort with fixed instructions; ``totals`` sums its calls."""

    def __init__(self, name: str, effort: str, ledger: Ledger, *, instructions: str,
                 max_output_tokens: int, send=None):
        if name not in PRICES:
            raise ValueError(f"No declared price for model {name}")
        if effort not in EFFORTS:
            raise ValueError(f"Unsupported reasoning effort {effort}")
        self.name, self.effort, self.ledger = name, effort, ledger
        self.instructions, self.max_output_tokens = instructions, max_output_tokens
        self.send = send or partial(post, api_key())
        self.totals = Counter()

    def call(self, prompt: str, schema: dict) -> dict:
        """Send one prompt and return the attempt record: id, status, usage, cost, text."""
        # Bytes bound tokens from above, so this reservation is a true worst case.
        tokens = len((self.instructions + prompt).encode())
        price_in, _, price_out = PRICES[self.name]
        self.ledger.reserve((tokens * price_in + self.max_output_tokens * price_out) / 1e6)
        started = time.monotonic()
        response = self.send({
            "model": self.name,
            "instructions": self.instructions,
            "input": [{"role": "user", "content": prompt}],
            "reasoning": {"effort": self.effort},
            "max_output_tokens": self.max_output_tokens,
            "text": {"format": {"type": "json_schema", "name": "decision",
                                "schema": schema, "strict": True}},
            "store": False,
        })
        # Without reported usage, charge the reserved worst case.
        usage = response.get("usage") or {
            "input_tokens": tokens, "output_tokens": self.max_output_tokens,
        }
        usd = usage_cost(self.name, usage)
        self.ledger.charge(usd, model=self.name, response_id=response.get("id"))
        attempt = {
            "response_id": response.get("id"),
            "status": response.get("status"),
            "seconds": time.monotonic() - started,
            "usage": usage,
            "usd": usd,
            "text": _output_text(response),
        }
        # Opt-in for WH3; the existing Spire trace schema and timing stay unchanged.
        if "_transport" in response:
            transport = response["_transport"]
            attempt.update({key: transport[key] for key in
                            ("provider_processing_ms", "actual_model", "transport_attempts")})
            attempt["seconds"] = transport["wall_seconds"]
        self.totals.update(
            calls=1, usd=usd, seconds=attempt["seconds"], input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            reasoning_tokens=(usage.get("output_tokens_details") or {}).get(
                "reasoning_tokens", 0),
            cached_tokens=(usage.get("input_tokens_details") or {}).get("cached_tokens", 0),
        )
        return attempt

    def ask(self, prompt: str, schema: dict, parse, retries: int) -> tuple[object, list[dict]]:
        """The parsed reply and every attempt. A reply that ``parse`` rejects with
        ValueError is retried with the error appended to the prompt."""
        attempts, feedback = [], ""
        for _ in range(1 + retries):
            attempt = self.call(prompt + feedback, schema)
            attempts.append(attempt)
            try:
                return parse(attempt["text"]), attempts
            except ValueError as error:
                attempt["error"] = str(error)
                feedback = f"\n\nYour previous reply was invalid: {error}. Reply again."
        raise InvalidReply(attempts)
