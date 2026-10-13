import pytest

from twwarhammer3 import protocol

OBSERVATION = {
    "armies": {"player": {"faction": "wh3_main_cth_cathay"}, "enemy": {"faction": "wh3_main_grn"}},
    "friendly": [{"id": "f1"}, {"id": "f2"}],
    "enemy_roster": [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}],
    "enemy": [{"id": "e2"}],
}


@pytest.mark.parametrize("orders", [
    [],
    [{"unit": "f1", "type": "halt"}],
    [{"unit": "f1", "type": "move", "x": 10, "z": -20.5, "run": True}],
    [{"unit": "f2", "type": "attack", "target": "e2", "run": False}],
])
def test_allowed_orders_pass(orders):
    protocol.validate_orders(orders, OBSERVATION)


@pytest.mark.parametrize(("orders", "message"), [
    ([{"unit": "e1", "type": "halt"}], "unknown friendly"),
    ([{"unit": "f1", "type": "halt"}, {"unit": "f1", "type": "halt"}], "ordered twice"),
    ([{"unit": "f1", "type": "charge"}], "unknown order type"),
    ([{"unit": "f1", "type": "move", "x": 1, "z": None}], "finite"),
    ([{"unit": "f1", "type": "move", "x": float("nan"), "z": 1}], "finite"),
    ([{"unit": "f1", "type": "move", "x": True, "z": 1}], "finite"),
    ([{"unit": "f1", "type": "attack", "target": "e1"}], "not visible"),
    (["halt"], "not an object"),
])
def test_disallowed_orders_are_named(orders, message):
    with pytest.raises(protocol.IllegalActionError, match=message):
        protocol.validate_orders(orders, OBSERVATION)


def test_scenario_key_counts_the_roster_not_the_visible_enemies():
    assert protocol.scenario_key(OBSERVATION) == "wh3_main_cth_cathay(2) vs wh3_main_grn(3)"


def capable_observation():
    return {**OBSERVATION, "friendly": [{"id": "f1", "ammo": 10,
            "behaviours": {"fire_at_will": True, "skirmish": False},
            "abilities": [{"key": "buff", "can_use": True},
                          {"key": "cooling", "can_use": False}]}, {"id": "f2"}]}


def test_toggles_ability_and_a_flanking_sequence_can_share_a_unit():
    protocol.validate_orders([
        {"unit": "f1", "type": "behaviour", "behaviour": "fire_at_will", "enabled": False},
        {"unit": "f1", "type": "ability", "ability": "buff", "target": "f2"},
        {"unit": "f1", "type": "move", "x": 10, "z": 20, "facing": 90, "width": 30},
        {"unit": "f1", "type": "move", "x": 50, "z": 20, "queue": True},
        {"unit": "f1", "type": "attack", "target": "e2", "mode": "melee", "queue": True},
    ], capable_observation())


@pytest.mark.parametrize(("order", "message"), [
    ({"type": "attack", "target": "e2", "queue": True}, "must follow a move"),
    ({"type": "attack", "target": "e2", "mode": "magic"}, "attack mode"),
    ({"type": "move", "x": 0, "z": 1, "width": -1}, "width"),
    ({"type": "move", "x": 0, "z": 1, "queue": "false"}, "booleans"),
    ({"type": "behaviour", "behaviour": "skirmish", "enabled": 1}, "boolean"),
    ({"type": "behaviour", "behaviour": "invincible", "enabled": True}, "unavailable"),
    ({"type": "ability", "ability": "unknown"}, "unavailable"),
    ({"type": "ability", "ability": "cooling"}, "unavailable"),
    ({"type": "ability", "ability": "buff", "target": "e1"}, "not visible"),
    ({"type": "ability", "ability": "buff", "target": "e2", "x": 0, "z": 1}, "ground"),
    ({"type": "ability", "ability": "buff", "x": 0}, "ground"),
])
def test_extended_orders_reject_unavailable_actions_and_invalid_arguments(order, message):
    with pytest.raises(protocol.IllegalActionError, match=message):
        protocol.validate_orders([{"unit": "f1", **order}], capable_observation())


def test_no_ranged_attack_without_ammunition_or_queue_after_an_attack():
    with pytest.raises(protocol.IllegalActionError, match="ammunition"):
        protocol.validate_orders([{"unit": "f2", "type": "attack", "mode": "ranged",
                                   "target": "e2"}], capable_observation())
    with pytest.raises(protocol.IllegalActionError, match="must follow a move"):
        protocol.validate_orders([{"unit": "f1", "type": "attack", "target": "e2"},
                                  {"unit": "f1", "type": "move", "x": 1, "z": 2,
                                   "queue": True}], capable_observation())
