"""Language artifacts through real rollout/evidence code, replacing only the engine and model."""

import json
from pathlib import Path

import pytest

pytest.importorskip("torch")

from test_language_policy import (  # noqa: E402
    TinyModel,
    TinyTokenizer,
    adapter_declaration,
    declaration,
)
from test_rollout_lifecycle import combat_message, harness, terminal_message  # noqa: E402

from gameai import provenance  # noqa: E402
from spire.combat import rollout  # noqa: E402
from spire.combat.evidence import audit_run, normalized_observation_fingerprint  # noqa: E402
from spire.engine.bridge import BridgeDisconnected  # noqa: E402
from spire.language import evaluation as language_evaluation  # noqa: E402
from spire.protocol import decision_from_message  # noqa: E402

# Re-export shared fixtures without creating a separate test helper framework.
__all__ = ["adapter_declaration", "declaration", "harness"]


@pytest.fixture
def setup(tmp_path, adapter_declaration, harness, monkeypatch):
    monkeypatch.setattr(
        provenance.subprocess,
        "check_output",
        lambda command, **kwargs: "a" * 40 if command[:3] == ["git", "rev-parse", "HEAD"] else "",
    )
    declaration_path = tmp_path / "policy.json"
    declaration_path.write_text(json.dumps(adapter_declaration))
    public = decision_from_message(combat_message(), session_id="fixture", sequence=2).to_dict()
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "purpose": "development",
                "id": "language-fixture",
                "game_seed": "TEST1",
                "policy_seed": 1000,
                "episodes": 2,
                "expected_start_sha256": normalized_observation_fingerprint(public["observation"]),
            }
        )
    )
    monkeypatch.setattr(language_evaluation, "dependency_versions", lambda: {"torch": "fixture"})
    return declaration_path, suite_path, tmp_path / "evaluation", harness


def session(*, failure=None):
    menu = {"ready_for_command": True, "in_game": False, "available_commands": ["start"]}
    return [menu, combat_message(), failure or terminal_message()]


def test_language_success_uses_frozen_adapter_and_audited_original_trace(setup):
    declaration_path, suite_path, output, runtime = setup
    runtime.sessions = [session(), session()]
    model, tokenizer = TinyModel(), TinyTokenizer()

    def loader(declaration):
        assert declaration["adapter"] is not None
        return model, tokenizer

    report = language_evaluation.evaluate_language(
        declaration_path, suite_path, output, loader=loader
    )
    assert report["valid"], report
    assert report["policy_artifact"]["type"] == "language"
    assert report["policy_artifact"]["pretrained_base_only"] is False
    assert report["metrics"]["wins"] == report["metrics"]["policy_attempts"] == 2
    assert report["metrics"]["policy_attempt_win_rate"] == 1
    assert audit_run(output)["valid"]
    assert (
        output / "frozen-language/declaration.json"
    ).read_bytes() == declaration_path.read_bytes()
    assert (
        output / "frozen-language/adapter/adapter_model.safetensors"
    ).read_bytes() == b"test adapter"
    assert all(
        bridge.commands == ["START IRONCLAD 0 TEST1", "play 1 0"] for bridge in runtime.bridges
    )
    assert all(game.closed for game in runtime.games)


@pytest.mark.parametrize(
    "tokens,response,kind",
    [
        (13, "I choose attack", "invalid_completion"),
        (2049, '{"a":0}', "context_limit"),
    ],
)
def test_policy_failures_keep_all_scheduled_attempts_without_engine_commands(
    setup,
    tokens,
    response,
    kind,
):
    declaration_path, suite_path, output, runtime = setup
    runtime.sessions = [session(), session()]
    model, tokenizer = TinyModel(), TinyTokenizer(response, tokens)
    report = language_evaluation.evaluate_language(
        declaration_path,
        suite_path,
        output,
        loader=lambda _: (model, tokenizer),
    )
    assert report["valid"], report
    assert report["metrics"]["policy_failures"] == 2
    assert report["metrics"]["completed_gameplay"] == 0
    assert report["metrics"]["win_rate"] is None
    assert report["metrics"]["policy_attempt_win_rate"] == 0
    audit = audit_run(output)
    assert audit["valid"], audit
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "completed"
    assert [item["policy_seed"] for item in manifest["episodes"]] == [1000, 1001]
    for result in manifest["episodes"]:
        assert result["status"] == "policy_failure"
        assert result["policy_failure"]["kind"] == kind
        assert result["combat_actions"] == result["invalid_actions"] == 0
        assert result["turns"] == 1
    assert all(bridge.commands == ["START IRONCLAD 0 TEST1"] for bridge in runtime.bridges)
    assert len(model.calls) == (2 if kind == "invalid_completion" else 0)


