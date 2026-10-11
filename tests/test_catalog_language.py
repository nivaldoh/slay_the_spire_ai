"""Language catalogs through real evaluation/auditing, with CPU model and engine fakes."""

import copy
import json
from pathlib import Path

import pytest

pytest.importorskip("torch")

import test_catalog as catalog_tests  # noqa: E402
import test_language_policy as language_tests  # noqa: E402

from spire import catalog, language_evaluation, language_policy  # noqa: E402
from spire.bridge import BridgeDisconnected  # noqa: E402
from spire.catalog_report import compare_catalogs, render_catalog_report  # noqa: E402
from spire.evidence import audit_run  # noqa: E402

# These fixtures substitute only process/bridge boundaries and source/dependency pins.
declaration = catalog_tests.declaration
runtime_harness = catalog_tests.runtime_harness
run_setup = catalog_tests.run_setup


@pytest.fixture
def language_setup(tmp_path, run_setup, monkeypatch):
    declaration = language_tests.declaration.__wrapped__(tmp_path, monkeypatch)
    declaration = language_tests.adapter_declaration.__wrapped__(tmp_path, declaration)
    artifact = tmp_path / "language.json"
    artifact.write_text(json.dumps(declaration))
    model, tokenizer = language_tests.TinyModel(), language_tests.TinyTokenizer()
    monkeypatch.setattr(language_evaluation, "dependency_versions", lambda: {"test": "cpu"})
    monkeypatch.setattr(language_evaluation, "load_tokenizer", lambda _: tokenizer)
    loaded, closed = [], []
    close = language_policy.LanguagePolicy.close

    def record_close(self):
        closed.append(len(model.calls))
        close(self)

    monkeypatch.setattr(language_policy.LanguagePolicy, "close", record_close)

    def loader(value):
        loaded.append(copy.deepcopy(value))
        assert Path(value["adapter"]["directory"]).parent.name == "frozen-policy"
        return model, tokenizer

    return (*run_setup, artifact, model, tokenizer, loader, loaded, closed)


def evaluate(setup):
    path, output, _, artifact, _, _, loader, _, _ = setup
    return catalog.evaluate_catalog("language", path, output,
                                    language_artifact=artifact, loader=loader)


def test_complete_catalog_owns_one_model_and_links_declarations(language_setup):
    path, output, runtime, original, model, _, _, loaded, closed = language_setup
    original_bytes = original.read_bytes()
    result = evaluate(language_setup)
    assert result["valid"], result["issues"]
    assert len(loaded) == 1 and closed == [4] and len(model.calls) == 4
    assert len(runtime.games) == 4 and all(game.closed for game in runtime.games)
    assert result["metrics"]["wins"] == 3 and result["metrics"]["losses"] == 1
    assert result["macro"]["win_rate"] == result["macro"]["policy_attempt_win_rate"] == 0.5
    artifact = result["policy_artifact"]
    assert artifact["source_declaration"]["sha256"] == catalog._digest(original_bytes)
    assert (output / "frozen-policy/source-declaration.json").read_bytes() == original_bytes
    assert artifact["declaration"]["adapter"]["directory"] == str(output / "frozen-policy/adapter")
    assert artifact["sha256"] != artifact["source_declaration"]["sha256"]
    for index, entry in enumerate(json.loads(path.read_bytes())["schedule"]):
        directory = output / f"runs/attempt-{index:04d}"
        assert audit_run(directory)["valid"]
        child = json.loads((directory / "manifest.json").read_bytes())
        assert child["config"]["policy_seed"] == entry["policy_seed"]
        assert child["config"]["policy_artifact"]["model_sha256"] == artifact["model_sha256"]
    assert catalog.audit_catalog(output) == result
    report = compare_catalogs([output])
    assert report["same_protocol"] and report["valid"]
    assert "Policy failures" in render_catalog_report(report)


@pytest.mark.parametrize("context", [False, True])
def test_policy_failure_continues_schedule_with_no_false_gameplay_macro(language_setup, context):
    _, output, runtime, _, model, tokenizer, _, loaded, closed = language_setup
    if context:
        tokenizer.tokens = 2049
    else:
        generate = model.generate

        def last_fails(**kwargs):
            if len(model.calls) == 3:
                tokenizer.response = "invalid"
            return generate(**kwargs)

        model.generate = last_fails
    result = evaluate(language_setup)
    assert result["valid"], result["issues"]
    assert result["status"] == "completed" and result["unattempted"] == 0
    assert result["metrics"]["policy_failures"] == (4 if context else 1)
    assert result["metrics"]["policy_attempts"] == 4
    assert result["macro"]["complete"] and result["macro"]["win_rate"] is None
    assert result["macro"]["mean_ending_hp"] is None
    assert result["macro"]["policy_attempt_win_rate"] == (0 if context else 0.5)
    assert len(runtime.games) == 4 and len(loaded) == len(closed) == 1
    assert catalog.audit_catalog(output)["valid"]


