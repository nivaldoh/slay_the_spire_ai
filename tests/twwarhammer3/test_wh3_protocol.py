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
    [{"unit": "f1", "type": "halt", "x": 0, "z": -20.5, "target": None,
      "run": False, "queue": False, "extra": True}],
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
    ([{"unit": "f2", "type": "attack", "target": ["e2"]}], "field 'target' must be a string"),
    ([{"unit": "f1", "type": "move", "x": 10**400, "z": 1}], "finite"),
])
def test_disallowed_orders_are_named(orders, message):
    with pytest.raises(protocol.IllegalActionError, match=message):
        protocol.validate_orders(orders, OBSERVATION)


@pytest.mark.parametrize("orders", [None, {"unit": "f1", "type": "halt"}, "halt"],
                         ids=["none", "one-order-object", "string"])
def test_a_reply_that_is_not_a_list_is_an_illegal_batch(orders):
    # Without the list check, None crashed validation with a TypeError instead of naming an
    # invalid batch (the one uncaught refusal removal in runs/protocol-planted-20261029/).
    with pytest.raises(protocol.IllegalActionError, match="must be a list"):
        protocol.validate_orders(orders, OBSERVATION)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), 10**400],
                         ids=["nan", "infinity", "negative-infinity", "oversized-integer"])
def test_nonfinite_order_fields_are_rejected(value):
    # Even fields a command ignores cross the Python -> Lua JSON boundary.
    with pytest.raises(protocol.IllegalActionError, match="finite"):
        protocol.validate_orders([{"unit": "f1", "type": "halt", "x": value}], OBSERVATION)


def test_scenario_key_counts_the_roster_not_the_visible_enemies():
    assert protocol.scenario_key(OBSERVATION) == "wh3_main_cth_cathay(2) vs wh3_main_grn(3)"


def test_flight_requests_use_capability_readiness_and_requested_state():
    unit = {"id": "f1", "can_fly": True, "flying": True, "flight": {"can_toggle": True}}
    state = {"friendly": [unit]}
    land = {"unit": "f1", "type": "flight", "flying": False}
    protocol.validate_orders([land], state)
    with pytest.raises(protocol.IllegalActionError, match="repeated flight"):
        protocol.validate_orders([land, land], state)
    with pytest.raises(protocol.IllegalActionError, match="boolean"):
        protocol.validate_orders([{**land, "flying": 0}], state)
    unit["flight"]["can_toggle"] = False
    with pytest.raises(protocol.IllegalActionError, match="unavailable now"):
        protocol.validate_orders([land], state)
    unit["flying"] = False
    protocol.validate_orders([land], state)  # already landed; a repeated request is a no-op
    unit["can_fly"] = False
    with pytest.raises(protocol.IllegalActionError, match="cannot fly"):
        protocol.validate_orders([land], state)


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


ABILITIES = dict(OBSERVATION, friendly=[
    {"id": "f1", "abilities": [{"key": "roar", "can_use": True, "ready": True},
                               {"key": "rage", "can_use": True, "ready": False}]},
    {"id": "f2"}], army={"currency": 120, "next_unlock": 200, "abilities": [
        {"key": "horn", "target": "Ground, Ally", "unlocked": True, "ready": True},
        {"key": "rage", "target": "Ally", "unlocked": True, "ready": False},
        {"key": "blade", "target": "Ground", "unlocked": False, "ready": False}]})


def test_abilities_must_be_ready_and_army_abilities_unlocked():
    ability = {"type": "ability", "target": None, "x": None, "z": None}
    protocol.validate_orders([dict(ability, unit="f1", ability="roar")], ABILITIES)
    with pytest.raises(protocol.IllegalActionError, match="'rage' is not ready"):
        protocol.validate_orders([dict(ability, unit="f1", ability="rage")], ABILITIES)
    horn = dict(ability, unit="army", ability="horn", x=10.0, z=20.0)
    protocol.validate_orders([horn], ABILITIES)
    protocol.validate_orders([dict(horn, x=None, z=None, target="f2")], ABILITIES)
    for order, message in [
        (dict(horn, ability="blade"), "unavailable army ability 'blade'"),
        (dict(horn, ability="rage", x=None, z=None, target="f1"), "'rage' is not ready"),
        (dict(horn, ability="roar"), "unavailable army ability 'roar'"),
        (dict(horn, x=None, z=None), "needs a unit target or x/z"),
        (dict(horn, target="e1"), "not visible"),
    ]:
        with pytest.raises(protocol.IllegalActionError, match=message):
            protocol.validate_orders([order], ABILITIES)
    with pytest.raises(protocol.IllegalActionError, match="repeated ability 'horn'"):
        protocol.validate_orders([horn, horn], ABILITIES)
    with pytest.raises(protocol.IllegalActionError, match="unknown friendly"):
        protocol.validate_orders([dict(horn, type="halt")], ABILITIES)


