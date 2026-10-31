"""Frozen language policy contracts using CPU tensors and an injected tiny model."""

import copy
import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest

torch = pytest.importorskip("torch")

from combat_support import combat_message  # noqa: E402
from language_policy_support import (  # noqa: E402
    TinyModel,
    TinyTokenizer,
    adapter_declaration,
    declaration,
)

from spire.language import policy as language  # noqa: E402
from spire.language.demonstrations import render_prompt  # noqa: E402
from spire.protocol import PolicyFailure, decision_from_message  # noqa: E402

__all__ = ["adapter_declaration", "declaration"]


@pytest.fixture
def decision():
    return decision_from_message(combat_message(), session_id="private-session", sequence=7)


def test_frozen_public_choice_preserves_identity_and_exact_greedy_decoding(declaration, decision):
    model, tokenizer = TinyModel(), TinyTokenizer()
    with language.LanguagePolicy(declaration, loader=lambda _: (model, tokenizer)) as policy:
        action = policy.choose(decision)
        assert action is decision.candidates[0]
        metadata = policy.choice_metadata(decision.id)
        assert metadata["completion"] == '{"a": 0}'
        assert metadata["raw_completion"] == '{"a": 0}<eos>'
        assert metadata["prompt_tokens"] == 13 and metadata["completion_tokens"] == 3
        assert (
            metadata["prompt_sha256"]
            == hashlib.sha256(render_prompt(decision).encode()).hexdigest()
        )
        assert tokenizer.messages == [{"role": "user", "content": render_prompt(decision)}]
        assert "private-session" not in str(tokenizer.messages)
        generation = model.calls[0]
        assert generation["max_new_tokens"] == 12 and generation["do_sample"] is False
        assert generation["num_beams"] == generation["num_return_sequences"] == 1
        assert generation["pad_token_id"] == tokenizer.eos_token_id
        assert all(not parameter.requires_grad for parameter in model.parameters())
        policy.verify_frozen()
        with pytest.raises(ValueError, match="No language completion"):
            policy.choice_metadata("stale")
    assert policy.model is None


@pytest.mark.parametrize(
    "response",
    [
        "end",
        '{"a":true}',
        '{"a":99}',
        '{"a":0,"a":0}',
        '{"a":0} explanation',
        '{"command":"play 1 0"}',
    ],
)
def test_invalid_output_has_no_retry_and_preserves_failure(declaration, decision, response):
    model, tokenizer = TinyModel(), TinyTokenizer(response)
    with language.LanguagePolicy(declaration, loader=lambda _: (model, tokenizer)) as policy:
        with pytest.raises(PolicyFailure) as caught:
            policy.choose(decision)
        failure = caught.value.failure
        assert failure["kind"] == "invalid_completion"
        assert failure["completion"] == response and failure["completion_tokens"] == 3
        assert failure["prompt_tokens"] == 13 and failure["max_prompt_tokens"] == 2048
        assert failure["inference_seconds"] >= 0
        assert len(model.calls) == 1


@pytest.mark.parametrize("tokens,accepted", [(2048, True), (2049, False)])
def test_context_cap_is_exact_and_never_truncates(declaration, decision, tokens, accepted):
    model, tokenizer = TinyModel(), TinyTokenizer(tokens=tokens)
    with language.LanguagePolicy(declaration, loader=lambda _: (model, tokenizer)) as policy:
        if accepted:
            policy.choose(decision)
            assert model.calls[0]["input_ids"].shape[1] == 2048
        else:
            with pytest.raises(PolicyFailure) as caught:
                policy.choose(decision)
            assert caught.value.failure["kind"] == "context_limit"
            assert caught.value.failure["completion"] is None
            assert caught.value.failure["completion_tokens"] == 0
            assert model.calls == []


@pytest.mark.parametrize(
    "field",
    ["decoder", "parser_version", "prompt_format", "max_prompt_tokens", "schema_version", "extra"],
)
def test_changed_contract_rejected_before_loader(declaration, field):
    declaration[field] = True if field == "schema_version" else "changed"
    loader = Mock()
    with pytest.raises(ValueError):
        language.LanguagePolicy(declaration, loader=loader)
    loader.assert_not_called()


@pytest.mark.parametrize("target", ["base", "adapter"])
def test_artifact_file_mutation_rejected_before_load(adapter_declaration, target):
    record = adapter_declaration[target]
    (Path(record["directory"]) / next(iter(record["files"]))).write_bytes(b"changed")
    loader = Mock()
    with pytest.raises(ValueError, match="files changed"):
        language.LanguagePolicy(adapter_declaration, loader=loader)
    loader.assert_not_called()


