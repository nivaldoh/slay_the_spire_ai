"""Supervised fine-tuning datasets from both games' model-decision exports.

Reads only the shared export-row contract (docs/posttraining.md), so it never imports a
game package. Each kept row becomes one chat example: the exact system prompt, the user
prompt of the request's last attempt (with any retry feedback) and that attempt's reply.

    uv run python -m gameai.sft EXPORT_DIR... --output DIR [--validation-group GAME:GROUP]

Rows are filtered in this order and counted under the first reason that drops them:
provider (default openrouter only), held_out split, no valid target, a retried target
with --first-attempt-only, and more tokens than --max-tokens. Validation holds exactly
the --validation-group groups, so a group never spans train and validation.
"""

from __future__ import annotations

import argparse
import json
import math
import tempfile
from collections import Counter
from pathlib import Path

from gameai.provenance import sha256

VERSION = 1
SPLITS = ("development", "held_out")
DEFAULT_PROVIDERS = ("openrouter",)


def target(row: dict) -> tuple[int, dict] | str:
    """The last attempt and its index when it is an accepted reply, else the drop reason."""
    attempts = row.get("attempts") or []
    if not attempts:
        return "no_attempts"
    last = attempts[-1]
    if row.get("error") is not None or last.get("error") is not None:
        return "error"
    if last.get("status") != "completed":
        return "status"
    if not isinstance(last.get("text"), str) or not last["text"].strip():
        return "empty"
    if not row.get("system_prompt") or not last.get("user_prompt"):
        return "missing_prompt"
    return len(attempts) - 1, last


def reasoning_text(attempt: dict) -> str | None:
    """Concatenated reasoning text parts; summaries are not reasoning."""
    text = "".join(part["text"] for part in attempt.get("reasoning") or []
                   if part.get("type") == "reasoning_text")
    return text or None


def chat_token_counter(name: str):
    """Tokens of the tokenizer's chat-template rendering of the full conversation."""
    from transformers import AutoTokenizer  # the llm extra

    tokenizer = AutoTokenizer.from_pretrained(name, trust_remote_code=False)

    def count(messages: list[dict]) -> int:
        text = tokenizer.apply_chat_template(messages, tokenize=False)
        return len(tokenizer(text, add_special_tokens=False)["input_ids"])
    return count


def _read_export(directory: Path) -> tuple[dict, list[dict]]:
    sources = json.loads((directory / "sources.json").read_text())
    decisions = directory / "decisions.jsonl"
    digest = sha256(decisions)
    if digest != sources.get("decisions_sha256"):
        raise ValueError(f"{decisions}: hash differs from sources.json decisions_sha256")
    rows = []
    with decisions.open() as handle:
        for line, raw in enumerate(handle, 1):
            row = json.loads(raw)
            if not (row.get("id") and row.get("game") and row.get("group") not in (None, "")
                    and row.get("split")):
                raise ValueError(f"{decisions}:{line}: row lacks id, game, group or split")
            if row["split"] not in SPLITS:
                raise ValueError(f"{decisions}:{line}: unknown split {row['split']!r}")
            rows.append(row)
    entry = {"path": str(directory), "decisions_sha256": digest,
             "schema_version": sources.get("schema_version"),
             "row_schema_versions": sorted({row.get("schema_version") for row in rows},
                                           key=str)}
    return entry, rows


def _stats(values: list[int]) -> dict:
    """Nearest-rank percentiles."""
    values, n = sorted(values), len(values)
    if not n:
        return {"count": 0, "p50": None, "p99": None, "max": None}
    return {"count": n, "p50": values[math.ceil(0.5 * n) - 1],
            "p99": values[math.ceil(0.99 * n) - 1], "max": values[-1]}