SIEGE = {**OBSERVATION, "mode": {"supplies": 1000, "slots": [
    {"id": "s1", "type": "tower", "x": 55, "z": 192, "usable": True,
     "options": [{"name": "tower_piercing_1", "cost": 500}, {"name": "tower_cannon_4",
                                                              "cost": 2000}]},
    {"id": "s2", "type": "tower", "x": -56, "z": 192, "usable": True,
     "built": "tower_piercing_1"},
]}}


@pytest.mark.parametrize("order, error", [
    ({"slot": "s1", "option": "tower_piercing_1"}, None),
    ({"slot": "s9", "option": "tower_piercing_1"}, "unknown building slot"),
    ({"slot": "s2", "option": "tower_piercing_1"}, "already has a building"),
    ({"slot": "s1", "option": "tower_cannon_9"}, "has no option"),
    ({"slot": "s1", "option": "tower_cannon_4"}, "costs 2000, supplies 1000"),
])
def test_build_orders_need_an_empty_slot_a_listed_option_and_the_supplies(order, error):
    orders = [{"unit": "army", "type": "build", **order}]
    if error is None:
        protocol.validate_orders(orders, SIEGE)
    else:
        with pytest.raises(protocol.IllegalActionError, match=error):
            protocol.validate_orders(orders, SIEGE)
    twice = [orders[0], orders[0]]
    if error is None:
        with pytest.raises(protocol.IllegalActionError, match="ordered twice"):
            protocol.validate_orders(twice, SIEGE)


SURVIVAL = {**OBSERVATION, "mode": {
    "supplies": 1000, "spawn_zones": [{"id": 14, "x": 320, "z": 0, "usable": True},
                                      {"id": 9, "x": 0, "z": 0, "usable": False}],
    # As in the survival pool: one type at two costs, the dearer listed first.
    "reinforcements": [{"type": "marauders", "cost": 446}, {"type": "warriors", "cost": 900},
                       {"type": "marauders", "cost": 400}],
    "slots": [{"id": "s1", "usable": True, "options": [{"name": "barricade_trap", "cost": 200}]},
              {"id": "s2", "usable": False, "options": [{"name": "barricade_trap", "cost": 200}]}],
}}


@pytest.mark.parametrize("orders, error", [
    ([{"type": "reinforce", "reinforcement": "marauders", "zone": 14}], None),
    ([{"type": "reinforce", "reinforcement": "marauders", "zone": 14}] * 2, None),
    ([{"type": "reinforce", "reinforcement": "warriors", "zone": 14},
      {"type": "reinforce", "reinforcement": "marauders", "zone": 14}],
     "marauders costs 400, supplies 1000 \\(900 already ordered\\)"),  # the cheaper one first
    ([{"type": "reinforce", "reinforcement": "trolls", "zone": 14}], "no 'trolls' left"),
    ([{"type": "reinforce", "reinforcement": "warriors", "zone": 14}] * 2, "no 'warriors' left"),
    ([{"type": "reinforce", "reinforcement": "marauders", "zone": 3}], "not one of yours"),
    ([{"type": "reinforce", "reinforcement": "marauders", "zone": 9}], "refuses purchases now"),
    ([{"type": "build", "slot": "s2", "option": "barricade_trap"}], "cannot be built on now"),
    # Builds and reinforcements share the supplies: 900 + 200 > 1000.
    ([{"type": "reinforce", "reinforcement": "warriors", "zone": 14},
      {"type": "build", "slot": "s1", "option": "barricade_trap"}],
     "barricade_trap costs 200, supplies 1000 \\(900 already ordered\\)"),
])
def test_purchases_come_from_the_pool_or_usable_slots_within_the_batchs_supplies(orders, error):
    orders = [{"unit": "army", **order} for order in orders]
    if error is None:
        protocol.validate_orders(orders, SURVIVAL)
    else:
        with pytest.raises(protocol.IllegalActionError, match=error):
            protocol.validate_orders(orders, SURVIVAL)


def test_a_purchase_after_a_unit_ability_or_toggle_in_the_same_batch_validates():
    state = {**SURVIVAL, "friendly": [{"id": "f1", "behaviours": {"fire_at_will": True},
                                       "abilities": [{"key": "a", "can_use": True,
                                                      "ready": True}]}]}
    protocol.validate_orders([
        {"unit": "f1", "type": "behaviour", "behaviour": "fire_at_will", "enabled": False},
        {"unit": "f1", "type": "ability", "ability": "a", "target": None, "x": None, "z": None},
        {"unit": "army", "type": "reinforce", "reinforcement": "marauders", "zone": 14},
        {"unit": "army", "type": "build", "slot": "s1", "option": "barricade_trap"},
    ], state)
