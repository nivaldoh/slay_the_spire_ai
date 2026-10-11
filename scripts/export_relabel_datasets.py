"""Export the declared heuristic-relabel Louse training and offline test datasets.

Selection rule, with no outcome or policy-quality filtering: every complete,
independently audited run under ``--runs`` with a single public start, excluding
language-policy behavior. Training uses only the pinned settled SPIREAI1 two-Louse
start; the offline test split uses every other start. Pre-settle SPIREAI1 starts are
skipped. See docs/language-relabel-experiment.md.

    uv run python scripts/export_relabel_datasets.py --runs runs \
        --train-output runs/new-train --test-output runs/new-test
"""

import argparse
import json
import sys
from pathlib import Path

from spire.demonstrations import RELABEL, DemonstrationSource, export_demonstrations
from spire.evidence import audit_run

LOUSE_PIN = "177b2fcdc80ed0e9efb7d2a01191a40df6e40d4123867d09e091fa122edc12c4"


def candidates(root: Path):
    for run in sorted(root.iterdir()):
        if not run.is_dir():
            continue
        if (run / "manifest.json").exists() and list(run.glob("episode-*")):
            yield run
        for parent in (run, *[child for child in sorted(run.iterdir()) if child.is_dir()]):
            if (parent / "runs").is_dir():
                for child in sorted((parent / "runs").iterdir()):
                    if (child / "manifest.json").exists():
                        yield child


def classify(root: Path):
    train, test, skipped = [], [], []
    for run in candidates(root):
        try:
            audited = audit_run(run)
        except Exception as error:  # noqa: BLE001 - recorded, never silently included
            skipped.append((str(run), f"audit error {type(error).__name__}"))
            continue
        manifest, episodes = audited["manifest"], audited["episodes"]
        complete = (
            audited["valid"]
            and manifest["status"] == "completed"
            and bool(episodes)
            and all(item["status"] in ("won", "lost") for item in episodes)
        )
        policy = manifest["config"]["policy"]
        starts = {item["combat_start_sha256"] for item in episodes}
        if not complete:
            skipped.append((str(run), "incomplete"))
        elif policy == "language":
            skipped.append((str(run), "language behavior"))
        elif len(starts) != 1 or None in starts:
            skipped.append((str(run), "mixed or missing start"))
        elif starts == {LOUSE_PIN}:
            train.append(run)
        elif manifest["config"]["game_seed"] == "SPIREAI1":
            skipped.append((str(run), "pre-settle SPIREAI1 start"))
        else:
            test.append(run)
    return train, test, skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--train-output", type=Path, required=True)
    parser.add_argument("--test-output", type=Path, required=True)
    args = parser.parse_args()
    train, test, skipped = classify(args.runs.resolve())
    for run, reason in skipped:
        print("skip", reason, run, file=sys.stderr)
    trained = export_demonstrations(
        args.train_output,
        [DemonstrationSource(run, "train", RELABEL, "public") for run in train],
        purpose="supervised_finetuning",
    )
    tested = export_demonstrations(
        args.test_output,
        [DemonstrationSource(run, "test", RELABEL, "public") for run in test],
        purpose="offline_evaluation",
    )
    for name, manifest in (("train", trained), ("test", tested)):
        print(
            name,
            json.dumps(
                {
                    k: manifest[k]
                    for k in (
                        "rows",
                        "unique_prompts",
                        "unique_examples",
                        "duplicate_rows",
                        "scenario_seed_families",
                        "public_start_families",
                    )
                }
            ),
        )


if __name__ == "__main__":
    main()