@pytest.mark.parametrize("target", ["parameter", "buffer", "training", "requires_grad"])
def test_frozen_verification_detects_in_memory_mutation(declaration, target):
    model = TinyModel()
    with language.LanguagePolicy(declaration, loader=lambda _: (model, TinyTokenizer())) as policy:
        if target == "parameter":
            model.weight.data.add_(1)  # No version-counter assumption: exact contents must differ.
        elif target == "buffer":
            model.buffer.add_(1)
        elif target == "training":
            model.train()
        else:
            model.weight.requires_grad_(True)
        with pytest.raises(ValueError, match="frozen|Frozen"):
            policy.verify_frozen()


def test_external_declaration_mutation_does_not_mutate_loaded_identity(declaration):
    original = copy.deepcopy(declaration)
    with language.LanguagePolicy(
        declaration, loader=lambda _: (TinyModel(), TinyTokenizer())
    ) as policy:
        declaration["decoder"]["do_sample"] = True
        assert policy.declaration == original
        policy.verify_frozen()


def test_gpu_lease_is_exclusive_released_on_exception_and_load_failure(
    tmp_path, monkeypatch, declaration
):
    monkeypatch.setattr(language, "GPU_LOCK_PATH", tmp_path / "gpu.lock")
    with pytest.raises(ValueError):
        with language.gpu_lease():
            with pytest.raises(RuntimeError, match="owns the GPU"):
                with language.gpu_lease():
                    pytest.fail("second lease acquired")
            raise ValueError("test unwind")
    monkeypatch.setattr(language, "load_local_model", Mock(side_effect=RuntimeError("load failed")))
    with pytest.raises(RuntimeError, match="load failed"):
        language.LanguagePolicy(declaration)
    with language.gpu_lease():
        pass


def test_default_loader_claims_the_lease_before_loading_and_releases_it_after_close(
    tmp_path, monkeypatch, declaration, decision
):
    # One GPU job at a time (AGENTS.md); this real lock is private to the test.
    monkeypatch.setattr(language, "GPU_LOCK_PATH", tmp_path / "gpu.lock")
    loaded = []

    def load(_declaration):
        with pytest.raises(RuntimeError, match="owns the GPU"):
            with language.gpu_lease():
                pass
        loaded.append(True)
        return TinyModel(), TinyTokenizer()

    monkeypatch.setattr(language, "load_local_model", load)

    with language.gpu_lease():
        with pytest.raises(RuntimeError, match="owns the GPU"):
            with language.LanguagePolicy(declaration):
                pass
        assert loaded == []

    with language.LanguagePolicy(declaration) as policy:
        assert policy.choose(decision) is decision.candidates[0]
        with pytest.raises(RuntimeError, match="owns the GPU"):
            with language.gpu_lease():
                pass
    assert loaded == [True]
    with language.gpu_lease():
        pass


def test_injected_cpu_loader_works_while_the_gpu_lease_is_held(
    tmp_path, monkeypatch, declaration, decision
):
    monkeypatch.setattr(language, "GPU_LOCK_PATH", tmp_path / "gpu.lock")

    with language.gpu_lease():
        with language.LanguagePolicy(
            declaration, loader=lambda _: (TinyModel(), TinyTokenizer())
        ) as policy:
            assert policy.choose(decision) is decision.candidates[0]


def test_decoder_preserves_embedded_special_tokens_and_removes_only_final_eos():
    class Tokenizer:
        def decode(self, ids, *, skip_special_tokens):
            assert skip_special_tokens is False
            return "".join({1: '{"a":0}', 2: "<think>", 151645: "<eos>"}[i] for i in ids)

    assert language.decode_completion(Tokenizer(), [1, 151645]) == ('{"a":0}', '{"a":0}<eos>')
    assert language.decode_completion(Tokenizer(), [2, 1, 151645])[0] == '<think>{"a":0}'
    assert language.decode_completion(Tokenizer(), [1, 151645, 151645])[0] == '{"a":0}<eos>'


