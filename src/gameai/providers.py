"""Declared Responses API routes; configuration never makes a network request.

Prices are USD per million input, cached input and output tokens. OpenRouter prices
are enforced routing ceilings, not the catalogue's cheapest advertised endpoint.
Checked 2026-10-16; actual OpenRouter charges come from the response's usage.cost.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    url: str
    key_env: str
    key_file_env: str
    prices: dict[str, tuple[float, float, float]]
    efforts: tuple[str, ...]


OPENAI = Provider(
    "https://api.openai.com/v1/responses", "OPENAI_API_KEY", "SPIRE_OPENAI_KEY_FILE",
    {"gpt-6-luna": (0.10, 0.01, 0.50), "gpt-6-sol": (2.00, 0.20, 10.00),
     "gpt-6.1-sol": (2.00, 0.10, 10.00), "gpt-6-astra": (10.00, 1.00, 50.00)},
    ("none", "low", "medium", "high"),
)
OPENROUTER = Provider(
    "https://openrouter.ai/api/v1/responses", "OPENROUTER_API_KEY", "OPENROUTER_API_KEY_FILE",
    {"z-ai/glm-5.3": (1.40, 1.40, 4.80), "moonshotai/kimi-k3": (3.00, 3.00, 15.00),
     "stepfun/step-5-preview": (1.00, 1.00, 2.70)},
    ("low", "high"),
)
PROVIDERS = {"openai": OPENAI, "openrouter": OPENROUTER}


def get_provider(name: str) -> Provider:
    try:
        return PROVIDERS[name]
    except KeyError:
        raise ValueError(f"invalid choice: provider {name!r}; use {', '.join(PROVIDERS)}") from None


def validate(provider: str, model: str, effort: str) -> None:
    spec = get_provider(provider)
    if model not in spec.prices or effort not in spec.efforts:
        raise ValueError(f"invalid choice for {provider}: use a policy with a model in "
                         f"{', '.join(spec.prices)} and an effort in {', '.join(spec.efforts)}")


def routing(provider: str, model: str) -> dict:
    if provider == "openai":
        return {}
    price_in, _, price_out = get_provider(provider).prices[model]
    return {"provider": {"require_parameters": True,
                         "max_price": {"prompt": price_in, "completion": price_out, "request": 0}}}
