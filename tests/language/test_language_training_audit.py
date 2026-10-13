"""Saved SFT acceptance uses real checkpoint/export validators and audited toy engine evidence."""

import copy
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")

import test_language_training as trainer_tests  # noqa: E402

from gameai.provenance import REPO_ROOT  # noqa: E402
from spire.language import policy, training  # noqa: E402
from spire.language.demonstrations import DemonstrationSource, export_demonstrations  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "audit_language_training_script",
    REPO_ROOT / "scripts/audit_language_training.py",
)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
REAL_VERIFY = training.verify_dataset
toy = trainer_tests.toy
evidence_run = trainer_tests.evidence_run
run = trainer_tests.run


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def watchdog(output, *, reason="worker_exit", extra_seconds=0):
    job = read(output / "job.json")
    elapsed = read(output / "training.json")["elapsed_seconds"] + extra_seconds
    value = {
        "schema_version": 1,
        "stop_reason": reason,
        "exit_code": 0,
        "started_unix": job["started_unix"],
        "deadline_unix": job["deadline_unix"],
        "supervision_deadline_unix": job["deadline_unix"],
        "finalize_only": False,
        "elapsed_seconds": elapsed,
        "cleanup_overrun_seconds": max(0, elapsed - job["config"]["time_budget_seconds"]),
        "minimum_available_mib": 1000,
        "maximum_gpu_used_mib": 100,
        "polls": 1,
    }
    write(output / "watchdog-100.json", value)


@pytest.fixture
def setup(tmp_path, toy, run, monkeypatch):
    directory = tmp_path / "real-dataset"
    export_demonstrations(
        directory,
        [DemonstrationSource(run, "train", "heuristic", "public")],
        purpose="supervised_finetuning",
    )
    monkeypatch.setattr(training, "verify_dataset", REAL_VERIFY)
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()
    source = {"revision": revision, "files": audit.archived_source(revision)}
    monkeypatch.setattr(training, "_source", lambda: source)
    monkeypatch.setattr(training, "_export", trainer_tests.REAL_EXPORT)
    monkeypatch.setattr(policy, "create_declaration", trainer_tests.REAL_DECLARATION)
    monkeypatch.setattr(policy, "validate_declaration", trainer_tests.REAL_VALIDATE)
    monkeypatch.setattr(policy, "BASE_FILES", {})

    class ShortTokenizer(trainer_tests.Tokenizer):
        def apply_chat_template(self, messages, **kwargs):
            return super().apply_chat_template([{"role": "user", "content": "S0"}], **kwargs)

    monkeypatch.setattr(training, "_load_tokenizer", lambda _: ShortTokenizer())
    return {**toy.config, "dataset": str(directory)}, tmp_path / "saved-sft"


@pytest.fixture
def saved(setup):
    config, output = setup
    training.train_language(output, config)
    watchdog(output)
    return output


def rewrite_checkpoint(output, change):
    pointer = read(output / "checkpoint.json")
    previous = output / pointer["path"]
    payload = torch.load(previous, map_location="cpu", weights_only=True)
    change(payload)
    temporary = output / "checkpoints/rewrite.tmp"
    torch.save(payload, temporary)
    identity = audit.digest(temporary)
    path = temporary.with_name(f"{pointer['generation']:06d}-{identity}.pt")
    temporary.replace(path)
    previous.unlink()
    pointer.update(path=str(path.relative_to(output)), sha256=identity)
    write(output / "checkpoint.json", pointer)
    summary = read(output / "training.json")
    summary["checkpoint"] = pointer
    for name in summary.keys() & payload["state"].keys():
        summary[name] = payload["state"][name]
    write(output / "training.json", summary)