def test_gameplay_and_policy_failures_have_both_denominators(setup):
    declaration_path, suite_path, output, runtime = setup
    runtime.sessions = [session(), session()]
    tokenizer = TinyTokenizer()
    model = TinyModel()
    original = model.generate

    def generate(**kwargs):
        tokenizer.response = '{"a":0}' if len(model.calls) == 0 else "invalid"
        return original(**kwargs)

    model.generate = generate
    report = language_evaluation.evaluate_language(
        declaration_path,
        suite_path,
        output,
        loader=lambda _: (model, tokenizer),
    )
    assert report["valid"], report
    assert report["metrics"]["wins"] == report["metrics"]["policy_failures"] == 1
    assert report["metrics"]["win_rate"] == 1
    assert report["metrics"]["policy_attempt_win_rate"] == 0.5


def test_infrastructure_failure_stops_without_claiming_policy_failure(setup):
    declaration_path, suite_path, output, runtime = setup
    runtime.sessions = [session(failure=BridgeDisconnected("disconnected")), session()]
    report = language_evaluation.evaluate_language(
        declaration_path,
        suite_path,
        output,
        loader=lambda _: (TinyModel(), TinyTokenizer()),
    )
    assert not report["valid"]
    assert report["metrics"]["infrastructure_failures"] == 1
    assert report["metrics"]["policy_failures"] == 0
    assert report["metrics"]["unattempted_episodes"] == 1
    assert len(runtime.games) == 1


@pytest.mark.parametrize("target", ["base", "adapter", "declaration", "snapshot", "tensor"])
def test_after_collection_mutation_invalidates_and_retains_original_identity(
    setup, monkeypatch, target
):
    declaration_path, suite_path, output, runtime = setup
    runtime.sessions = [session(), session()]
    original = language_evaluation.rollout
    model = TinyModel()

    def tamper(*args, **kwargs):
        result = original(*args, **kwargs)
        declaration = json.loads(declaration_path.read_bytes())
        if target in {"base", "adapter"}:
            record = declaration[target]
            (Path(record["directory"]) / next(iter(record["files"]))).write_bytes(b"changed")
        elif target == "declaration":
            declaration_path.write_text("{}")
        elif target == "snapshot":
            path = output / "frozen-language/declaration.json"
            path.chmod(0o644)
            path.write_text("{}")
        else:
            model.weight.data.add_(1)
        return result

    monkeypatch.setattr(language_evaluation, "rollout", tamper)
    report = language_evaluation.evaluate_language(
        declaration_path,
        suite_path,
        output,
        loader=lambda _: (model, TinyTokenizer()),
    )
    assert not report["valid"] and report["consistency_errors"]
    assert report["policy_artifact"]["declaration"]["base"]["id"] == "Qwen/Qwen3-0.6B"


def test_declaration_mismatch_fails_before_any_game(setup):
    declaration_path, suite_path, output, runtime = setup
    declaration = json.loads(declaration_path.read_bytes())
    declaration["base"]["revision"] = "wrong"
    declaration_path.write_text(json.dumps(declaration))
    with pytest.raises(ValueError, match="pinned"):
        language_evaluation.evaluate_language(
            declaration_path,
            suite_path,
            output,
            loader=lambda _: (TinyModel(), TinyTokenizer()),
        )
    assert not runtime.games and not output.exists()


def test_tensor_mutation_between_attempts_blocks_second_launch(setup):
    declaration_path, suite_path, output, runtime = setup
    model = TinyModel()

    def ending():
        model.weight.data.add_(1)
        return terminal_message()

    runtime.sessions = [[*session()[:2], ending], session()]
    with pytest.raises(ValueError, match="tensors changed"):
        language_evaluation.evaluate_language(
            declaration_path,
            suite_path,
            output,
            loader=lambda _: (model, TinyTokenizer()),
        )
    assert len(runtime.games) == 1
    assert json.loads((output / "manifest.json").read_text())["status"] == "interrupted"


