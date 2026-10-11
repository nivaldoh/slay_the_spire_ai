"""Offline greedy agreement of a frozen language policy with heuristic labels.

Reads an exported demonstration dataset, rebuilds every public Decision from its
audited origin trace, and asks the frozen policy for one greedy choice per unique
prompt. No game is launched and no weights change. Agreement with a teacher label
is a diagnostic of imitation, not a gameplay score.

    PYTHONPATH=src /path/to/cuda-env/bin/python scripts/offline_agreement.py \
        --declaration policy.json --dataset runs/dataset --split test --output report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from spire.demonstrations import render_prompt
from spire.evidence import audit_run
from spire.language_policy import LanguagePolicy
from spire.protocol import Action, Decision, PolicyFailure


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_examples(dataset: Path, split: str) -> list[dict]:
    """One entry per unique prompt, with its rebuilt Decision and row multiplicity."""
    manifest = json.loads((dataset / "manifest.json").read_text())
    for name, digest in manifest["files"].items():
        if _sha((dataset / name).read_bytes()) != digest:
            raise ValueError(f"Dataset file changed: {name}")
    rows = [json.loads(line) for line in (dataset / f"{split}.jsonl").read_text().splitlines()]
    origins = [
        json.loads(line)
        for line in (dataset / "origins.jsonl").read_text().splitlines()
        if json.loads(line)["split"] == split
    ]
    runs = {source["run_sha256"]: Path(source["run"]) for source in manifest["sources"]}
    audits, unique = {}, {}
    for row, origin in zip(rows, origins, strict=True):
        key = origin["prompt_sha256"]
        if key in unique:
            unique[key]["rows"] += 1
            continue
        run = runs[origin["origin_run_sha256"]]
        if run not in audits:
            audits[run] = audit_run(run)
        episode = next(
            item for item in audits[run]["episodes"] if item["session_id"] == origin["session_id"]
        )
        transition = next(
            item
            for item in episode["transitions"]
            if item["transition_id"] == origin["transition_id"]
        )
        decision = Decision(
            transition["action"]["decision_id"],
            transition["observation"],
            tuple(Action(**item) for item in transition["candidates"]),
        )
        if render_prompt(decision) != row["prompt"]:
            raise ValueError("Rebuilt public prompt differs from the exported row")
        unique[key] = {
            "decision": decision,
            "label": json.loads(row["completion"])["a"],
            "start": origin["public_start_sha256"],
            "rows": 1,
        }
    return list(unique.values())


def evaluate(declaration: Path, dataset: Path, split: str) -> dict:
    examples = load_examples(dataset, split)
    by_start = defaultdict(Counter)
    confusion = Counter()
    failures = Counter()
    started = time.monotonic()
    with LanguagePolicy.from_declaration(declaration) as policy:
        for example in examples:
            decision, label = example["decision"], example["label"]
            counts = by_start[example["start"]]
            counts["prompts"] += 1
            counts["rows"] += example["rows"]
            try:
                choice = decision.candidates.index(policy.choose(decision))
            except PolicyFailure as error:
                failures[error.failure["kind"]] += 1
                counts["failures"] += 1
                choice = None
            if choice == label:
                counts["agree"] += 1
                counts["agree_rows"] += example["rows"]
            kind = decision.candidates[label]
            confusion[
                (
                    kind.card_id or kind.kind,
                    "failure"
                    if choice is None
                    else (decision.candidates[choice].card_id or decision.candidates[choice].kind),
                )
            ] += 1
        policy.verify_frozen()
        model_sha256 = policy.model_sha256
    total = Counter()
    for counts in by_start.values():
        total.update(counts)
    return {
        "schema_version": 1,
        "scope": "Offline greedy agreement with heuristic labels; not a gameplay score",
        "declaration": str(declaration.resolve()),
        "declaration_sha256": _sha(declaration.read_bytes()),
        "model_sha256": model_sha256,
        "dataset": str(dataset.resolve()),
        "dataset_manifest_sha256": _sha((dataset / "manifest.json").read_bytes()),
        "split": split,
        "prompts": total["prompts"],
        "rows": total["rows"],
        "prompt_agreement": total["agree"] / total["prompts"],
        "row_agreement": total["agree_rows"] / total["rows"],
        "policy_failures": dict(failures),
        "by_public_start": {
            start: {
                **dict(counts),
                "prompt_agreement": counts["agree"] / counts["prompts"],
            }
            for start, counts in sorted(by_start.items())
        },
        "label_vs_choice": [
            {"label": label, "choice": choice, "prompts": count}
            for (label, choice), count in sorted(confusion.items())
        ],
        "seconds": time.monotonic() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", choices=["train", "validation", "test"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists")
    report = evaluate(args.declaration, args.dataset.resolve(), args.split)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "prompts",
                    "prompt_agreement",
                    "row_agreement",
                    "policy_failures",
                    "seconds",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
