"""Offline greedy agreement of a frozen language policy with heuristic labels.

Reads an exported demonstration dataset, rebuilds every public Decision from its
audited origin trace, and asks the frozen policy for one greedy choice per unique
prompt. It also scores every canonical legal completion to report the normalized
candidate distribution: its argmax, the teacher label's probability and entropy.
No game is launched and no weights change. Agreement with a teacher label is a
diagnostic of imitation, not a gameplay score.

    PYTHONPATH=src /path/to/cuda-env/bin/python scripts/offline_agreement.py \
        --declaration policy.json --dataset runs/dataset --split test --output report.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path

from spire.demonstrations import render_prompt
from spire.evidence import audit_run
from spire.language_policy import LanguagePolicy
from spire.protocol import Action, Decision, PolicyFailure


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


LABEL_ROLES = {"heuristic", "heuristic_relabel"}


def _origins(dataset: Path) -> list[dict]:
    return [json.loads(line) for line in (dataset / "origins.jsonl").read_text().splitlines()]


def _manifest(dataset: Path) -> dict:
    manifest = json.loads((dataset / "manifest.json").read_text())
    for name, digest in manifest["files"].items():
        if _sha((dataset / name).read_bytes()) != digest:
            raise ValueError(f"Dataset file changed: {name}")
    return manifest


def check_disjoint(evaluated: Path, training: Path) -> dict:
    """The two exports were built separately, so recheck their split boundaries here."""
    _manifest(training)
    keys = ("prompt_sha256", "public_start_sha256", "scenario_seed_family_sha256")
    trained = {key: {item[key] for item in _origins(training)} for key in keys}
    overlap = {key: len({item[key] for item in _origins(evaluated)} & trained[key]) for key in keys}
    if any(overlap.values()):
        raise ValueError(f"Evaluation data overlaps training data: {overlap}")
    return {"training_manifest_sha256": _sha((training / "manifest.json").read_bytes()), **overlap}


def load_examples(dataset: Path, split: str) -> list[dict]:
    """One entry per unique prompt and start, with its rebuilt Decision and row count.

    Only deterministic public-heuristic labels are supported, so every duplicate
    prompt must carry the same label.
    """
    manifest = _manifest(dataset)
    if not {source["source_role"] for source in manifest["sources"]} <= LABEL_ROLES:
        raise ValueError("Agreement needs deterministic public-heuristic labels")
    rows = [json.loads(line) for line in (dataset / f"{split}.jsonl").read_text().splitlines()]
    origins = [item for item in _origins(dataset) if item["split"] == split]
    runs = {source["run_sha256"]: Path(source["run"]) for source in manifest["sources"]}
    audits, unique = {}, {}
    for row, origin in zip(rows, origins, strict=True):
        key = (origin["prompt_sha256"], origin["public_start_sha256"])
        label = json.loads(row["completion"])["a"]
        if key in unique:
            if unique[key]["label"] != label:
                raise ValueError("Duplicate public prompt has conflicting labels")
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
            "label": label,
            "start": origin["public_start_sha256"],
            "rows": 1,
        }
    return list(unique.values())


FIELDS = ("prompts", "rows", "agree", "agree_rows", "failures", "argmax_agree")
SUMS = ("label_probability", "entropy", "max_probability")


def evaluate(declaration: Path, dataset: Path, split: str, training: Path | None = None) -> dict:
    disjoint = None if training is None else check_disjoint(dataset, training)
    examples = load_examples(dataset, split)
    by_start = defaultdict(Counter)
    candidate = defaultdict(lambda: dict.fromkeys(SUMS, 0.0))
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
            probabilities = [math.exp(value) for value in policy.candidate_log_probs(decision)]
            counts["argmax_agree"] += probabilities.index(max(probabilities)) == label
            sums = candidate[example["start"]]
            sums["label_probability"] += probabilities[label]
            sums["entropy"] -= sum(p * math.log(p) for p in probabilities if p > 0)
            sums["max_probability"] += max(probabilities)
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
    totals = {key: sum(item[key] for item in candidate.values()) for key in SUMS}
    return {
        "schema_version": 1,
        "scope": "Offline greedy agreement with heuristic labels; not a gameplay score",
        "declaration": str(declaration.resolve()),
        "declaration_sha256": _sha(declaration.read_bytes()),
        "model_sha256": model_sha256,
        "dataset": str(dataset.resolve()),
        "dataset_manifest_sha256": _sha((dataset / "manifest.json").read_bytes()),
        "split": split,
        "disjoint_from_training": disjoint,
        "prompts": total["prompts"],
        "rows": total["rows"],
        "prompt_agreement": total["agree"] / total["prompts"],
        "row_agreement": total["agree_rows"] / total["rows"],
        "policy_failures": dict(failures),
        "candidate_argmax_agreement": total["argmax_agree"] / total["prompts"],
        **{f"mean_{key}": totals[key] / total["prompts"] for key in SUMS},
        "by_public_start": {
            start: {
                **{field: counts[field] for field in FIELDS},
                "prompt_agreement": counts["agree"] / counts["prompts"],
                **{f"mean_{key}": candidate[start][key] / counts["prompts"] for key in SUMS},
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
    parser.add_argument(
        "--training-dataset", type=Path, help="Reject prompt, start or seed overlap with it"
    )
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists")
    training = args.training_dataset.resolve() if args.training_dataset else None
    report = evaluate(args.declaration, args.dataset.resolve(), args.split, training)
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
                    "candidate_argmax_agreement",
                    "mean_label_probability",
                    "mean_entropy",
                    "seconds",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
