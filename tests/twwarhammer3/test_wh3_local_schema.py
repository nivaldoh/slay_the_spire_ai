"""C's wire schema follows the provider contract while retaining its local message cap."""

import json

import pytest
from wh3_fixtures import FakeSend

from gameai.ledger import Ledger
from gameai.providers import get_provider
from twwarhammer3.battle import llm, local_team
from twwarhammer3.protocol import PolicyFailure


def view():
    return {"time_ms": 1000, "friendly": [{"id": "f1", "type": "sword", "men": 90,
                                          "state": []}], "enemy": []}


def member(tmp_path, provider, messages):
    send = FakeSend(json.dumps({"orders": [{"unit": "f1", "type": "halt"}],
                                "reason": "hold", "notes": None, "messages": messages}))
    policy = llm.LLMPolicy(next(iter(get_provider(provider).prices)), "low",
                           Ledger(tmp_path / "spend.jsonl", 1), send=send, provider=provider)
    return local_team.LocalModel(policy), send


@pytest.mark.parametrize("provider,wire_bound", (("anthropic", None), ("openai", 2)))
def test_c_schema_omits_anthropic_unsupported_array_constraint(tmp_path, provider, wire_bound):
    # Independent reference: Anthropic Structured outputs, JSON Schema limitations,
    # disallows array constraints beyond minItems 0/1; OpenAI supports maxItems.
    policy, send = member(tmp_path, provider, [])
    assert policy.decide(view()) == [{"unit": "f1", "type": "halt"}]
    schema = send.bodies[0]["text"]["format"]["schema"]
    assert schema["properties"]["messages"].get("maxItems") == wire_bound


def test_anthropic_oversized_messages_are_still_rejected_locally_without_partial_orders(tmp_path):
    policy, send = member(tmp_path, "anthropic", [{"channel": "signal", "code": "READY"}] * 3)
    with pytest.raises(PolicyFailure):
        policy.decide(view())
    assert len(send.bodies) == 1
    assert policy.drain_messages() == []