def test_infrastructure_stops_remaining_schedule_and_closes_parent_model(language_setup):
    _, _, runtime, _, _, _, _, loaded, closed = language_setup
    runtime.sessions[1] = [BridgeDisconnected("synthetic disconnect")]
    result = evaluate(language_setup)
    assert not result["valid"] and result["status"] == "stopped"
    assert result["metrics"]["infrastructure_failures"] == 1
    assert result["metrics"]["policy_failures"] == 0
    assert result["unattempted"] == 2 and len(runtime.games) == 2
    assert result["macro"]["policy_attempt_win_rate"] is None
    assert len(loaded) == len(closed) == 1


@pytest.mark.parametrize("target", ["original", "parent_adapter", "tensor"])
def test_mutation_stops_before_next_child_and_closes_model(language_setup, target):
    _, output, runtime, original, model, _, _, _, closed = language_setup
    terminal = runtime.sessions[0][-1]

    def mutate():
        if target == "original":
            original.write_text("{}")
        elif target == "parent_adapter":
            path = output / "frozen-policy/adapter/adapter_model.safetensors"
            path.chmod(0o644)
            path.write_bytes(b"changed")
        else:
            model.weight.data.add_(1)
        return terminal

    runtime.sessions[0][-1] = mutate
    result = evaluate(language_setup)
    assert not result["valid"] and result["orchestration_failures"] == 1
    assert len(runtime.games) == 1 and len(closed) == 1


@pytest.mark.parametrize(
    "target", ["declaration", "adapter", "tokens", "manifest_artifact", "snapshot_inventory"],
)
def test_reaudit_rejects_tampering_even_after_child_hash_inventory_refresh(language_setup, target):
    _, output, _, _, _, _, _, _, _ = language_setup
    assert evaluate(language_setup)["valid"]
    directory = output / "runs/attempt-0000"
    if target == "declaration":
        path = directory / "frozen-language/declaration.json"
        path.chmod(0o644)
        path.write_text("{}")
    elif target == "adapter":
        path = directory / "frozen-language/adapter/adapter_model.safetensors"
        path.chmod(0o644)
        path.write_bytes(b"changed")
    elif target == "tokens":
        path = directory / "episode-0000/trace.jsonl"
        events = [json.loads(line) for line in path.read_text().splitlines()]
        next(event["behavior"] for event in events if event["kind"] == "decision")[
            "prompt_tokens"
        ] += 1
        path.write_text("".join(json.dumps(event) + "\n" for event in events))
        assert audit_run(directory)["valid"]  # Core audit cannot reproduce tokenizer counts.
    elif target == "manifest_artifact":
        path = directory / "manifest.json"
        value = json.loads(path.read_bytes())
        value["config"]["policy_artifact"]["model_sha256"] = "b" * 64
        path.write_text(json.dumps(value))
    else:
        path = directory / "evaluation.json"
        value = json.loads(path.read_bytes())
        value["snapshot_files"] = {}
        path.write_text(json.dumps(value))
    manifest_path = output / "catalog-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["children"][0]["files"] = catalog._files(directory)
    manifest_path.write_text(json.dumps(manifest))
    result = catalog.audit_catalog(output)
    assert not result["valid"] and result["issues"]
    assert result["metrics"]["invalid_evidence"] == 1


def test_corrupt_policy_failure_is_invalidated_instead_of_kept_as_scored_failure(language_setup):
    _, output, _, _, _, tokenizer, _, _, _ = language_setup
    tokenizer.response = "invalid"
    assert evaluate(language_setup)["valid"]
    path = output / "runs/attempt-0000/frozen-language/declaration.json"
    path.chmod(0o644)
    path.write_text("{}")
    manifest_path = output / "catalog-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["children"][0]["files"] = catalog._files(path.parents[1])
    manifest_path.write_text(json.dumps(manifest))
    result = catalog.audit_catalog(output)
    assert not result["valid"] and result["metrics"]["invalid_evidence"] == 1
    assert result["metrics"]["policy_failures"] == 3


