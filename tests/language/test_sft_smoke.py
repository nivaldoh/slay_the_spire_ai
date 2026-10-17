"""scripts/sft_smoke.py skips rows it cannot train exactly instead of aborting the run."""

import importlib.util
import json
from collections import Counter

import pytest

from gameai.provenance import REPO_ROOT

SPEC = importlib.util.spec_from_file_location("sft_smoke_script",
                                              REPO_ROOT / "scripts/sft_smoke.py")
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


class Tokenizer:
    """Qwen3's rendering with thinking off, one token per character. Like the real template,
    it strips a final reply's leading newlines."""

    chat_template = "{%- if enable_thinking is defined %}"
    eos_token = "<|im_end|>"

    def apply_chat_template(self, messages, tokenize, add_generation_prompt=False,
                            enable_thinking=True):
        text = "".join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n"
                       for m in messages[:2]) + "<|im_start|>assistant\n<think>\n\n</think>\n\n"
        if add_generation_prompt:
            return text
        return text + messages[2]["content"].lstrip("\n") + "<|im_end|>\n"

    def __call__(self, text, add_special_tokens):
        return {"input_ids": [ord(c) for c in text]}


def chat(reply):
    return {"messages": [{"role": "system", "content": "S"}, {"role": "user", "content": "U"},
                         {"role": "assistant", "content": reply}]}


def test_usable_skips_template_mismatches_and_long_rows():
    pairs = [(chat('{"a": 1}'), "ok"), (chat('\n{"a": 1}'), "newline"),
             (chat("x" * 200), "long")]
    skipped = Counter()

    kept = smoke.usable(Tokenizer(), pairs, 150, skipped)

    assert skipped == {"template": 1, "max_tokens": 1}
    [(example, row_id, prompt, target)] = kept
    assert row_id == "ok"
    assert "".join(map(chr, prompt)).endswith("assistant\n<think>\n\n</think>\n\n")
    assert "".join(map(chr, target)) == '{"a": 1}<|im_end|>'


def test_read_split_requires_aligned_sidecar(tmp_path):
    (tmp_path / "train.jsonl").write_text(json.dumps(chat("{}")) + "\n")
    (tmp_path / "train-rows.jsonl").write_text(json.dumps({"id": "r1"}) + "\n")

    assert smoke.read_split(tmp_path, "train") == [(chat("{}"), "r1")]
    assert smoke.read_split(tmp_path, "validation") == []
    (tmp_path / "train-rows.jsonl").write_text("")
    with pytest.raises(ValueError):
        smoke.read_split(tmp_path, "train")


def test_action_match_ignores_only_top_level_free_text():
    reference = '{"choice": 1, "reason": "safer", "notes": null}'
    assert smoke.score('{"notes": "keep", "choice": 1, "reason": "other"}', reference) == {
        "json_valid": True, "exact_match": False, "action_match": True}
    assert smoke.score('{"choice":1,"reason":"safer","notes":null}', reference) == {
        "json_valid": True, "exact_match": True, "action_match": True}
    assert smoke.score('{"choice": 0, "reason": "safer", "notes": null}', reference) == {
        "json_valid": True, "exact_match": False, "action_match": False}
    assert smoke.score("choice 1", reference) == {
        "json_valid": False, "exact_match": False, "action_match": False}
    # Free text inside an action (a WH3 order) is part of the action.
    orders = '{"orders": [{"unit": "f1", "reason": "%s"}], "reason": "r", "notes": null}'
    assert not smoke.score(orders % "a", orders % "b")["action_match"]


def test_token_loss_weights_rows_by_target_tokens():
    rows = smoke.usable(Tokenizer(), [(chat('{"a": 1}'), "a"), (chat("{}"), "b")], 150,
                        Counter())
    assert [len(target) for *_, target in rows] == [18, 12]

    # Each row's mean loss is its length here: (18 * 18 + 12 * 12) / 30 tokens.
    assert smoke.token_loss(rows, lambda prompt, target: len(target)) == pytest.approx(15.6)
    assert smoke.token_loss([], lambda prompt, target: 1.0) is None
