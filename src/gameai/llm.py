"""Model API calls for any game: transport, spend and the reply-retry loop.

Standard library only. Requests and replies use the OpenAI Responses API shape; ``post``
translates them to and from Anthropic's Messages API, so nothing else knows that format.
Provider settings name the credential environment variables; keys are never logged or
written to evidence. A ``Model`` reserves a conservative cost including retries before
sending, then charges reported usage. Attempts with uncertain billing are charged at the
reserved rate. The game supplies instructions, prompt, reply schema and parser.
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
from gameai.providers import (
    ANTHROPIC_VERSION,
    ANTHROPIC_WORKSPACE_ENV,
    OPENAI,
    get_provider,
    logprobs,
    routing,
    validate,
)

API_URL = OPENAI.url
PRICES = OPENAI.prices
TRANSPORT_ATTEMPTS = 3
# JUDGEMENT?: Resends and retry text — assistant, 2026-10-12 and 10-17 (flagged by Claude, 10-28):
# failed responses are resent twice per ask on their own counter; an invalid reply is re-asked with
# fixed text, not a versioned prompt. Exported rows and export.py's RETRY_SUFFIX rest on that text.
FAILED_RESENDS = 2  # per ask, apart from the parse retries
# A non-streaming reply arrives only when finished: room for a 16,000-token reply at about
# 30 tokens/s. No OpenAI attempt so far took over 32 s; longer ones are untested.
# JUDGEMENT?: 600 s per read x 3 attempts: one stalled call silences a direct WH3 controller
# for up to 30 min (card battles end by 22 min) and bills 3 reservations. The 16k cap is the
# owner's; 600 s itself is the assistant's (b27). Engineering or a benchmark parameter?
READ_TIMEOUT_S = 600
TRANSIENT_HTTP = {408, 409, 429, 500, 502, 503, 504}
# JUDGEMENT: Anthropic 529 — assistant's plan, adopted 2026-10-31: resent like the codes above and
# charged at the reservation each time; raising at once would forfeit sooner and bill less.
OVERLOADED = {"anthropic": {529}}  # other providers' 529s raise at once, as before
CUT_OFF = ("\n\nYour previous reply was cut off at the output limit before the JSON ended."
           " Reply again.")
JSON_TYPES = {"object": dict, "array": list, "string": str, "integer": int,
              "number": (int, float), "boolean": bool, "null": type(None)}


class APIError(RuntimeError):
    """Transport or service failure: infrastructure, never a gameplay outcome. ``retryable``
    names the failure kind, a failed response, which ``Model.ask`` resends unchanged up to
    FAILED_RESENDS times; it stays set on the one raised after they run out."""

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
    if not key:
        path = os.environ.get(spec.key_file_env)
        if not path:
            raise APIError(f"Set {spec.key_env} or {spec.key_file_env}")
        key = Path(path).expanduser().read_text().strip()
        if not key:
            raise APIError(f"Empty credential file named by {spec.key_file_env}")
    # Both fail here, before any game launches: the server would answer HTTP 400, which WH3
    # scores as the model failing. A paste once left terminal escape codes before a key.
    if not key.isprintable():
        raise APIError(f"The {provider} key holds unprintable characters; write it again")
    if provider == "anthropic" and not os.environ.get(ANTHROPIC_WORKSPACE_ENV):
        raise APIError(f"Set {ANTHROPIC_WORKSPACE_ENV} to the workspace each request bills")
    return key


def _usage_counts(usage: dict) -> tuple[int, int, int]:
    if not isinstance(usage, dict):
        raise ValueError("Reported usage must be an object")
    details = usage.get("input_tokens_details")
    if details is None:
        details = {}
    if not isinstance(details, dict):
        raise ValueError("Reported input_tokens_details must be an object")
    counts = (usage.get("input_tokens"), details.get("cached_tokens", 0),
              usage.get("output_tokens"))
    if any(not _is_json(count, "integer") or count < 0 for count in counts):
        raise ValueError("Reported token counts must be finite nonnegative integers")
    input_tokens, cached, output_tokens = counts
    if cached > input_tokens:
        raise ValueError("Reported cached tokens exceed input tokens")
    return input_tokens, cached, output_tokens


def usage_cost(model: str, usage: dict, provider: str = "openai") -> float:
    if provider == "openrouter":
        cost = usage.get("cost") if isinstance(usage, dict) else None
        if (isinstance(cost, bool) or not isinstance(cost, (int, float))
                or not math.isfinite(cost) or cost < 0):
            raise ValueError("OpenRouter did not report a finite nonnegative usage.cost")
        return cost
    price_in, price_cached, price_out = get_provider(provider).prices[model]
    input_tokens, cached, output_tokens = _usage_counts(usage)
    cost = (
        (input_tokens - cached) * price_in
        + cached * price_cached
        + output_tokens * price_out
    ) / 1e6
    if not math.isfinite(cost) or cost < 0:
        raise ValueError("Calculated usage cost must be finite and nonnegative")
    return cost


def post(key: str, body: dict, attempts: int = TRANSPORT_ATTEMPTS, *,
         record_transport: bool = False, provider: str = "openai",
         timeout_s: float | None = None) -> dict:
    """One API call; retries only transient transport and service errors. An Anthropic
    request is translated before the first attempt (a ValueError then sends nothing) and its
    reply after the read, outside the retries, so a translation can never resend a call.
    timeout_s selects the per-read limit; omitted calls keep the marked shared default."""
    url = get_provider(provider).url
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if provider == "openrouter":
        headers["X-OpenRouter-Metadata"] = "enabled"
    elif provider == "anthropic":
        body = _to_messages(body)
        headers["anthropic-version"] = ANTHROPIC_VERSION
        if workspace := os.environ.get(ANTHROPIC_WORKSPACE_ENV):
            headers["anthropic-workspace-id"] = workspace
    data = json.dumps(body).encode()
    transient = TRANSIENT_HTTP | OVERLOADED.get(provider, set())
    started = time.time()
    uncertain = 0
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(request, timeout=(
                    READ_TIMEOUT_S if timeout_s is None else timeout_s)) as response:
                value = json.load(response)
            break
        except urllib.error.HTTPError as error:
            # Read past the display boundary so truncation cannot leave a key prefix behind.
            detail = error.read(500 + len(key)).decode(errors="replace").replace(key, "<key>")[:500]
            uncertain += error.code >= 500 or error.code == 408
            if error.code not in transient or attempt == attempts:
                raise APIError(f"HTTP {error.code}: {detail}", uncertain) from None
        except (OSError, http.client.HTTPException, ValueError) as error:
            uncertain += 1
            if attempt == attempts:
                detail = str(error).replace(key, "<key>")
                raise APIError(f"{type(error).__name__}: {detail}", uncertain) from None
        time.sleep(2**attempt)
    if provider == "anthropic":
        value = _from_messages(value)
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


# Model.call's request fields; any other has no translation and is refused before sending.
MESSAGES_FIELDS = {"model", "instructions", "input", "max_output_tokens", "reasoning", "text",
                   "store"}
# Haiku 5.5 bills prompts over 100,000 tokens at five times the declared prices, which
# usage_cost would undercharge. The server adds its own prompt for thinking and structured
# outputs, so this byte cap is a margin under that step, not a proof.
# JUDGEMENT: Haiku byte cap — assistant's plan, adopted 2026-10-31: a larger request is refused
# (in WH3, a forfeit); declaring the higher prices instead would send and charge it.
LONG_PROMPT_BYTES = {"claude-haiku-5-5": 100_000}


def _to_messages(body: dict) -> dict:
    """The Messages API request for the Responses-shaped ``body`` that ``Model.call`` builds.
    ``store`` is dropped: Anthropic keeps no response for later turns."""
    unknown = sorted(body.keys() - MESSAGES_FIELDS)
    if unknown:
        raise ValueError(f"no Anthropic translation for request fields {unknown}")
    wire = {"model": body["model"], "max_tokens": body["max_output_tokens"],
            "system": body["instructions"], "messages": body["input"]}
    reasoning = body.get("reasoning") or {}
    config = {"effort": reasoning["effort"]} if "effort" in reasoning else {}
    if "text" in body:
        config["format"] = {"type": "json_schema", "schema": body["text"]["format"]["schema"]}
    if config:
        wire["output_config"] = config
    if reasoning.get("summary") == "auto":
        wire["thinking"] = {"type": "adaptive", "display": "summarized"}
    limit = LONG_PROMPT_BYTES.get(body["model"])
    if limit and len(json.dumps(wire).encode()) > limit:
        raise ValueError(f"{body['model']} request over {limit} bytes, where its long-prompt"
                         " prices start; they are not declared")
    return wire


def _from_messages(reply: dict) -> dict:
    """The Responses-shaped reply for a Messages API ``reply``. Unknown blocks and stop
    reasons pass without raising: a raise here would escape the call's charge."""
    blocks = [block for block in reply.get("content") or [] if isinstance(block, dict)]
    # Omitted thinking has empty text and redacted thinking none: nothing to keep.
    output = [{"type": "reasoning",
               "summary": [{"type": "summary_text", "text": block["thinking"]}]}
              for block in blocks if block.get("type") == "thinking" and block.get("thinking")]
    content = [{"type": "output_text", "text": block["text"]} for block in blocks
               if block.get("type") == "text" and isinstance(block.get("text"), str)]
    stop = reply.get("stop_reason")
    # JUDGEMENT: Refusals — assistant's plan, adopted 2026-10-31: never sent `fallbacks` (another
    # model would answer); a refusal is OpenAI's refusal shape, re-asked as an invalid reply.
    if stop == "refusal":
        content = [{"type": "refusal", "refusal": "".join(part["text"] for part in content),
                    "stop_details": reply.get("stop_details")}]
    if content:
        output.append({"type": "message", "role": "assistant", "content": content})
    status, details = "completed", None
    if stop == "max_tokens":
        status, details = "incomplete", {"reason": "max_output_tokens"}
    elif stop not in ("end_turn", "refusal"):
        status, details = "incomplete", {"reason": stop}
    usage = reply.get("usage")
    if isinstance(usage, dict):
        # Anthropic's input_tokens leaves out cache reads and writes; Responses' includes them.
        read = usage.get("cache_read_input_tokens") or 0
        usage = {
            "input_tokens": (usage.get("input_tokens") or 0) + read
            + (usage.get("cache_creation_input_tokens") or 0),
            "input_tokens_details": {"cached_tokens": read},
            "output_tokens": usage.get("output_tokens") or 0,
            "output_tokens_details": {"reasoning_tokens": (
                usage.get("output_tokens_details") or {}).get("thinking_tokens") or 0},
        }
    else:
        usage = None  # Model.call then charges the reserved worst case
    return {"id": reply.get("id"), "model": reply.get("model"), "status": status,
            "incomplete_details": details, "output": output, "usage": usage}


