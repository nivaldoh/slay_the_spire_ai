import hashlib
import json
import sys

import pytest

from gameai import sft

SYSTEM = "You play."


def attempt(text='{"a": 1}', status="completed", error=None, user="state", reasoning=None):
    value = {"user_prompt": user, "text": text, "status": status, "reasoning": reasoning,
             "usage": {"input_tokens": 10, "output_tokens": 3}}
    if error is not None:
        value["error"] = error
    return value


def row(id, *attempts, game="spire", group=1, split="development", provider="openrouter",
        error=None, **fields):
    return {"schema_version": 1, "id": id, "game": game, "group": group, "split": split,
            "policy": "llm", "provider": provider, "model": "qwen/qwen3.6-35b-a3b",
            "effort": "none", "prompt_version": "v1", "system_prompt": SYSTEM,
            "system_prompt_sha256": hashlib.sha256(SYSTEM.encode()).hexdigest(),
            "user_prompt": "state", "attempts": list(attempts), "error": error,
            "outcome": {"status": "lost", "gameplay_outcome": "lost"}, "labels": {"floor": 3},
            "provenance": {}, **fields}


def export(directory, rows):
    directory.mkdir()
    text = "".join(json.dumps(r) + "\n" for r in rows)
    (directory / "decisions.jsonl").write_text(text)
    (directory / "sources.json").write_text(json.dumps(
        {"schema_version": 1, "decisions_sha256": hashlib.sha256(text.encode()).hexdigest()}))
    return directory


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


ROWS = [
    row("s1", attempt()),
    row("s2", attempt("oops", error="not JSON"),
        attempt('{"a": 2}', user="state\n\nYour previous reply was invalid: not JSON."),
        group=2),
    row("s3", attempt(), group=2, provider="openai"),
    row("w1", attempt(), game="twwarhammer3", group="S1", split="held_out"),
    row("w2", attempt('{"orders": []}'), game="twwarhammer3", group="S2"),
    row("e1", attempt(), attempt(text="", status="failed"),
        error={"type": "APIError", "message": "HTTP 502"}),
    row("e2", attempt(status="incomplete")),
    row("e3", attempt(text="  ")),
    row("e4"),
    row("e5", attempt(user=None)),
]