def build(exports: list[Path], output: Path, *, providers=DEFAULT_PROVIDERS,
          validation_groups=(), first_attempt_only=False, reasoning=False,
          tokenizer: str | None = None, max_tokens: int | None = None, counter=None) -> dict:
    """Write train/validation chat files, their row sidecars, manifest.json and datacard.md
    into the new directory ``output``. ``counter`` replaces the --tokenizer counter."""
    if not exports:
        raise ValueError("Select at least one export directory")
    if max_tokens is not None and tokenizer is None:
        raise ValueError("--max-tokens needs --tokenizer")
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Dataset destination already exists: {output}")
    validation = set()
    for item in validation_groups:
        game, sep, group = item.partition(":")
        if not (sep and game and group):
            raise ValueError(f"--validation-group {item!r}: use GAME:GROUP")
        validation.add((game, group))
    if tokenizer is not None and counter is None:
        counter = chat_token_counter(tokenizer)
    inputs, ids, dropped, by_source = [], set(), Counter(), Counter()
    kept = {"train": [], "validation": []}
    for directory in exports:
        entry, rows = _read_export(directory.resolve())
        inputs.append(entry)
        for row in rows:
            if row["id"] in ids:
                raise ValueError(f"Duplicate row id {row['id']} in {directory}")
            ids.add(row["id"])
            source = (row["game"], row.get("model"), row.get("effort"))
            found = target(row)
            if row.get("provider") not in providers:
                reason = "provider"
            elif row["split"] == "held_out":
                reason = "held_out"
            elif isinstance(found, str):
                reason = found
            elif first_attempt_only and found[0]:
                reason = "retried"
            else:
                index, attempt = found
                thought = reasoning_text(attempt) if reasoning else None
                answer = {"role": "assistant", "content": attempt["text"]}
                if thought:
                    answer["reasoning_content"] = thought
                messages = [{"role": "system", "content": row["system_prompt"]},
                            {"role": "user", "content": attempt["user_prompt"]}, answer]
                tokens = counter(messages) if counter else None
                reason = "max_tokens" if max_tokens is not None and tokens > max_tokens else None
            if reason:
                dropped[reason] += 1
                by_source[source + ("dropped",)] += 1
                continue
            by_source[source + ("kept",)] += 1
            split = "validation" if (row["game"], str(row["group"])) in validation else "train"
            kept[split].append(({"messages": messages}, {
                "id": row["id"], "game": row["game"], "group": row["group"],
                "split": row["split"], "provider": row["provider"], "model": row.get("model"),
                "effort": row.get("effort"), "prompt_version": row.get("prompt_version"),
                "attempt_index": index, "reasoning": thought, "outcome": row.get("outcome"),
                "labels": row.get("labels") or {}, "tokens": tokens}))
    groups = {split: sorted({f"{r['game']}:{r['group']}" for _, r in items})
              for split, items in kept.items()}
    missing = sorted(f"{g}:{n}" for g, n in validation if f"{g}:{n}" not in groups["validation"])
    if missing:
        raise ValueError(f"--validation-group has no kept rows: {', '.join(missing)}")
    sources = sorted({key[:3] for key in by_source}, key=str)
    manifest = {
        "version": VERSION, "builder_sha256": sha256(Path(__file__)), "inputs": inputs,
        "arguments": {"providers": sorted(providers), "validation_groups": sorted(
            validation_groups), "first_attempt_only": first_attempt_only,
            "reasoning": reasoning, "tokenizer": tokenizer, "max_tokens": max_tokens},
        "counts": {"rows": len(ids), "train": len(kept["train"]),
                   "validation": len(kept["validation"]),
                   "dropped": dict(sorted(dropped.items())),
                   "with_reasoning": sum(r["reasoning"] is not None
                                         for items in kept.values() for _, r in items),
                   "by_game_model": [
                       {"game": game, "model": model, "effort": effort,
                        "kept": by_source[(game, model, effort, "kept")],
                        "dropped": by_source[(game, model, effort, "dropped")]}
                       for game, model, effort in sources]},
        "groups": groups,
        "tokens": {split: _stats([r["tokens"] for _, r in items if r["tokens"] is not None])
                   if counter else None for split, items in kept.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".sft-", dir=output.parent) as temporary:
        directory = Path(temporary)
        for split, items in kept.items():
            with (directory / f"{split}.jsonl").open("w") as chat, \
                    (directory / f"{split}-rows.jsonl").open("w") as sidecar:
                for example, row in items:
                    chat.write(json.dumps(example, ensure_ascii=False) + "\n")
                    sidecar.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        (directory / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        (directory / "datacard.md").write_text(_data_card(manifest))
        directory.rename(output)
    return manifest


def _data_card(manifest: dict) -> str:
    counts, arguments = manifest["counts"], manifest["arguments"]
    return f"""# Supervised fine-tuning dataset (builder version {VERSION})

Built by `gameai.sft` from {len(manifest['inputs'])} model-decision export(s); see
`manifest.json` for input hashes, arguments, counts and token statistics.

- `train.jsonl`, `validation.jsonl`: one chat per line (system, user, assistant). The
  user message is the exact prompt of the request's last attempt, retry feedback
  included; the assistant message is that attempt's raw reply.
- `train-rows.jsonl`, `validation-rows.jsonl`: aligned line by line with the chats: row id,
  game, group, provider, model, effort, prompt version, attempt index, reasoning, outcome,
  labels and tokens. Outcomes and labels are evaluation data, never model inputs.

Kept: {counts['train']} train and {counts['validation']} validation of {counts['rows']}
rows. Dropped by reason: `{json.dumps(counts['dropped'], sort_keys=True)}`.

## Selection

- Providers kept: {', '.join(arguments['providers'])}. Rows produced by other providers'
  models are dropped by default: whether OpenAI outputs may train a model is the owner's
  open provider-terms decision. Open-weight model rows served through OpenRouter may.
- Targets are the last attempt of a request, used only when it was accepted: no attempt
  or row error, status `completed` and non-blank text. Earlier rejected attempts stay in
  the prompt history only through the retry feedback the model saw. A target is not a
  claim that the action was good: winning and losing battles and runs are both kept.
- Held-out rows (`split` held_out) never enter a dataset.
- Validation groups: {', '.join(arguments['validation_groups']) or 'none'}. A group
  (Spire seed, WH3 scenario family) lies wholly in train or in validation.
- First attempt only: {arguments['first_attempt_only']}. Reasoning: {arguments['reasoning']}
  ({counts['with_reasoning']} kept rows carry `reasoning_content`, from `reasoning_text`
  parts only; provider summaries are not reasoning). Without it, replies made with
  reasoning on are trained as direct answers.
- Tokenizer: {arguments['tokenizer']}; limit {arguments['max_tokens']}. Rows over the limit
  are dropped, never truncated.

Review the source models' terms before training or redistribution. This card is not a
license.
"""


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m gameai.sft", description=__doc__.split(
        "\n\n")[0])
    parser.add_argument("exports", nargs="+", type=Path, metavar="EXPORT_DIR")
    parser.add_argument("--output", type=Path, required=True, help="new dataset directory")
    parser.add_argument("--provider", action="append",
                        help="keep rows from this provider; repeatable (default openrouter)")
    parser.add_argument("--validation-group", action="append", default=[],
                        metavar="GAME:GROUP", help="put this group in validation; repeatable")
    parser.add_argument("--first-attempt-only", action="store_true",
                        help="keep only targets accepted on the first attempt")
    parser.add_argument("--reasoning", action="store_true",
                        help="add the target's reasoning text as reasoning_content")
    parser.add_argument("--tokenizer", metavar="NAME_OR_PATH",
                        help="count chat-template tokens (needs the llm extra)")
    parser.add_argument("--max-tokens", type=int, help="drop rows over this many tokens")
    args = parser.parse_args(argv)
    try:
        manifest = build(args.exports, args.output,
                         providers=tuple(args.provider or DEFAULT_PROVIDERS),
                         validation_groups=tuple(args.validation_group),
                         first_attempt_only=args.first_attempt_only, reasoning=args.reasoning,
                         tokenizer=args.tokenizer, max_tokens=args.max_tokens)
    except (ValueError, OSError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(manifest["counts"], indent=2, sort_keys=True))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
