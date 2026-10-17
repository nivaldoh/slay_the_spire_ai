"""Responses API calls for any game: transport, spend and the reply-retry loop.

Standard library only. Provider settings name the credential environment variables;
keys are never logged or written to evidence. A ``Model`` reserves a conservative cost
including retries before sending, then charges reported usage. Attempts with uncertain
billing are charged at the reserved rate. The game supplies instructions, prompt, reply
schema and parser.
"""

from __future__ import annotations

import http.client
import json
import math
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from functools import partial
from pathlib import Path
from queue import Empty, SimpleQueue

from gameai.ledger import Ledger
from gameai.providers import OPENAI, get_provider, routing, validate

API_URL = OPENAI.url
PRICES = OPENAI.prices
TRANSPORT_ATTEMPTS = 3
TRANSIENT_HTTP = {408, 409, 429, 500, 502, 503, 504}
CUT_OFF = ("\n\nYour previous reply was cut off at the output limit before the JSON ended."
           " Reply again.")


class APIError(RuntimeError):
    """Transport or service failure: infrastructure, never a gameplay outcome. ``retryable``
    names the failure kind, a failed response, which ``Model.ask`` resends unchanged while
    retries remain; it stays set on the one raised after they run out."""

    def __init__(self, message: str, uncertain_attempts: int = 0, retryable: bool = False):
        super().__init__(message)
        self.uncertain_attempts, self.retryable = uncertain_attempts, retryable


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
                            selected.get("provider"), backend_model=selected.get("model"),
                            router_attempts=metadata.get("attempt"))
                return value
        except urllib.error.HTTPError as error:
            # Read past the display boundary so truncation cannot leave a key prefix behind.
            detail = error.read(500 + len(key)).decode(errors="replace").replace(key, "<key>")[:500]
            uncertain += error.code >= 500 or error.code == 408
            if error.code not in TRANSIENT_HTTP or attempt == attempts:
                raise APIError(f"HTTP {error.code}: {detail}", uncertain) from None
        except (OSError, http.client.HTTPException, ValueError) as error:
            uncertain += 1
            if attempt == attempts:
                detail = str(error).replace(key, "<key>")
                raise APIError(f"{type(error).__name__}: {detail}", uncertain) from None
        time.sleep(2**attempt)


def reasoning_parts(output: list | None) -> list[dict]:
    """Text parts of returned reasoning items, with their provider type, field and item index.

    OpenAI returns summaries (``summary_text``); open-weight models through OpenRouter return
    the reasoning itself (``reasoning_text`` in ``content``).
    """
    return [dict(part, item_index=i, field=field)
            for i, item in enumerate(output or []) if item.get("type") == "reasoning"
            for field in ("summary", "content")
            for part in item.get(field) or [] if isinstance(part.get("text"), str)]


def _output_text(response: dict) -> str:
    return "".join(
        part.get("text", "")
        for item in response.get("output", []) if item.get("type") == "message"
        for part in item.get("content", []) if part.get("type") == "output_text"
    )


