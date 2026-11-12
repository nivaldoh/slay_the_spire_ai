"""V2's door rule across refused/accepted orders; no claim of engine action.

Reference: escalade-eval.md, Witness version 2 options: replace the standing gate attack
with one halt if no other order replaces it. integration.md, Acknowledgements: a refusal
is not issuance. The public Helmgart sketch remains the existing unverified fixture.
"""

import pytest
from wh3_siege_attack import first_observation, later

from twwarhammer3.battle import escalade, play
from twwarhammer3.protocol import validate_orders

GATE_ATTACKERS = (escalade.EscaladeV2, escalade.ConcentrateV2, escalade.CavalryEarlyV2,
                  escalade.PiecemealV2, escalade.GateOnlyV2, escalade.BesiegeNearestV2)


def decide(policy, observation, refused=()):
    orders = policy.decide(play.public(observation, {}))
    validate_orders(orders, observation)
    # These scripts issue at most one replacement order per unit, never queued successors.
    assert len({o["unit"] for o in orders}) == len(orders)
    policy.acknowledge({"results": [
        {"index": i, "unit": o["unit"], "ok": o["unit"] not in refused, "queued": False}
        for i, o in enumerate(orders, 1)]}, {})
    return orders


def gate_attack(make, refused=()):
    start, policy = first_observation(), make()
    decide(policy, start, refused)
    orders = decide(policy, later(start, 150000), refused)
    assert any(o["unit"] == "f13" and o["type"] == "attack_building" and o["target"] == "g1"
               for o in orders)
    fallen = later(start, 165000, mode={"gates": [
        {"destroyed": False, "hp": 0, "name": "Gatehouse", "x": -32, "z": -16}]})
    fallen["mode"]["fortifications"][0]["hp"] = 10
    fallen["enemy"] = []
    return policy, fallen


def for_unit(orders, identity="f13"):
    return [o for o in orders if o["unit"] == identity]


@pytest.mark.parametrize("make", GATE_ATTACKERS)
def test_refused_halt_retries_until_accepted_then_stops_even_when_idle(make):
    policy, fallen = gate_attack(make)
    halt = [{"unit": "f13", "type": "halt"}]
    assert for_unit(decide(policy, fallen, refused={"f13"})) == halt
    assert for_unit(decide(policy, later(fallen, 166000), refused={"f13"})) == halt
    assert for_unit(decide(policy, later(fallen, 167000))) == halt
    assert for_unit(decide(policy, later(fallen, 180000))) == []


@pytest.mark.parametrize("make", [escalade.EscaladeV2, escalade.BesiegeNearestV2])
def test_refused_halt_survives_a_missing_fort_read(make):
    policy, fallen = gate_attack(make)
    decide(policy, fallen, refused={"f13"})
    unread = later(fallen, 166000)
    unread["mode"] = {"error": "mode_section failed"}
    assert for_unit(decide(policy, unread)) == [{"unit": "f13", "type": "halt"}]


@pytest.mark.parametrize("change", [{"state": ["routing"]}, {"men": 0}])
def test_pending_halt_waits_for_an_able_unit(change):
    policy, fallen = gate_attack(escalade.EscaladeV2)
    decide(policy, fallen, refused={"f13"})
    assert for_unit(decide(policy, later(fallen, 166000, f13=change))) == []
    assert for_unit(decide(policy, later(fallen, 167000))) == [{"unit": "f13", "type": "halt"}]


@pytest.mark.parametrize("make,identity,kind", [
    (escalade.EscaladeV2, "f4", "move"), (escalade.BesiegeNearestV2, "f13", "attack")])
@pytest.mark.parametrize("accepted", [False, True])
def test_only_an_accepted_replacement_clears_the_need_to_stop(make, identity, kind, accepted):
    policy, fallen = gate_attack(make)
    replacement = later(fallen, 165000)
    replacement["enemy"] = first_observation()["enemy"]
    orders = for_unit(decide(policy, replacement, refused=set() if accepted else {identity}),
                      identity)
    assert len(orders) == 1 and orders[0]["type"] == kind
    # The next read cannot supply a new siege/move/attack; the old gate attack still needs
    # a halt only if its replacement was refused. Both cases retain the known door breach.
    unread = later(fallen, 166000)
    unread["mode"] = {"error": "mode_section failed"}
    assert for_unit(decide(policy, unread), identity) == (
        [] if accepted else [{"unit": identity, "type": "halt"}])


@pytest.mark.parametrize("accepted", [False, True])
def test_replacement_before_the_breach_does_not_erase_an_unreplaced_gate_order(accepted):
    policy, fallen = gate_attack(escalade.EscaladeV2)
    # As in the existing phase-4 fixture: six infantry enter before the door falls, so
    # everyone, including the Grom, attacks an enemy. A refused attack leaves g1 in force.
    inside = {f"f{i}": {"z": 40.0, "x": -20.0 + 8 * i} for i in (2, 3, 4, 5, 6, 7)}
    combat = later(first_observation(), 160000, **inside)
    replacement = for_unit(decide(policy, combat, refused=set() if accepted else {"f13"}))
    assert len(replacement) == 1 and replacement[0]["type"] == "attack"
    breached = later(combat, 165000, mode=fallen["mode"])
    breached["enemy"] = []
    assert for_unit(decide(policy, breached)) == (
        [] if accepted else [{"unit": "f13", "type": "halt"}])


@pytest.mark.parametrize("make", [escalade.EscaladeV2, escalade.BesiegeNearestV2])
def test_a_refused_gate_order_does_not_create_a_standing_order_to_halt(make):
    policy, fallen = gate_attack(make, refused={"f13"})
    assert for_unit(decide(policy, fallen)) == []


@pytest.mark.parametrize("make", [escalade.EscaladeV2, escalade.BesiegeNearestV2])
@pytest.mark.parametrize("accepted", [False, True])
def test_missing_door_read_does_not_restart_a_known_breached_gate_attack(make, accepted):
    policy, fallen = gate_attack(make)
    assert for_unit(decide(policy, fallen, refused=set() if accepted else {"f13"})) == [
        {"unit": "f13", "type": "halt"}]
    partial = later(fallen, 166000, mode={"gates": []})  # g1 still reads 10% in fortifications
    assert for_unit(decide(policy, partial)) == (
        [] if accepted else [{"unit": "f13", "type": "halt"}])
    assert for_unit(decide(policy, later(partial, 180000))) == []