def test_base_only_catalog_and_saved_audit_do_not_load_another_model(language_setup, monkeypatch):
    path, output, _, artifact, model, tokenizer, _, _, closed = language_setup
    value = json.loads(artifact.read_bytes())
    value["adapter"] = None
    artifact.write_text(json.dumps(value))
    result = catalog.evaluate_catalog("language", path, output, language_artifact=artifact,
                                      loader=lambda _: (model, tokenizer))
    assert result["valid"] and result["policy_artifact"]["pretrained_base_only"]
    assert not (output / "frozen-policy/adapter").exists() and closed == [4]
    monkeypatch.setattr(language_policy, "LanguagePolicy", lambda *_: pytest.fail("model load"))
    monkeypatch.setattr(language_policy, "gpu_lease", lambda: pytest.fail("GPU lease"))
    assert catalog.audit_catalog(output)["valid"]


def test_interrupt_unwinds_parent_model_and_reserves_only_interrupted_child(language_setup):
    _, output, runtime, _, _, _, _, loaded, closed = language_setup
    runtime.sessions[1] = [KeyboardInterrupt()]
    with pytest.raises(KeyboardInterrupt):
        evaluate(language_setup)
    assert len(loaded) == len(closed) == 1
    assert len(runtime.games) == 2 and all(game.closed for game in runtime.games)
    result = catalog.audit_catalog(output)
    assert result["status"] == "interrupted" and result["unattempted"] == 2
    assert not result["valid"]


@pytest.mark.parametrize("target", ["original_declaration", "execution_declaration", "adapter"])
def test_parent_frozen_semantics_reject_tamper_after_inventory_refresh(language_setup, target):
    _, output, _, _, _, _, _, _, _ = language_setup
    assert evaluate(language_setup)["valid"]
    names = {"original_declaration": "source-declaration.json",
             "execution_declaration": "declaration.json",
             "adapter": "adapter/adapter_model.safetensors"}
    path = output / "frozen-policy" / names[target]
    path.chmod(0o644)
    path.write_bytes(b"{}")
    manifest_path = output / "catalog-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["policy_files"] = catalog._files(output / "frozen-policy")
    manifest_path.write_text(json.dumps(manifest))
    result = catalog.audit_catalog(output)
    assert not result["valid"] and any("Frozen policy" in issue for issue in result["issues"])


def test_language_comparison_checks_contract_but_not_adapter(language_setup, monkeypatch):
    from spire import catalog_report

    _, output, _, _, _, _, _, _, _ = language_setup
    assert evaluate(language_setup)["valid"]
    original = catalog_report._run(output)
    changed = copy.deepcopy(original)
    changed["policy_artifact"]["model_sha256"] = "b" * 64
    changed["policy_artifact"]["declaration"]["adapter"]["files"] = {"new": "b" * 64}
    values = iter([original, changed])
    monkeypatch.setattr(catalog_report, "_run", lambda _: next(values))
    assert compare_catalogs([output, output])["same_protocol"]
    changed["language_policy_contract"]["decoder"]["max_new_tokens"] = 24
    values = iter([original, changed])
    result = compare_catalogs([output, output])
    assert not result["same_protocol"]
    assert result["protocol_differences"] == ["language_policy_contract"]


def test_saved_catalog_uses_frozen_adapter_but_rechecks_external_base(language_setup):
    import shutil

    _, output, _, original, _, _, _, _, _ = language_setup
    declaration = json.loads(original.read_bytes())
    assert evaluate(language_setup)["valid"]
    original.unlink()
    shutil.rmtree(declaration["adapter"]["directory"])
    assert catalog.audit_catalog(output)["valid"]
    base = Path(declaration["base"]["directory"])
    (base / next(iter(declaration["base"]["files"]))).write_text("changed")
    result = catalog.audit_catalog(output)
    assert not result["valid"] and any("base files changed" in item for item in result["issues"])


def test_saved_audit_validates_external_base_once_for_all_children(language_setup, monkeypatch):
    _, output, _, _, _, _, _, _, _ = language_setup
    assert evaluate(language_setup)["valid"]
    validate = language_evaluation.validate_declaration
    validated = []

    def record(value):
        validated.append(value)
        return validate(value)

    monkeypatch.setattr(language_evaluation, "validate_declaration", record)
    assert catalog.audit_catalog(output)["valid"]
    assert len(validated) == 1


def test_out_of_range_tokenizer_error_is_invalid_saved_evidence(language_setup, monkeypatch):
    _, output, _, _, _, tokenizer, _, _, _ = language_setup
    assert evaluate(language_setup)["valid"]

    def invalid(*args, **kwargs):
        raise OverflowError("token exceeds decoder range")

    monkeypatch.setattr(tokenizer, "decode", invalid)
    result = catalog.audit_catalog(output)
    assert not result["valid"]
    assert all("out of range" in child["issues"][0] for child in result["children"])
