import json
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from spire.__main__ import main


@pytest.mark.parametrize("valid", [True, False])
@pytest.mark.parametrize("policy_args", [["--policy", "heuristic"], ["--checkpoint", "policy.pt"]])
def test_catalog_evaluation_dispatches_and_reports_macro(
    monkeypatch, tmp_path, capsys, valid, policy_args
):
    suite = tmp_path / "catalog.json"
    suite.write_text('{"schema_version": 2}')
    output = tmp_path / "result"
    result = {"valid": valid, "metrics": {"wins": 3}, "macro": {"win_rate": 0.75}}
    evaluate = Mock(return_value=result)
    monkeypatch.setitem(sys.modules, "spire.catalog", SimpleNamespace(evaluate_catalog=evaluate))
    monkeypatch.setattr(sys, "argv", [
        "spire", "evaluate", *policy_args, "--suite", str(suite), "--output", str(output)
    ])

    assert main() == (0 if valid else 1)
    assert evaluate.call_args.args == (
        "neural" if policy_args[0] == "--checkpoint" else "heuristic", suite, output
    )
    checkpoint = evaluate.call_args.kwargs["checkpoint"]
    assert (str(checkpoint) if checkpoint else None) == (
        "policy.pt" if policy_args[0] == "--checkpoint" else None
    )
    printed = capsys.readouterr().out
    assert '"win_rate": 0.75' in printed
    assert str(output / "catalog-evaluation.json") in printed


@pytest.mark.parametrize("declaration", [[], {}, {"schema_version": True}, {"schema_version": 3}])
def test_invalid_schema_fails_before_evaluation(monkeypatch, tmp_path, declaration):
    suite = tmp_path / "suite.json"
    suite.write_text(json.dumps(declaration))
    evaluate = Mock()
    monkeypatch.setitem(sys.modules, "spire.catalog", SimpleNamespace(evaluate_catalog=evaluate))
    monkeypatch.setattr(sys, "argv", [
        "spire", "evaluate", "--policy", "random", "--suite", str(suite), "--output", "unused"
    ])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    evaluate.assert_not_called()


@pytest.mark.parametrize("catalog", [True, False])
@pytest.mark.parametrize("valid", [True, False])
def test_report_uses_matching_auditor_and_writes_json(
    monkeypatch, tmp_path, capsys, catalog, valid
):
    run = tmp_path / "run"
    run.mkdir()
    if catalog:
        # A partial parent manifest must still go through the catalog auditor.
        (run / "catalog-manifest.json").write_text("{}")
    result = {"valid": valid, "runs": []}
    compare = Mock(return_value=result)
    render = Mock(return_value="Audited result\n")
    if catalog:
        module = "spire.catalog_report"
        functions = {"compare_catalogs": compare, "render_catalog_report": render}
    else:
        module = "spire.report"
        functions = {"compare_runs": compare, "render_report": render}
    monkeypatch.setitem(sys.modules, module, SimpleNamespace(**functions))
    output = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", ["spire", "report", str(run), "--output", str(output)])

    assert main() == (0 if valid else 1)
    compare.assert_called_once_with([run])
    render.assert_called_once_with(result)
    assert json.loads(output.read_text()) == result
    assert "Audited result" in capsys.readouterr().out


def test_report_rejects_mixed_catalog_and_legacy_runs(monkeypatch, tmp_path, capsys):
    catalog = tmp_path / "catalog"
    catalog.mkdir()
    (catalog / "catalog.json").write_text("{}")
    monkeypatch.setattr(sys, "argv", ["spire", "report", str(catalog), str(tmp_path / "legacy")])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert "Report catalogs and single-scenario runs separately" in capsys.readouterr().err
