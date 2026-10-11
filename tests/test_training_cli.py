import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from spire.__main__ import main


def test_new_training_requires_explicit_resource_limits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["spire", "train", "--output", "runs/example"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2


def test_resume_cannot_silently_extend_training_budget(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "spire",
            "train",
            "--resume",
            "--output",
            "runs/example",
            "--time-budget",
            "9999",
        ],
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2


def test_resume_uses_saved_configuration(monkeypatch):
    train = Mock(return_value={"status": "completed"})
    monkeypatch.setitem(sys.modules, "spire.training", SimpleNamespace(train=train))
    monkeypatch.setattr(sys, "argv", ["spire", "train", "--resume", "--output", "runs/example"])
    assert main() == 0
    assert train.call_args.args[1] is None
    assert train.call_args.kwargs == {"resume": True}


def test_new_training_passes_explicit_learning_rate(monkeypatch):
    train = Mock(return_value={"status": "completed"})
    monkeypatch.setitem(sys.modules, "spire.training", SimpleNamespace(train=train))
    monkeypatch.setattr(sys, "argv", [
        "spire", "train", "--output", "runs/example", "--suite", "suite.json",
        "--episodes", "2", "--batch-steps", "2", "--updates", "1",
        "--time-budget", "60", "--learning-rate", "0.003",
    ])
    assert main() == 0
    assert train.call_args.args[1]["learning_rate"] == 0.003


def test_resume_rejects_learning_rate_override(monkeypatch):
    monkeypatch.setattr(sys, "argv", [
        "spire", "train", "--resume", "--output", "runs/example", "--learning-rate", "0.003",
    ])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2


def test_evaluation_passes_checkpoint_without_importing_training(monkeypatch, tmp_path):
    suite = tmp_path / "suite.json"
    suite.write_text('{"schema_version": 1}')
    evaluate = Mock(return_value={"valid": True, "audit": {"metrics": {}}})
    monkeypatch.setitem(sys.modules, "spire.evaluation", SimpleNamespace(evaluate=evaluate))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "spire",
            "evaluate",
            "--checkpoint",
            "artifact.pt",
            "--suite",
            str(suite),
            "--output",
            "runs/example",
        ],
    )
    assert main() == 0
    assert evaluate.call_args.args[0] == "neural"
    assert str(evaluate.call_args.kwargs["checkpoint"]) == "artifact.pt"
