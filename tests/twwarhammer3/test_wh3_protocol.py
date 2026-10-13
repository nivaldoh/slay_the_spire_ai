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
