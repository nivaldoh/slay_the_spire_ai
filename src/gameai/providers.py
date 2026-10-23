"""Declared Responses API routes; configuration never makes a network request.

Prices are USD per million input, cached input and output tokens. OpenRouter prices
are enforced routing ceilings, not the catalogue's cheapest advertised endpoint.
Checked 2026-10-16; actual OpenRouter charges come from the response's usage.cost.
Reasoning efforts are per model, each accepted by one live schema call on 2026-10-16:
OpenAI's lists come from the API's own unsupported-value errors, OpenRouter's from the
catalogue's supported_efforts. A model whose catalogue entry lists none is on/off: "none"
and "medium" (OpenRouter's level for reasoning enabled).
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
# Per-model request fields, sent and recorded with every request. Qwen3.6-35B-A3B is the
# open-weight model to fine-tune: its baseline runs at fp8 or better (its cheapest endpoint
# is fp4) with the catalogue's default sampling made explicit.
# Failure rates differ by backend (docs/twwarhammer3/log.md, queue C), so each compared
# model is served by one backend with no fallback: the endpoints checked live on 2026-10-18
# (latency.md P3). Step 5 preview is unpinned.
def _pin(slug: str) -> dict:
    return {"only": [slug], "order": [slug], "allow_fallbacks": False}


ROUTES = {"qwen/qwen3.6-35b-a3b": {"quantizations": ["fp8", "bf16"], **_pin("parasail")},
          "z-ai/glm-5.3": _pin("decart"), "moonshotai/kimi-k3": _pin("sail-research")}
SAMPLING = {"qwen/qwen3.6-35b-a3b": {"temperature": 1.0, "top_p": 0.95}}
# Token logprobs, sent only for callers that ask (Spire's play since 2026-10-23). A live probe
# that day: Parasail returns each output token's logprob, bytes and top alternatives through
# the Responses route for `logprobs` with `top_logprobs`; under a strict schema they are the
# constrained distribution (masked alternatives read -9999). A sent seed did not repeat replies.
# JUDGEMENT: 10 alternatives (assistant, 2026-10-23): every single-digit choice; 5 halves the
# size, 20 doubles it. The choice distributions in Spire traces rest on it.
LOGPROBS = {"qwen/qwen3.6-35b-a3b": 10}
PROVIDERS = {"openai": OPENAI, "openrouter": OPENROUTER}


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
    if provider == "openai":
        return {}
    price_in, _, price_out = get_provider(provider).prices[model]
    return {"provider": {"require_parameters": True,
                         "max_price": {"prompt": price_in, "completion": price_out, "request": 0},
                         **ROUTES.get(model, {})},
            **SAMPLING.get(model, {})}