def reasoning_parts(output: list | None) -> list[dict]:
    """Text parts of returned reasoning items, with their provider type, field and item index.

    OpenAI and Anthropic return summaries (``summary_text``); open-weight models through
    OpenRouter return the reasoning itself (``reasoning_text`` in ``content``).
    """
    return [dict(part, item_index=i, field=field)
            for i, item in enumerate(output or []) if item.get("type") == "reasoning"
            for field in ("summary", "content")
            for part in item.get(field) or [] if isinstance(part.get("text"), str)]


def _is_json(value, kind: str) -> bool:
    if isinstance(value, bool):
        return kind == "boolean"
    if isinstance(value, (int, float)):
        try:
            if not math.isfinite(value):
                return False  # Python's parser accepts NaN and Infinity; JSON has neither
        except OverflowError:
            return False  # an integer beyond float range
    return isinstance(value, JSON_TYPES[kind])


def check_fields(value, schema: dict, name: str = "reply"):
    """``value`` if it is an object holding every field ``schema`` requires, and each of the
    schema's fields it holds has a type and enum value the schema allows (a boolean is not a
    number, nor is an integer beyond float range); ValueError, which ``ask`` retries,
    otherwise. OpenAI enforces strict schemas, but open-weight backends may not. Extra
    fields pass; items of arrays are the game's to check."""
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    for key, spec in schema["properties"].items():
        if key not in value:
            if key in schema["required"]:
                raise ValueError(f"{name} has no {key!r} field")
            continue
        field = value[key]
        kinds = [spec["type"]] if isinstance(spec["type"], str) else spec["type"]
        if not any(_is_json(field, kind) for kind in kinds):
            raise ValueError(f"{name} field {key!r} must be {' or '.join(kinds)}")
        if "enum" in spec and field not in spec["enum"]:
            allowed = ", ".join(map(str, spec["enum"]))
            raise ValueError(f"{name} field {key!r} must be one of {allowed}")
    return value


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
                 record_exchanges: bool = False, record_logprobs: bool = False):
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
        # Opt-in: token logprobs where providers.LOGPROBS declares them, kept in each
        # attempt's output items.
        self.record_logprobs = record_logprobs
        self.exchanges = SimpleQueue()
        self.exchange_count = 0

    def call(self, prompt: str, schema: dict) -> dict:
        """Send one prompt and return the attempt record: id, status, usage, cost, text.
        The worst-case cost stays reserved in the ledger until the call returns or raises."""
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
            **(logprobs(self.name) if self.record_logprobs else {}),
        }
        # JUDGEMENT: Anthropic summaries — assistant's plan, adopted 2026-10-31: on whenever
        # exchanges are recorded. A separate model writes them; added latency, which WH3
        # counts, is unverified.
        if (self.record_exchanges and self.provider in ("openai", "anthropic")
                and self.effort != "none"):
            body["reasoning"]["summary"] = "auto"
        # Include the schema and an allowance for provider framing at one token/byte.
        tokens = len(json.dumps(body).encode()) + 1024
        price_in, _, price_out = get_provider(self.provider).prices[self.name]
        reservation = (tokens * price_in + self.max_output_tokens * price_out) / 1e6
        held = reservation * TRANSPORT_ATTEMPTS
        self.ledger.reserve(held)
        try:
            return self._call_reserved(body, tokens, reservation)
        finally:
            self.ledger.release(held)

    def _call_reserved(self, body: dict, tokens: int, reservation: float) -> dict:
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
                           response_error=response.get("error"))
        if self.record_exchanges or response.get("incomplete_details"):
            # Kept without capture too: ``ask`` chooses the cut-off notice by its reason.
            attempt["incomplete_details"] = response.get("incomplete_details")
        # Opt-in (both games' play commands): served model, backend and transport wall time.
        if "_transport" in response:
            transport = response["_transport"]
            attempt.update({key: transport[key] for key in
                            ("provider_processing_ms", "actual_model", "transport_attempts")})
            attempt["seconds"] = transport["wall_seconds"]
            if self.provider != "openai":
                attempt["provider"] = self.provider
            if self.provider == "openrouter":
                attempt.update(backend=transport.get("backend"),
                               backend_model=transport.get("backend_model"),
                               router_attempts=transport.get("router_attempts"))
        totals = dict(calls=1, usd=usd, seconds=attempt["seconds"])
        aggregate_tokens = True
        if self.provider != "openrouter":
            try:
                _usage_counts(usage)
            except ValueError:
                # Raw malformed usage stays in the billed attempt, not token totals.
                aggregate_tokens = False
        if aggregate_tokens:
            # OpenRouter reports cost separately; retain its existing token-reading errors.
            totals.update(
                input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"],
                reasoning_tokens=(usage.get("output_tokens_details") or {}).get(
                    "reasoning_tokens", 0),
                cached_tokens=(usage.get("input_tokens_details") or {}).get("cached_tokens", 0),
            )
        self.totals.update(totals)
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
        ValueError, or nests too deeply to parse, is retried with the error appended to the
        prompt, or with a cut-off notice when a reply cut at the output limit is not valid
        JSON. A failed response is resent unchanged, up to FAILED_RESENDS times per ask
        without spending a retry. When either allowance runs out the last failure is raised,
        a rejected reply as InvalidReply; an APIError carries the attempts made so far as
        ``attempts``."""
        attempts, feedback, resends = [], "", FAILED_RESENDS
        self.exchange_count += 1
        exchange = {"id": f"m{self.exchange_count}", "prompt": prompt, "attempts": attempts}
        try:
            while True:
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
                    if failure.retryable and resends:
                        resends -= 1
                        continue
                    raise failure
                try:
                    return parse(attempt["text"]), attempts
                except (ValueError, RecursionError) as error:
                    attempt["error"] = str(error)
                    # Not "Extra data": that JSON ended, and more output followed it.
                    cut = ((attempt.get("incomplete_details") or {}).get("reason")
                           == "max_output_tokens" and isinstance(error, json.JSONDecodeError)
                           and error.msg != "Extra data")
                    feedback = (CUT_OFF if cut else
                                f"\n\nYour previous reply was invalid: {error}. Reply again.")
                if not retries:
                    raise InvalidReply(attempts)
                retries -= 1
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

        The caller writes them on its own thread. Opt-in; both games' play commands record them.
        """
        while True:
            try:
                yield self.exchanges.get_nowait()
            except Empty:
                return