def test_language_rollout_requires_factory_before_output(tmp_path):
    with pytest.raises(ValueError, match="policy factory"):
        rollout.rollout(tmp_path / "run", {"policy": "language", "game_seed": "TEST1"})
    assert not (tmp_path / "run").exists()


def test_base_only_language_artifact(setup, declaration):
    declaration_path, suite_path, output, runtime = setup
    declaration_path.write_text(json.dumps(declaration))
    runtime.sessions = [session(), session()]
    report = language_evaluation.evaluate_language(
        declaration_path,
        suite_path,
        output,
        loader=lambda _: (TinyModel(), TinyTokenizer()),
    )
    assert report["valid"] and report["policy_artifact"]["pretrained_base_only"]
    assert report["policy_artifact"]["adapter_snapshot_path"] is None
    assert not (output / "frozen-language/adapter").exists()


@pytest.mark.parametrize("target", ["prompt_tokens", "completion_token_ids", "chat_prompt_sha256"])
def test_token_evidence_mismatch_invalidates_successful_evaluation(setup, monkeypatch, target):
    declaration_path, suite_path, output, runtime = setup
    runtime.sessions = [session(), session()]
    original = language_evaluation.rollout

    def tamper(*args, **kwargs):
        result = original(*args, **kwargs)
        path = output / "episode-0000/trace.jsonl"
        events = [json.loads(line) for line in path.read_text().splitlines()]
        behavior = next(event["behavior"] for event in events if event["kind"] == "decision")
        if target == "prompt_tokens":
            behavior[target] += 1
        elif target == "completion_token_ids":
            behavior[target] = [99]
        else:
            behavior[target] = "0" * 64
        path.write_text("".join(json.dumps(event) + "\n" for event in events))
        return result

    monkeypatch.setattr(language_evaluation, "rollout", tamper)
    result = language_evaluation.evaluate_language(
        declaration_path,
        suite_path,
        output,
        loader=lambda _: (TinyModel(), TinyTokenizer()),
    )
    assert not result["valid"] and result["consistency_errors"]


def test_failure_after_a_successful_action_remains_linked_and_counts_once(setup):
    declaration_path, suite_path, output, runtime = setup
    second = combat_message()
    second["game_state"]["combat_state"]["turn"] = 2
    runtime.sessions = [[*session()[:2], second], session()]
    model, tokenizer = TinyModel(), TinyTokenizer()
    original = model.generate

    def generate(**kwargs):
        tokenizer.response = '{"a":0}' if not model.calls else "invalid"
        return original(**kwargs)

    model.generate = generate
    result = language_evaluation.evaluate_language(
        declaration_path,
        suite_path,
        output,
        loader=lambda _: (model, tokenizer),
    )
    assert result["valid"], result
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["episodes"][0]["combat_actions"] == 1
    assert manifest["episodes"][0]["turns"] == 2
    assert manifest["episodes"][0]["invalid_actions"] == 0
    assert result["metrics"]["policy_failures"] == 2


def test_borrowed_policy_stays_open_after_child_and_requires_matching_declaration(setup):
    from spire.language.policy import LanguagePolicy

    declaration_path, suite_path, output, runtime = setup
    runtime.sessions = [session(), session()]
    with LanguagePolicy.from_declaration(
        declaration_path, loader=lambda _: (TinyModel(), TinyTokenizer())
    ) as policy:
        result = language_evaluation.evaluate_language(
            declaration_path, suite_path, output, _policy=policy
        )
        assert result["valid"] and policy.model is not None
        policy.verify_frozen()
        changed = json.loads(declaration_path.read_bytes())
        changed["provenance"]["different"] = True
        declaration_path.write_text(json.dumps(changed))
        with pytest.raises(ValueError, match="differs from declaration"):
            language_evaluation.evaluate_language(
                declaration_path, suite_path, output.parent / "different", _policy=policy
            )
        assert policy.model is not None
    assert policy.model is None
