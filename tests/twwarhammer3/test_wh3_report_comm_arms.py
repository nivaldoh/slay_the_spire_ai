"""Battle C v2's arms on the report page: report_html.commander makes a composed team on a
scenario whose `communication` declares version 2 a compared method named by its arm, with model
and scripted teams of one arm in separate rows. Member cards come from controllers.card over
the arms' own controller configurations, as a play job records them."""

import json

import pytest

from gameai.provenance import REPO_ROOT
from twwarhammer3.battle import controllers, local_team, report_html
from twwarhammer3.battle.setup import scenarios

JOB = {"model": "claude-haiku-5-5", "effort": "low", "provider": "anthropic"}


class Team:
    """Stands in for the built LocalTeam: controllers.card reads only its card."""

    def __init__(self, members):
        self.card = {"member_controllers": members}


def commander(config: str, scenario: str) -> dict:
    """The page's row for a team built from configs/twwarhammer3/controllers/<config>.json."""
    spec = json.loads((REPO_ROOT / f"configs/twwarhammer3/controllers/{config}.json").read_text())
    members = {}
    for name, member in spec["members"].items():
        kind = member["type"]
        # A model member needs an API to build; its card reads only the class and the job.
        policy = (object.__new__(local_team.LocalModel) if kind in controllers.MODEL_POLICIES
                  else controllers.controller_class(kind)())
        members[name] = controllers.card(kind, policy, JOB)
    trial = {"policy": "configured", "delay_ms": 0,
             "card": controllers.card("configured", Team(members), JOB)}
    return report_html.commander(trial, {"scenario": scenarios()[scenario], **JOB})


@pytest.mark.parametrize("scenario,config,name", [
    ("emp-envelopment-c-peer-v2", "cannae-peer-model", "Peer captains"),
    ("emp-envelopment-c-relay-v2", "cannae-relay-model", "Relay commander"),
    ("emp-envelopment-c-overview-v2", "cannae-overview-model", "Overview commander"),
    ("emp-envelopment-c-unlinked-v2", "cannae-unlinked-model", "No links")])
def test_a_model_team_on_a_v2_arm_is_a_model_row_named_by_its_arm(scenario, config, name):
    # Catches the version before 2026-11-08, which classed every C v2 battle as a diagnostic
    # probe (off the page, replay not embedded), and a row named by the shared model.
    who = commander(config, scenario)
    assert (who["kind"], who["name"], who["family"]) == ("model", name, "claude-haiku-5-5")
    assert who["detail"] == "model members: claude-haiku-5-5, low reasoning"
    assert who["short"] == "low reasoning"


@pytest.mark.parametrize("scenario,config,name,classes", [
    ("emp-envelopment-c-peer-v2", "cannae-peer-witness", "Peer captains", "PeerWitness"),
    ("emp-envelopment-c-relay-v2", "cannae-relay-witness", "Relay commander",
     "PeerWitness, RelayWitnessCommander"),
    ("emp-envelopment-c-overview-v2", "cannae-overview-witness", "Overview commander",
     "OverviewWitnessCaptain, OverviewWitnessCommander"),
    ("emp-envelopment-c-muted-v2", "cannae-muted-witness", "Muted peers", "PeerWitness"),
    ("emp-envelopment-c-muted-overview-v2", "cannae-muted-overview-witness", "Muted overview",
     "OverviewWitnessCaptain, OverviewWitnessCommander")])
def test_a_scripted_team_on_a_v2_arm_is_a_scripted_row_naming_its_classes(scenario, config, name,
                                                                          classes):
    # Catches classing every composed C v2 team as a model row: the witnesses would share the
    # arm's row (name and detail) and score with its model battles and take a model's colour.
    who = commander(config, scenario)
    assert (who["kind"], who["name"], who["family"]) == ("scripted", name, "Scripted")
    assert who["detail"] == f"scripted members: {classes}"
    # Catches one short label for every scripted row (review 2026-11-08: the witness and another
    # scripted team of one arm read the same in the battle picker).
    assert who["short"] == classes


@pytest.mark.parametrize("arm", ["peer", "relay", "overview"])
def test_a_stage_one_channel_probe_on_a_v2_arm_stays_a_diagnostic_probe(arm):
    # Catches scoring the delivery probes (TextProbeMember, ProbeCommander) as compared methods
    # (review 2026-11-08): they check delivery only and must stay off the page.
    assert commander(f"cannae-{arm}-probe", f"emp-envelopment-c-{arm}-v2")["kind"] == "diagnostic"


@pytest.mark.parametrize("scenario", ["emp-envelopment-c-v1", "emp-envelopment-c-global-v2"])
def test_a_team_on_a_v1_arm_stays_a_diagnostic_probe(scenario):
    # Catches keying on any `communication` declaration, or on the battle's own version 2
    # (global-v2 declares communication version 1), instead of the declaration's version 2.
    assert commander("cannae-local-model", scenario)["kind"] == "diagnostic"