def test_audit_links_real_data_checkpoints_exports_and_does_not_mutate(saved, monkeypatch):
    before = {str(p): audit.digest(p) for p in saved.rglob("*") if p.is_file()}
    monkeypatch.setattr(training, "_load_model", lambda _: pytest.fail("Auditor loads no model"))
    monkeypatch.setattr(policy, "gpu_lease", lambda: pytest.fail("Auditor takes no GPU lease"))
    result = audit.audit_language_training(saved)
    assert result["valid"], result["errors"]
    assert all(result["checks"].values())
    assert result["updates"] == 3 and result["changed_adapter_elements"] > 0
    assert result["charged_tokens"] == result["committed_tokens"] == 192
    assert result["reservations"] == {"committed": 3, "reserved": 0, "abandoned_before_commit": 0}
    assert {str(p): audit.digest(p) for p in saved.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("damage", ["initial", "committed", "reservation"])
def test_missing_checkpoint_ancestry_is_rejected(saved, damage):
    paths = sorted((saved / "checkpoints").glob("*.pt"))
    paths[{"initial": 0, "committed": 2, "reservation": 1}[damage]].unlink()
    result = audit.audit_language_training(saved)
    assert not result["valid"]
    assert any(
        "checkpoint" in error.lower() or "reservation" in error.lower()
        for error in result["errors"]
    )


@pytest.mark.parametrize(
    "damage", ["nan", "optimizer_steps", "optimizer_shape", "foreign_occurrence", "sampler"]
)
def test_semantic_checkpoint_tampering_fails_after_rehash(saved, damage):
    def change(payload):
        if damage == "nan":
            next(iter(payload["adapter"].values())).flatten()[0] = float("nan")
            payload["state"]["adapter_sha256"] = training.tensor_hash(payload["adapter"])
        elif damage == "optimizer_steps":
            for state in payload["optimizer"]["state"].values():
                state["step"] = torch.tensor(999.0)
        elif damage == "optimizer_shape":
            for state in payload["optimizer"]["state"].values():
                state["exp_avg"] = torch.zeros(1)
                state["exp_avg_sq"] = torch.zeros(1)
        elif damage == "foreign_occurrence":
            payload["state"]["consumed"][0]["example_id"] = "invented"
            payload["state"]["reservations"][0]["occurrences"][0]["example_id"] = "invented"
        else:
            payload["state"]["sampler"]["epoch"] += 1

    rewrite_checkpoint(saved, change)
    result = audit.audit_language_training(saved)
    assert not result["valid"], result


@pytest.mark.parametrize("damage", ["tensor", "provenance", "missing"])
def test_forged_export_rejected_even_with_refreshed_hashes(saved, damage):
    from safetensors.torch import load_file, save_file

    directory = Path(read(saved / "training.json")["artifact"]["directory"])
    declaration = read(directory / "policy.json")
    if damage == "missing":
        (directory / "adapter/adapter_model.safetensors").unlink()
    elif damage == "tensor":
        path = directory / "adapter/adapter_model.safetensors"
        value = load_file(path)
        save_file({name: tensor + 0.1 for name, tensor in value.items()}, str(path))
        declaration["adapter"]["files"][path.name] = audit.digest(path)
    else:
        declaration["provenance"]["updates"] += 1
    write(directory / "policy.json", declaration)
    record = read(directory / "export.json")
    record["files"] = {
        name: audit.digest(directory / name)
        for name in record["files"]
        if (directory / name).exists()
    }
    write(directory / "export.json", record)
    summary = read(saved / "training.json")
    summary["artifact"] = {"directory": str(directory), **record}
    write(saved / "training.json", summary)
    result = audit.audit_language_training(saved)
    assert not result["valid"] and any("Export" in error for error in result["errors"])


@pytest.mark.parametrize(
    "damage",
    ["source", "dataset", "summary_count", "summary_deadline", "negative_elapsed", "late_elapsed"],
)
def test_frozen_lineage_and_summary_tampering_rejected(saved, damage):
    if damage == "source":
        job = read(saved / "job.json")
        job["source"]["files"]["src/spire/language_training.py"] = "0" * 64
        write(saved / "job.json", job)
    elif damage == "dataset":
        job = read(saved / "job.json")
        path = Path(job["config"]["dataset"]) / "train.jsonl"
        row = json.loads(path.read_text())
        row["completion"] = '{"a":1}'
        write(path, row)
        manifest_path = path.parent / "manifest.json"
        manifest = read(manifest_path)
        manifest["files"]["train.jsonl"] = audit.digest(path)
        write(manifest_path, manifest)
    else:
        summary = read(saved / "training.json")
        if damage in {"summary_count", "summary_deadline"}:
            summary["updates" if damage == "summary_count" else "deadline_unix"] += 1
        else:
            summary["elapsed_seconds"] = -1 if damage == "negative_elapsed" else 10000
        write(saved / "training.json", summary)
    assert not audit.audit_language_training(saved)["valid"]


@pytest.mark.parametrize("damage", ["missing", "deadline", "ram", "cleanup", "late_collection"])
def test_supervisor_limit_tampering_rejected(saved, damage):
    path = saved / "watchdog-100.json"
    if damage == "missing":
        path.unlink()
    else:
        value = read(path)
        if damage == "deadline":
            value["supervision_deadline_unix"] += 600
        elif damage == "ram":
            value["minimum_available_mib"] = 100
        elif damage == "cleanup":
            value["cleanup_overrun_seconds"] += 50
        else:
            value["started_unix"] = value["deadline_unix"] + 1
        write(path, value)
    assert not audit.audit_language_training(saved)["valid"]


def test_token_stopped_job_is_valid_without_maximum_updates(setup):
    config, output = setup
    training.train_language(output, {**config, "max_tokens": 64})
    watchdog(output)
    report = audit.audit_language_training(output)
    assert report["valid"], report["errors"]
    assert report["updates"] == 1 and report["stop_reason"] == "token_limit"


def test_deadline_stop_retains_pending_charge_without_claiming_update(setup, monkeypatch):
    config, output = setup
    original = training._optimizer_step

    def finish_after_deadline(*args):
        result = original(*args)
        deadline = read(output / "job.json")["deadline_unix"]
        monkeypatch.setattr(training.time, "time", lambda: deadline + 1)
        return result

    monkeypatch.setattr(training, "_optimizer_step", finish_after_deadline)
    training.train_language(output, config)
    watchdog(output, reason="deadline")
    report = audit.audit_language_training(output)
    assert report["valid"], report["errors"]
    assert report["updates"] == report["changed_adapter_elements"] == 0
    assert report["charged_tokens"] == 64 and report["committed_tokens"] == 0
    assert report["reservations"]["reserved"] == 1


def test_audit_accepts_bounded_cpu_finalization_after_expired_resume(setup, monkeypatch):
    config, output = setup
    training.train_language(output, config)
    watchdog(output)
    job = read(output / "job.json")
    started = job["deadline_unix"] + 5
    monkeypatch.setattr(training.time, "time", lambda: started)
    training.train_language(output, resume=True, finalize_only=True)
    write(
        output / "watchdog-200.json",
        {
            "schema_version": 1,
            "stop_reason": "worker_exit",
            "exit_code": 0,
            "started_unix": started,
            "deadline_unix": job["deadline_unix"],
            "supervision_deadline_unix": started + 30,
            "finalize_only": True,
            "elapsed_seconds": 0.1,
            "cleanup_overrun_seconds": 5.1,
            "minimum_available_mib": 1000,
            "maximum_gpu_used_mib": None,
            "polls": 1,
        },
    )
    report = audit.audit_language_training(output)
    assert report["valid"], report["errors"]
    assert report["deadline_unix"] == job["deadline_unix"]
    assert len(report["invocations"]) == 2 and report["invocations"][-1]["finalize_only"]


def test_interrupted_pending_then_resumed_abandoned_reservation_is_preserved(setup, monkeypatch):
    config, output = setup
    original = training._optimizer_step

    def interrupted(*args):
        original(*args)
        raise KeyboardInterrupt()

    monkeypatch.setattr(training, "_optimizer_step", interrupted)
    with pytest.raises(KeyboardInterrupt):
        training.train_language(output, config)
    watchdog(output, reason="KeyboardInterrupt")
    report = audit.audit_language_training(output)
    assert report["valid"], report["errors"]
    assert report["updates"] == 0 and report["reservations"]["reserved"] == 1
    first = read(output / "watchdog-100.json")
    started = training.time.time()
    monkeypatch.setattr(training, "_optimizer_step", original)
    training.train_language(output, resume=True)
    last = copy.deepcopy(first)
    last.update(
        started_unix=started,
        elapsed_seconds=training.time.time() - started,
        stop_reason="worker_exit",
    )
    write(output / "watchdog-200.json", last)
    report = audit.audit_language_training(output)
    assert report["valid"], report["errors"]
    assert report["reservations"]["abandoned_before_commit"] == 1
    assert report["charged_tokens"] == 256 and report["committed_tokens"] == 192
