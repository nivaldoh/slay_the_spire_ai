"""Responses API calls for any game: transport, spend and the reply-retry loop.

Standard library only. Provider settings name the credential environment variables;
keys are never logged or written to evidence. A ``Model`` reserves a conservative cost
including retries before sending, then charges reported usage. Attempts with uncertain
billing are charged at the reserved rate. The game supplies instructions, prompt, reply
schema and parser.
"""

from __future__ import annotations

import json
import math
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from functools import partial
from pathlib import Path

from gameai.ledger import Ledger
from gameai.providers import OPENAI, get_provider, routing, validate

API_URL = OPENAI.url
PRICES = OPENAI.prices  # existing Spire imports keep their OpenAI defaults
EFFORTS = OPENAI.efforts
TRANSPORT_ATTEMPTS = 3
TRANSIENT_HTTP = {408, 409, 429, 500, 502, 503, 504}


class APIError(RuntimeError):
    """Transport or service failure: infrastructure, never a gameplay outcome."""

    def __init__(self, message: str, uncertain_attempts: int = 0):
        super().__init__(message)
        self.uncertain_attempts = uncertain_attempts


class InvalidReply(RuntimeError):
    """Every attempt's reply failed the game's parser."""

    def __init__(self, attempts: list[dict]):
        super().__init__("No valid reply after declared retries")
        self.attempts = attempts


def api_key(provider: str = "openai") -> str:
    spec = get_provider(provider)
    key = os.environ.get(spec.key_env, "").strip()
    if key:
        return key
    path = os.environ.get(spec.key_file_env)
    if not path:
        raise APIError(f"Set {spec.key_env} or {spec.key_file_env}")
    key = Path(path).expanduser().read_text().strip()
    if not key:
        raise APIError(f"Empty credential file named by {spec.key_file_env}")
    return key


def usage_cost(model: str, usage: dict, provider: str = "openai") -> float:
    if provider == "openrouter":
        cost = usage.get("cost")
        if (isinstance(cost, bool) or not isinstance(cost, (int, float))
                or not math.isfinite(cost) or cost < 0):
            raise ValueError("OpenRouter did not report a finite nonnegative usage.cost")
        return cost
    price_in, price_cached, price_out = get_provider(provider).prices[model]
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    return (
        (usage["input_tokens"] - cached) * price_in
        + cached * price_cached
        + usage["output_tokens"] * price_out
    ) / 1e6


def post(key: str, body: dict, attempts: int = TRANSPORT_ATTEMPTS, *,
         record_transport: bool = False, provider: str = "openai") -> dict:
    """One Responses API call; retries only transient transport and service errors."""
    data = json.dumps(body).encode()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if provider == "openrouter":
        headers["X-OpenRouter-Metadata"] = "enabled"
    started = time.time()
    uncertain = 0
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(get_provider(provider).url, data=data, headers=headers)
            with urllib.request.urlopen(request, timeout=60) as response:
                value = json.load(response)
                if uncertain:
                    value["_uncertain_attempts"] = uncertain
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
                    if provider == "openrouter":
                        metadata = value.get("openrouter_metadata") or {}
                        selected = next((item for item in (metadata.get("endpoints") or {}).get(
                            "available", []) if item.get("selected")), {})
                        value["_transport"].update(
                            provider=provider, backend=value.get("provider") or
                            selected.get("provider"), router_attempts=metadata.get("attempt"))
                return value
        except urllib.error.HTTPError as error:
            detail = error.read(500).decode(errors="replace").replace(key, "<key>")
            uncertain += error.code >= 500 or error.code == 408
            if error.code not in TRANSIENT_HTTP or attempt == attempts:
                raise APIError(f"HTTP {error.code}: {detail}", uncertain) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError,
                json.JSONDecodeError) as error:
            uncertain += 1
            if attempt == attempts:
                detail = str(error).replace(key, "<key>")
                raise APIError(f"{type(error).__name__}: {detail}", uncertain) from None
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
                 max_output_tokens: int, send=None, provider: str = "openai"):
        validate(provider, name, effort)
        if max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
        self.name, self.effort, self.ledger = name, effort, ledger
        self.provider = provider
        self.instructions, self.max_output_tokens = instructions, max_output_tokens
        self.send = send or partial(post, api_key(provider), provider=provider,
                                   record_transport=provider == "openrouter")
        self.totals = Counter()

    def call(self, prompt: str, schema: dict) -> dict:
        """Send one prompt and return the attempt record: id, status, usage, cost, text."""
        body = {
            "model": self.name,
            "instructions": self.instructions,
            "input": [{"role": "user", "content": prompt}],
            "reasoning": {"effort": self.effort},
            "max_output_tokens": self.max_output_tokens,
            "text": {"format": {"type": "json_schema", "name": "decision",
                                "schema": schema, "strict": True}},
            "store": False,
            **routing(self.provider, self.name),
        }
        # Include the schema and an allowance for provider framing at one token/byte.
        tokens = len(json.dumps(body).encode()) + 1024
        price_in, _, price_out = get_provider(self.provider).prices[self.name]
        reservation = (tokens * price_in + self.max_output_tokens * price_out) / 1e6
        self.ledger.reserve(reservation * TRANSPORT_ATTEMPTS)
        started = time.monotonic()
        try:
            response = self.send(body)
        except APIError as error:
            self._charge_uncertain(reservation, error.uncertain_attempts)
            raise
        self._charge_uncertain(reservation, response.get("_uncertain_attempts", 0))
        # Without reported usage, charge the reserved worst case.
        usage = response.get("usage") or {
            "input_tokens": tokens, "output_tokens": self.max_output_tokens,
        }
        cost_error = None
        try:
            usd = usage_cost(self.name, usage, self.provider)
        except ValueError as error:
            usd, cost_error = reservation, str(error)
        fields = {"provider": self.provider} if self.provider != "openai" else {}
        if cost_error:
            fields["estimated"] = True
        self.ledger.charge(usd, model=self.name, response_id=response.get("id"), **fields)
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
            if self.provider != "openai":
                attempt.update(provider=self.provider, backend=transport.get("backend"),
                               router_attempts=transport.get("router_attempts"))
        self.totals.update(
            calls=1, usd=usd, seconds=attempt["seconds"], input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            reasoning_tokens=(usage.get("output_tokens_details") or {}).get(
                "reasoning_tokens", 0),
            cached_tokens=(usage.get("input_tokens_details") or {}).get("cached_tokens", 0),
        )
        if cost_error:
            raise APIError(f"{cost_error}; charged reservation and stopped")
        if usd > reservation:
            raise APIError("Reported cost exceeded reservation; charged actual cost and stopped")
        if response.get("error"):
            raise APIError(f"{self.provider} returned a failed response {response.get('id')}")
        return attempt

    def _charge_uncertain(self, reservation: float, attempts: int) -> None:
        if attempts:
            usd = reservation * attempts
            self.ledger.charge(usd, model=self.name, provider=self.provider, estimated=True,
                               reason="uncertain_transport", attempts=attempts)
            self.totals.update(usd=usd, uncertain_transport_attempts=attempts)

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