@pytest.mark.parametrize("change", ["missing", "extra", "value", "shape", "lossy_dtype", "nan"])
def test_adapter_tensor_verification_rejects_incomplete_or_changed_restore(change):
    saved = {"lora_A": torch.tensor([1.0, 2.0]), "lora_B": torch.tensor([3.0, 4.0])}
    restored = {key: value.clone() for key, value in saved.items()}
    if change == "missing":
        del restored["lora_B"]
    elif change == "extra":
        restored["unexpected"] = torch.zeros(1)
    elif change == "value":
        restored["lora_A"][0] += 1
    elif change == "shape":
        restored["lora_A"] = restored["lora_A"].reshape(1, 2)
    elif change == "lossy_dtype":
        restored["lora_A"] = restored["lora_A"].to(torch.bfloat16)
    else:
        saved["lora_A"][0] = restored["lora_A"][0] = float("nan")
    with pytest.raises(ValueError, match="adapter tensor"):
        language._verify_adapter_tensors(restored, saved)


@pytest.mark.parametrize("dtype", [torch.float32, torch.float16, torch.bfloat16])
def test_adapter_tensor_verification_accepts_exact_values_and_lossless_peft_promotion(dtype):
    saved = {"lora_A": torch.tensor([1.25, -0.5], dtype=dtype)}
    language._verify_adapter_tensors({"lora_A": saved["lora_A"].clone()}, saved)
    language._verify_adapter_tensors({"lora_A": saved["lora_A"].float()}, saved)


@pytest.mark.parametrize("malformed", [False, True])
def test_actual_cpu_peft_reload_rejects_missing_serialized_tensor(tmp_path, monkeypatch, malformed):
    peft = pytest.importorskip("peft")
    transformers = pytest.importorskip("transformers")
    safetensors = pytest.importorskip("safetensors.torch")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    config = transformers.Qwen3Config(
        vocab_size=32,
        hidden_size=16,
        intermediate_size=32,
        num_hidden_layers=1,
        num_attention_heads=2,
        num_key_value_heads=1,
        head_dim=8,
    )
    model = peft.get_peft_model(
        transformers.Qwen3ForCausalLM(config),
        peft.LoraConfig(r=2, lora_alpha=4, target_modules=["q_proj"], task_type="CAUSAL_LM"),
    )
    directory = tmp_path / "adapter"
    model.save_pretrained(directory)
    path = directory / "adapter_model.safetensors"
    saved = safetensors.load_file(path)
    assert len(saved) == 2 and next(model.parameters()).device.type == "cpu"
    if malformed:
        del saved[next(iter(saved))]
        safetensors.save_file(saved, path)
        with pytest.warns(UserWarning, match="missing adapter keys"):
            with pytest.raises(ValueError, match="tensor keys differ"):
                language._load_adapter(transformers.Qwen3ForCausalLM(config), str(directory))
    else:
        restored = language._load_adapter(transformers.Qwen3ForCausalLM(config), str(directory))
        language._verify_adapter_tensors(peft.get_peft_model_state_dict(restored), saved)
        assert all(not parameter.requires_grad for parameter in restored.parameters())


def test_candidate_completions_are_canonical_choice_tokens_plus_eos():
    class CharacterTokenizer:
        eos_token_id = 99

        def __call__(self, text, *, add_special_tokens):
            assert add_special_tokens is False
            return {"input_ids": [ord(character) for character in text]}

    tokens = language.candidate_completions(CharacterTokenizer(), 11)
    assert tokens[0] == [*map(ord, '{"a":0}'), 99]
    assert tokens[10] == [*map(ord, '{"a":10}'), 99]
    with pytest.raises(ValueError, match="at least one"):
        language.candidate_completions(CharacterTokenizer(), 0)


def test_batched_candidate_scores_equal_unpadded_per_completion_sums():
    transformers = pytest.importorskip("transformers")
    torch.manual_seed(0)
    config = transformers.Qwen3Config(
        vocab_size=32,
        hidden_size=16,
        intermediate_size=32,
        num_hidden_layers=2,
        num_attention_heads=2,
        num_key_value_heads=1,
        head_dim=8,
    )
    model = transformers.Qwen3ForCausalLM(config).eval()
    prompt = [3, 5, 7, 11, 13]
    completions = [[1, 2, 31], [4, 31], [6, 8, 9, 31]]
    with torch.no_grad():
        batched = language.candidate_log_probs(model, prompt, completions)
        for index, tokens in enumerate(completions):
            logits = model(input_ids=torch.tensor([prompt + tokens])).logits[0].float()
            expected = sum(
                torch.log_softmax(logits[len(prompt) - 1 + offset], dim=-1)[token]
                for offset, token in enumerate(tokens)
            )
            assert torch.allclose(batched[index], expected, atol=1e-5)
    scores = language.candidate_log_probs(model, prompt, completions)
    torch.log_softmax(scores, dim=0)[0].backward()
    assert any(parameter.grad is not None for parameter in model.parameters())
