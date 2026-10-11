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


def test_language_catalog_rejected_before_optional_model_import(monkeypatch, tmp_path, capsys):
    suite = tmp_path / "catalog.json"
    suite.write_text('{"schema_version": 2}')
    evaluate = Mock()
    monkeypatch.setitem(sys.modules, "spire.language_evaluation",
                        SimpleNamespace(evaluate_language=evaluate))
    monkeypatch.setattr(sys, "argv", [
        "spire", "evaluate", "--language-artifact", "policy.json",
        "--suite", str(suite), "--output", "unused",
    ])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    evaluate.assert_not_called()
    assert "requires a schema-1 suite" in capsys.readouterr().err
