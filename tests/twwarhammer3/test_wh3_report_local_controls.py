"""A development screen must keep its completed silent controls beside its witnesses.

Reference: the seven-condition card/manifest in runs/comm-next-20261110. A local rush
and central concentration are scripted controls even though their channel is version 1.
"""

import json
from copy import deepcopy

import pytest
from wh3_fixtures import make_job

from twwarhammer3.battle import report, report_html

PREFIX = "twwarhammer3.battle.local_scripts:"


def member(name, kind="external"):
    return {"class": PREFIX + name, "kind": kind}


def team(*members):
    return {"kind": "composed", "class": "twwarhammer3.battle.local_team:LocalTeam",
            "disclosure": {"member_controllers": dict(enumerate(members))}}


def test_completed_silent_controls_stay_visible_as_separate_rows_beside_a_witness(tmp_path):
    jobs = []
    for name, script, version, arm, ending in (
        ("rush", "ThinkingRush", 1, "silent", "lost"),
        ("concentration", "CentralConcentration", 1, "silent", "lost"),
        ("witness", "PeerWitness", 2, "peer", "won"),
    ):
        job = make_job(tmp_path, name, [("configured", 0.1, ending)])
        path = job / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["scenario"] = {"name": arm, "communication": {"version": version, "arm": arm}}
        path.write_text(json.dumps(manifest))
        path = job / "episode-0000/result.json"
        result = json.loads(path.read_text())
        result["card"] = team(*[member(script) for _ in range(5)])
        path.write_text(json.dumps(result))
        jobs.append(job)
    source = report.collect(jobs)
    original = deepcopy(source)
    data = report_html.display_data(source)
    shown = {key for scenario in data["scenarios"] for key in scenario["battles"]}
    assert shown == set(data["battles"]) and len(shown) == 3
    silent = next(scenario for scenario in data["scenarios"] if scenario["name"] == "silent")
    assert {(row["kind"], row["name"], len(row["battles"])) for row in silent["rows"]} == {
        ("scripted", "Local rush", 1), ("scripted", "Central concentration", 1)}
    assert data["omitted"]["battles"] == []
    assert source == original


@pytest.mark.parametrize("other", [
    member("Unknown"), member("ThinkingRush", "model"), member("CentralConcentration"),
])
def test_unknown_model_or_mixed_silent_members_stay_diagnostic(other):
    trial = {"policy": "configured", "card": team(member("ThinkingRush"), other)}
    definition = {"scenario": {"communication": {"version": 1, "arm": "silent"}}}
    assert report_html.commander(trial, definition)["kind"] == "diagnostic"