class Model:
    """One model at one reasoning effort with fixed instructions; ``totals`` sums its calls."""

    def __init__(self, name: str, effort: str, ledger: Ledger, *, instructions: str,
                 max_output_tokens: int, send=None, provider: str = "openai",
                 record_exchanges: bool = False):
        validate(provider, name, effort)
        if max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
        self.name, self.effort, self.ledger = name, effort, ledger
        self.provider = provider
        self.instructions, self.max_output_tokens = instructions, max_output_tokens
        self.send = send or partial(post, api_key(provider), provider=provider,
                                   record_transport=provider == "openrouter")
        self.totals = Counter()
        self.record_exchanges = record_exchanges
        self.exchanges = SimpleQueue()
        self.exchange_count = 0

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
        if self.record_exchanges and self.provider == "openai" and self.effort != "none":
            body["reasoning"]["summary"] = "auto"
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
            if self.record_exchanges:
                error.attempt = {"request": body, "transport_error": str(error),
                                 "uncertain_attempts": error.uncertain_attempts}
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
        if self.record_exchanges:
            attempt.update(request=body, output=response.get("output", []),
                           response_error=response.get("error"),
                           incomplete_details=response.get("incomplete_details"))
        # Opt-in for WH3; the existing Spire trace schema and timing stay unchanged.
        if "_transport" in response:
            transport = response["_transport"]
            attempt.update({key: transport[key] for key in
                            ("provider_processing_ms", "actual_model", "transport_attempts")})
            attempt["seconds"] = transport["wall_seconds"]
            if self.provider != "openai":
                attempt.update(provider=self.provider, backend=transport.get("backend"),
                               backend_model=transport.get("backend_model"),
                               router_attempts=transport.get("router_attempts"))
        self.totals.update(
            calls=1, usd=usd, seconds=attempt["seconds"], input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            reasoning_tokens=(usage.get("output_tokens_details") or {}).get(
                "reasoning_tokens", 0),
            cached_tokens=(usage.get("input_tokens_details") or {}).get("cached_tokens", 0),
        )
        if cost_error:
            error = APIError(f"{cost_error}; charged reservation and stopped")
        elif usd > reservation:
            error = APIError("Reported cost exceeded reservation; charged actual cost and stopped")
        elif response.get("error"):
            attempt["error"] = f"{self.provider} returned a failed response {response.get('id')}"
            error = APIError(attempt["error"], retryable=True)
        else:
            return attempt
        # Attached even without exchange capture, so the caller keeps the billed attempt.
        error.attempt = attempt
        raise error

    def _charge_uncertain(self, reservation: float, attempts: int) -> None:
        if attempts:
            usd = reservation * attempts
            self.ledger.charge(usd, model=self.name, provider=self.provider, estimated=True,
                               reason="uncertain_transport", attempts=attempts)
            self.totals.update(usd=usd, uncertain_transport_attempts=attempts)

    def ask(self, prompt: str, schema: dict, parse, retries: int) -> tuple[object, list[dict]]:
        """The parsed reply and every attempt. A reply that ``parse`` rejects with
        ValueError is retried with the error appended to the prompt, or with a cut-off
        notice when a reply cut at the output limit is not valid JSON; a failed response is
        resent unchanged. The last failure is raised when retries run out; an APIError then
        carries the attempts made so far as ``attempts``."""
        attempts, feedback = [], ""
        self.exchange_count += 1
        exchange = {"id": f"m{self.exchange_count}", "prompt": prompt, "attempts": attempts}
        try:
            for remaining in range(retries, -1, -1):
                failure = None
                try:
                    attempt = self.call(prompt + feedback, schema)
                except APIError as error:
                    if not hasattr(error, "attempt"):
                        raise
                    failure, attempt = error, error.attempt
                if self.record_exchanges:
                    attempt["exchange_id"] = exchange["id"]
                attempts.append(attempt)
                if failure:
                    if failure.retryable and remaining:
                        continue
                    raise failure
                try:
                    return parse(attempt["text"]), attempts
                except ValueError as error:
                    attempt["error"] = str(error)
                    feedback = (CUT_OFF if attempt["status"] == "incomplete"
                                and isinstance(error, json.JSONDecodeError) else
                                f"\n\nYour previous reply was invalid: {error}. Reply again.")
            raise InvalidReply(attempts)
        except Exception as error:
            if isinstance(error, APIError):
                error.attempts = attempts
            if self.record_exchanges:
                exchange["error"] = {"type": type(error).__name__, "message": str(error)}
            raise
        finally:
            if self.record_exchanges:
                self.exchanges.put(exchange)

    def drain_exchanges(self):
        """Completed calls, including failures and unadopted asynchronous replies.

        The caller writes them on its own thread. Opt-in keeps Spire evidence unchanged.
        """
        while True:
            try:
                yield self.exchanges.get_nowait()
            except Empty:
                return