def test_build_keeps_accepted_last_attempts_and_splits_whole_groups(tmp_path):
    source = export(tmp_path / "export", ROWS)

    manifest = sft.build([source], tmp_path / "data", validation_groups=["spire:2"])

    train, validation = lines(tmp_path / "data/train.jsonl"), lines(
        tmp_path / "data/validation.jsonl")
    assert train == [
        {"messages": [{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": "state"},
                      {"role": "assistant", "content": '{"a": 1}'}]},
        {"messages": [{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": "state"},
                      {"role": "assistant", "content": '{"orders": []}'}]}]
    # The target is the retry, with the exact feedback-bearing prompt that produced it.
    assert validation[0]["messages"][1:] == [
        {"role": "user", "content": "state\n\nYour previous reply was invalid: not JSON."},
        {"role": "assistant", "content": '{"a": 2}'}]
    rows = lines(tmp_path / "data/train-rows.jsonl")
    assert [r["id"] for r in rows] == ["s1", "w2"]
    assert rows[0] == {"id": "s1", "game": "spire", "group": 1, "split": "development",
                       "provider": "openrouter", "model": "qwen/qwen3.6-35b-a3b",
                       "effort": "none", "prompt_version": "v1", "attempt_index": 0,
                       "reasoning": None, "labels": {"floor": 3}, "tokens": None,
                       "outcome": {"status": "lost", "gameplay_outcome": "lost"}}
    assert lines(tmp_path / "data/validation-rows.jsonl")[0]["attempt_index"] == 1
    counts = manifest["counts"]
    assert (counts["rows"], counts["train"], counts["validation"]) == (10, 2, 1)
    assert counts["dropped"] == {"empty": 1, "error": 1, "held_out": 1, "missing_prompt": 1,
                                 "no_attempts": 1, "provider": 1, "status": 1}
    assert manifest["groups"] == {"train": ["spire:1", "twwarhammer3:S2"],
                                  "validation": ["spire:2"]}
    assert manifest["inputs"][0]["decisions_sha256"] == json.loads(
        (source / "sources.json").read_text())["decisions_sha256"]
    assert manifest["tokens"] == {"train": None, "validation": None}
    assert "owner's" in (tmp_path / "data/datacard.md").read_text()


def test_provider_and_first_attempt_filters(tmp_path):
    source = export(tmp_path / "export", ROWS)

    manifest = sft.build([source], tmp_path / "data", providers=("openai", "openrouter"),
                         first_attempt_only=True)

    assert [r["id"] for r in lines(tmp_path / "data/train-rows.jsonl")] == ["s1", "s3", "w2"]
    assert manifest["counts"]["dropped"]["retried"] == 1
    assert "provider" not in manifest["counts"]["dropped"]


def test_effort_filter_and_kept_models_in_the_data_card(tmp_path):
    source = export(tmp_path / "export", [
        row("a", attempt()), row("b", attempt(), effort="medium"),
        row("c", attempt(), provider="openai", model="gpt-5")])

    sft.main([str(source), "--output", str(tmp_path / "data"), "--effort", "none"])

    manifest = json.loads((tmp_path / "data/manifest.json").read_text())
    assert [r["id"] for r in lines(tmp_path / "data/train-rows.jsonl")] == ["a"]
    assert manifest["counts"]["dropped"] == {"effort": 1, "provider": 1}
    assert manifest["arguments"]["efforts"] == ["none"]
    card = (tmp_path / "data/datacard.md").read_text()
    assert "Models kept: qwen/qwen3.6-35b-a3b. Efforts kept: none." in card


def test_tokenizer_without_the_llm_extra_is_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "transformers", None)  # import fails
    with pytest.raises(ValueError, match="llm extra"):
        sft.build([export(tmp_path / "export", ROWS)], tmp_path / "data", tokenizer="Qwen")


def test_reasoning_content_uses_reasoning_text_never_summaries(tmp_path):
    parts = [{"type": "summary_text", "text": "Summary.", "field": "summary", "item_index": 0},
             {"type": "reasoning_text", "text": "Block ", "field": "content", "item_index": 0},
             {"type": "reasoning_text", "text": "first.", "field": "content", "item_index": 0}]
    source = export(tmp_path / "export", [
        row("r1", attempt(reasoning=parts)),
        row("r2", attempt(reasoning=parts[:1])),
        row("r3", attempt(reasoning=None))])

    manifest = sft.build([source], tmp_path / "with", reasoning=True)
    sft.build([source], tmp_path / "without")

    answers = [r["messages"][2] for r in lines(tmp_path / "with/train.jsonl")]
    assert answers[0] == {"role": "assistant", "content": '{"a": 1}',
                          "reasoning_content": "Block first."}
    assert "reasoning_content" not in answers[1] and "reasoning_content" not in answers[2]
    assert [r["reasoning"] for r in lines(tmp_path / "with/train-rows.jsonl")] == [
        "Block first.", None, None]
    assert manifest["counts"]["with_reasoning"] == 1
    assert all("reasoning_content" not in r["messages"][2]
               for r in lines(tmp_path / "without/train.jsonl"))


def test_token_limit_drops_rows_and_reports_percentiles(tmp_path):
    source = export(tmp_path / "export", [row("a", attempt("x" * 5)), row("b", attempt("x" * 50)),
                                          row("c", attempt("x" * 9), group=2)])

    manifest = sft.build([source], tmp_path / "data", tokenizer="chars", max_tokens=10,
                         validation_groups=["spire:2"],
                         counter=lambda messages: len(messages[2]["content"]))

    assert manifest["counts"]["dropped"] == {"max_tokens": 1}
    assert manifest["tokens"] == {"train": {"count": 1, "p50": 5, "p99": 5, "max": 5},
                                  "validation": {"count": 1, "p50": 9, "p99": 9, "max": 9}}
    assert lines(tmp_path / "data/validation-rows.jsonl")[0]["tokens"] == 9
    with pytest.raises(ValueError, match="needs --tokenizer"):
        sft.build([source], tmp_path / "other", max_tokens=10)


def test_output_is_deterministic_and_never_replaced(tmp_path):
    source = export(tmp_path / "export", ROWS)

    sft.build([source], tmp_path / "one", validation_groups=["spire:2"])
    sft.main([str(source), "--output", str(tmp_path / "two"), "--validation-group", "spire:2"])

    names = sorted(p.name for p in (tmp_path / "one").iterdir())
    assert names == ["datacard.md", "manifest.json", "train-rows.jsonl", "train.jsonl",
                     "validation-rows.jsonl", "validation.jsonl"]
    assert all((tmp_path / "one" / n).read_bytes() == (tmp_path / "two" / n).read_bytes()
               for n in names)
    with pytest.raises(FileExistsError):
        sft.build([source], tmp_path / "one")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["export", "one", "two"]


@pytest.mark.parametrize("rows, message", [
    ([{k: v for k, v in row("a", attempt()).items() if k != "group"}], "lacks id, game, group"),
    ([row("a", attempt(), split="test")], "unknown split"),
    ([row("a", attempt(), game="sts2")], "unknown game"),
    ([row("a", attempt()), row("a", attempt())], "Duplicate row id"),
])
def test_refuses_rows_outside_the_contract(tmp_path, rows, message):
    with pytest.raises(ValueError, match=message):
        sft.build([export(tmp_path / "export", rows)], tmp_path / "data")
    assert not (tmp_path / "data").exists()


def test_refuses_changed_exports_and_empty_validation_groups(tmp_path):
    source = export(tmp_path / "export", ROWS)
    with pytest.raises(ValueError, match="no kept rows: twwarhammer3:S1"):
        sft.build([source], tmp_path / "data", validation_groups=["twwarhammer3:S1"])
    with pytest.raises(ValueError, match="GAME:GROUP"):
        sft.build([source], tmp_path / "data", validation_groups=["S2"])
    with (source / "decisions.jsonl").open("a") as handle:
        handle.write(json.dumps(row("late", attempt())) + "\n")
    with pytest.raises(ValueError, match="decisions_sha256"):
        sft.build([source], tmp_path / "data")
    assert not (tmp_path / "data").exists()
