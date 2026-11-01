"""Declared model routes; configuration never makes a network request.

OpenAI and OpenRouter take Responses API requests; Anthropic's Messages API gets the same
request translated in ``gameai.llm``. Prices are USD per million input, cached input and
output tokens. OpenRouter prices are enforced routing ceilings, not the catalogue's cheapest
advertised endpoint. Checked 2026-10-16; actual OpenRouter charges come from the response's
usage.cost. Reasoning efforts are per model, each accepted by one live schema call on
2026-10-16: OpenAI's lists come from the API's own unsupported-value errors, OpenRouter's
from the catalogue's supported_efforts. A model whose catalogue entry lists none is on/off:
"none" and "medium" (OpenRouter's level for reasoning enabled). Anthropic's prices and
efforts are from its pricing and effort pages, read 2026-10-31.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    url: str
    key_env: str
    key_file_env: str
    prices: dict[str, tuple[float, float, float]]
    efforts: dict[str, tuple[str, ...]]


OPENAI = Provider(
    "https://api.openai.com/v1/responses", "OPENAI_API_KEY", "SPIRE_OPENAI_KEY_FILE",
    {"gpt-6-luna": (0.10, 0.01, 0.50), "gpt-6-sol": (2.00, 0.20, 10.00),
     "gpt-6.1-sol": (2.00, 0.10, 10.00), "gpt-6-astra": (10.00, 1.00, 50.00)},
    {**dict.fromkeys(("gpt-6-luna", "gpt-6-sol"),
                     ("none", "low", "medium", "high", "xhigh", "max")),
     **dict.fromkeys(("gpt-6.1-sol", "gpt-6-astra"), ("low", "medium", "high", "xhigh", "max"))},
)
OPENROUTER = Provider(
    "https://openrouter.ai/api/v1/responses", "OPENROUTER_API_KEY", "OPENROUTER_API_KEY_FILE",
    {"z-ai/glm-5.3": (1.40, 1.40, 4.80), "moonshotai/kimi-k3": (3.00, 3.00, 15.00),
     "stepfun/step-5-preview": (1.00, 1.00, 2.70), "qwen/qwen3.6-35b-a3b": (0.15, 0.15, 1.00)},
    {"z-ai/glm-5.3": ("low", "high", "max"), "moonshotai/kimi-k3": ("none", "low", "high", "max"),
     "stepfun/step-5-preview": ("low", "medium", "high"),
     # On/off: the catalogue lists no effort levels. Live 2026-10-17, every effort value was
     # accepted, "none" did not reason, and low to max all reasoned 1.3k-4k tokens.
     "qwen/qwen3.6-35b-a3b": ("none", "medium")},
)
# Haiku's prices hold for prompts up to 100,000 tokens (five times higher above; gameai.llm
# refuses larger Haiku requests). Nothing is cached: no request sends cache_control.
# JUDGEMENT: Anthropic efforts — assistant's plan, adopted 2026-10-31: no "none" (thinking off
# only on Haiku and Sonnet, at high or below); a "none" mode would need an effort chosen for it.
# JUDGEMENT: Haiku first — assistant's plan, adopted 2026-10-31: WH3's default Anthropic model;
# Sonnet first would change every job that names no @MODEL.
# JUDGEMENT: Effort labels — assistant's plan, 2026-10-31: Anthropic "high" is not OpenAI
# "high" in compute; any cross-provider comparison at one label rests on treating them alike.
ANTHROPIC = Provider(
    "https://api.anthropic.com/v1/messages", "GAMEAI_ANTHROPIC_API_KEY",
    "GAMEAI_ANTHROPIC_API_KEY_FILE",
    {"claude-haiku-5-5": (0.10, 0.01, 0.50), "claude-sonnet-5-5": (2.00, 0.10, 10.00),
     "claude-opus-5-5": (4.00, 0.20, 20.00)},
    dict.fromkeys(("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"),
                  ("low", "medium", "high", "xhigh", "max")),
)
# JUDGEMENT: API version — assistant's plan, adopted 2026-10-31: 2026-10-21, the latest; for
# Messages it only refuses fields never sent here. 2023-06-01 would accept the same requests.
ANTHROPIC_VERSION = "2026-10-21"
# A key not scoped to one workspace needs the workspace's ID on every request.
ANTHROPIC_WORKSPACE_ENV = "GAMEAI_ANTHROPIC_WORKSPACE_ID"
# Per-model request fields, sent and recorded with every request. Qwen3.6-35B-A3B is the
# open-weight model to fine-tune: its baseline runs at fp8 or better (its cheapest endpoint
# is fp4) with the catalogue's default sampling made explicit.
# Failure rates differ by backend (docs/twwarhammer3/log.md, queue C), so each compared
# model is served by one backend with no fallback: the endpoints checked live on 2026-10-18
# (latency.md P3). Step 5 preview is unpinned.
# JUDGEMENT: Backend pins — assistant under delegation, b36 (2026-10-19; flagged by Claude,
# 2026-10-28): one backend per compared model, no fallback, its failures the model's. Other
# backends change latency and failure rates; state.md decision 7 asks the owner to review.
def _pin(slug: str) -> dict:
    return {"only": [slug], "order": [slug], "allow_fallbacks": False}


ROUTES = {"qwen/qwen3.6-35b-a3b": {"quantizations": ["fp8", "bf16"], **_pin("parasail")},
          "z-ai/glm-5.3": _pin("decart"), "moonshotai/kimi-k3": _pin("sail-research")}
# JUDGEMENT?: Student serving — assistant, 2026-10-17 (flagged by Claude, 2026-10-28): Qwen3.6
# at fp8/bf16 with explicit temperature 1.0 and top_p 0.95; others at backend defaults. fp4, or
# explicit sampling for every model, changes its traces and datasets (state.md decision 7).
SAMPLING = {"qwen/qwen3.6-35b-a3b": {"temperature": 1.0, "top_p": 0.95}}
# Token logprobs, sent only for callers that ask (Spire's play since 2026-10-23). A live probe
# that day: Parasail returns each output token's logprob, bytes and top alternatives through
# the Responses route for `logprobs` with `top_logprobs`; under a strict schema they are the
# constrained distribution (masked alternatives read -9999). A sent seed did not repeat replies.
# JUDGEMENT: 10 alternatives (assistant, 2026-10-23): every single-digit choice; 5 halves the
# size, 20 doubles it. The choice distributions in Spire traces rest on it.
LOGPROBS = {"qwen/qwen3.6-35b-a3b": 10}
PROVIDERS = {"openai": OPENAI, "openrouter": OPENROUTER, "anthropic": ANTHROPIC}


def get_provider(name: str) -> Provider:
    try:
        return PROVIDERS[name]
    except KeyError:
        raise ValueError(f"invalid choice: provider {name!r}; use {', '.join(PROVIDERS)}") from None


def validate(provider: str, model: str, effort: str) -> None:
    spec = get_provider(provider)
    if model not in spec.prices:
        raise ValueError(f"invalid choice for {provider}: use a policy with a model in "
                         f"{', '.join(spec.prices)}")
    if effort not in spec.efforts[model]:
        raise ValueError(f"invalid choice for {provider} {model}: use an effort in "
                         f"{', '.join(spec.efforts[model])}")


def logprobs(model: str) -> dict:
    """Request fields that return ``model``'s token logprobs, or none where undeclared."""
    return {"logprobs": True, "top_logprobs": LOGPROBS[model]} if model in LOGPROBS else {}


def routing(provider: str, model: str) -> dict:
    """Request fields that route and sample ``model`` beyond the transport's own."""
    if provider != "openrouter":
        return {}
    price_in, _, price_out = get_provider(provider).prices[model]
    return {"provider": {"require_parameters": True,
                         "max_price": {"prompt": price_in, "completion": price_out, "request": 0},
                         **ROUTES.get(model, {})},
            **SAMPLING.get(model, {})}
