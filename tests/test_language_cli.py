import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from spire.__main__ import main


@pytest.mark.parametrize("valid", [True, False])
def test_language_artifact_uses_separate_frozen_evaluator(monkeypatch, tmp_path, capsys, valid):
    suite = tmp_path / "suite.json"
    suite.write_text('{"schema_version": 1}')
    artifact = tmp_path / "language-policy.json"
    output = tmp_path / "evaluation"
    evaluate = Mock(return_value={
        "valid": valid, "audit": {"metrics": {"policy_failures": 2, "policy_attempts": 8}}
    })
    monkeypatch.setitem(sys.modules, "spire.language_evaluation",
                        SimpleNamespace(evaluate_language=evaluate))
    monkeypatch.setattr(sys, "argv", [
        "spire", "evaluate", "--language-artifact", str(artifact),
        "--suite", str(suite), "--output", str(output),
    ])
    assert main() == (0 if valid else 1)
    evaluate.assert_called_once_with(artifact, suite, output)
    printed = capsys.readouterr().out
    assert '"policy_failures": 2' in printed
    assert str(output / "evaluation.json") in printed


@pytest.mark.parametrize("valid", [True, False])
def test_language_catalog_dispatches_separate_artifact(monkeypatch, tmp_path, capsys, valid):
    suite = tmp_path / "catalog.json"
    suite.write_text('{"schema_version": 2}')
    artifact, output = tmp_path / "policy.json", tmp_path / "evaluation"
    evaluate = Mock(return_value={
        "valid": valid, "metrics": {"policy_failures": 2},
        "macro": {"policy_attempt_win_rate": 0.5},
    })
    monkeypatch.setitem(sys.modules, "spire.catalog", SimpleNamespace(evaluate_catalog=evaluate))
    monkeypatch.setattr(sys, "argv", [
        "spire", "evaluate", "--language-artifact", str(artifact),
        "--suite", str(suite), "--output", str(output),
    ])
    assert main() == (0 if valid else 1)
    evaluate.assert_called_once_with("language", suite, output, checkpoint=None,
                                     language_artifact=artifact)
    printed = capsys.readouterr().out
    assert '\"policy_failures\": 2' in printed
    assert str(output / "catalog-evaluation.json") in printed
