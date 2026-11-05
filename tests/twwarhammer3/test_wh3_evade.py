"""Evade's order rules on observations shaped like saved jobs; no live game or tactical claim."""

import pytest

from twwarhammer3.battle import controllers
from twwarhammer3.battle.evade import RETRY_MS, Evade
from twwarhammer3.protocol import HIDDEN_KEYS, PolicyFailure, validate_orders

MAP = {"min_x": -512, "max_x": 512, "min_z": -512, "max_z": 512}  # A's real public bounds
NEAR = -482  # 30 m inside
FAR = 482


def unit(identity, x, z, *state, **changes):
    """A row with the fields of a saved Cannae job's first observation."""
    return {"id": identity, "type": "wh_main_emp_inf_swordsmen", "class": "infantry",
            "commander": False, "can_fly": False, "flying": False, "bearing": 93, "x": x, "z": z,
            "men": 90, "men0": 90, "hp": 1, "range": 0, "speed": [1.5, 3], "state": list(state),
            **changes}


def view(friendly, enemy, time_ms=5200, bounds=MAP):
    return {"schema": 1, "job": "job", "battle": "b1", "seq": 1, "phase": "Deployed",
            "time_ms": time_ms, "speed": 1, "remaining_ms": 1200000 - time_ms,
            "friendly": friendly, "enemy": enemy,
            "enemy_roster": [{"id": row["id"], "type": row["type"]} for row in enemy],
            "mode": {"type": "land_normal", "role": "defender", "timeout_winner": "us"},
            "terrain": {"x0": bounds["min_x"] + 16, "z0": bounds["min_z"] + 16, "cell_m": 32,
                        "rows": ["." * 32] * 32, "sample_width_m": 16, "sampled_ms": 4900,
                        "bounds": bounds}}


def run_to(identity, x, z):
    return {"unit": identity, "type": "move", "x": x, "z": z, "run": True}


def refused(*orders, error="unreachable"):
    """An acknowledgement shaped like a saved job's refused move."""
    return {"request": 1, "applied_ms": 5300, "results": [
        {"index": index, "unit": order["unit"], "ok": False, "error": error}
        for index, order in enumerate(orders, 1)]}


class Public(dict):
    """An observation that fails the test when a hidden key is read."""

    def __getitem__(self, key):
        assert key not in HIDDEN_KEYS, key
        return super().__getitem__(key)

    def get(self, key, default=None):
        assert key not in HIDDEN_KEYS, key
        return super().get(key, default)


def test_units_in_contact_run_to_the_point_farthest_from_every_enemy_and_never_attack():
    policy = Evade()
    friendly = [unit("f1", 60, -175, "melee"), unit("f2", 60, -225, "melee", "wavering"),
                unit("f3", 0, -125, "moving", "running")]
    enemy = [unit("e1", 62, -175, "melee"), unit("e2", 246, -225)]
    orders = []
    for step, time_ms in enumerate(range(5200, 60000, 1200)):
        observation = view(friendly, enemy, time_ms)
        batch = policy.decide(observation)
        validate_orders(batch, observation)
        orders += batch
        if step == 0:
            assert batch == [run_to(u["id"], NEAR, FAR) for u in friendly]
    assert {order["type"] for order in orders} == {"move"}
    assert all(order["run"] is True for order in orders)


def test_points_follow_the_public_bounds_and_edge_midpoints_can_be_the_farthest():
    bounds = {"min_x": -100, "max_x": 900, "min_z": 200, "max_z": 1000}
    left, right, low, high = -70, 870, 230, 970
    corners = [unit(f"e{i}", x, z) for i, (x, z) in enumerate(
        ((left, low), (left, high), (right, low), (right, high)))]
    friendly = [unit("f1", 800, 800)]
    # With enemies on all four corners the long sides' midpoints are farthest.
    assert Evade().decide(view(friendly, corners, bounds=bounds)) == [run_to("f1", 400, high)]
    assert Evade().decide(view(friendly, corners[:1], bounds=bounds)) == [
        run_to("f1", right, high)]
    # Taller than wide, so the z midpoint decides; 0 would be wrong here.
    tall = {"min_x": 200, "max_x": 1000, "min_z": -100, "max_z": 900}
    corners = [unit(f"e{i}", x, z) for i, (x, z) in enumerate(
        ((230, -70), (230, 870), (970, -70), (970, 870)))]
    assert Evade().decide(view(friendly, corners, bounds=tall)) == [run_to("f1", 970, 400)]


@pytest.mark.parametrize("state", ("melee", "routing"))
def test_an_enemy_counts_for_distance_whatever_it_is_doing(state):
    # Without e1 the pick would be the corner 116 m from it.
    enemy = [unit("e1", -400, 400, state), unit("e2", 400, -100)]
    assert Evade().decide(view([unit("f1", 0, 0, "idle")], enemy)) == [run_to("f1", NEAR, NEAR)]


def test_an_exact_tie_goes_to_each_units_nearest_point():
    friendly = [unit("f1", -300, -300), unit("f2", 300, 300), unit("f3", -300, 300)]
    assert Evade().decide(view(friendly, [unit("e1", 0, 0)])) == [
        run_to("f1", NEAR, NEAR), run_to("f2", FAR, FAR), run_to("f3", NEAR, FAR)]


def test_a_unit_reissues_only_on_a_new_point_or_after_stopping_and_at_most_every_10_s():
    policy = Evade()
    east, north = [unit("e1", 400, 0)], [unit("e1", -300, 500)]
    start = 5200
    ahead = run_to("f1", NEAR, NEAR)  # 400, 0 ties the two west corners; f1 is nearer this one
    moving, fighting = unit("f1", -100, -100, "moving", "running"), unit("f1", -100, -100, "melee")
    assert policy.decide(view([moving], east, start)) == [ahead]
    # The same point while moving: never again, however long it takes.
    assert policy.decide(view([moving], east, start + 3 * RETRY_MS)) == []
    # Stopped, shown here by melee with no idle flag, as most saved fighting rows are.
    now = start + 3 * RETRY_MS + 1200
    assert policy.decide(view([fighting], east, now)) == [ahead]
    assert policy.decide(view([fighting], east, now + RETRY_MS - 1)) == []
    # A new point also waits out the 10 s.
    new = run_to("f1", FAR, NEAR)
    assert policy.decide(view([moving], north, now + RETRY_MS - 1)) == []
    assert policy.decide(view([moving], north, now + RETRY_MS)) == [new]


def test_the_10_s_bound_is_per_unit():
    policy = Evade()
    east, start = [unit("e1", 400, 0)], 5200
    first, second = run_to("f1", NEAR, NEAR), run_to("f2", NEAR, FAR)
    moving = [unit("f1", -100, -100, "moving"), unit("f2", -100, 100, "moving")]
    stopped = [unit("f1", -100, -100, "idle"), unit("f2", -100, 100, "idle")]
    assert policy.decide(view(moving, east, start)) == [first, second]
    assert policy.decide(view([stopped[0], moving[1]], east, start + RETRY_MS)) == [first]
    # f2 stops a second after f1's order; that order must not hold f2 back.
    assert policy.decide(view(stopped, east, start + RETRY_MS + 1000)) == [second]


def test_a_refused_point_is_left_out_and_the_unit_runs_to_the_next_farthest():
    policy = Evade()
    stopped, enemy = [unit("f1", 0, 0, "idle")], [unit("e1", -300, -100)]
    corner, next_best = run_to("f1", FAR, FAR), run_to("f1", FAR, NEAR)
    assert policy.decide(view(stopped, enemy, 5200)) == [corner]
    policy.acknowledge(refused(corner), {})
    # The new point still waits out the 10 s.
    assert policy.decide(view(stopped, enemy, 5200 + RETRY_MS - 1)) == []
    assert policy.decide(view(stopped, enemy, 5200 + RETRY_MS)) == [next_best]
    # The list is the army's: a unit that never tried that point is not sent there either.
    assert policy.decide(view([unit("f2", 400, 400, "idle")], enemy, 5200 + RETRY_MS)) == [
        run_to("f2", FAR, NEAR)]


def test_only_an_unreachable_refusal_drops_a_point():
    policy = Evade()
    stopped, enemy = [unit("f1", 0, 0, "idle")], [unit("e1", -300, -100)]
    orders = policy.decide(view(stopped, enemy, 5200))
    policy.acknowledge(refused(*orders, error="unit_routing"), {})
    assert policy.decide(view(stopped, enemy, 5200 + RETRY_MS)) == orders


def test_with_all_eight_points_refused_the_job_fails_rather_than_holding_silently():
    policy = Evade()
    stopped, enemy = [unit("f1", 0, 0, "idle")], [unit("e1", 400, 0)]
    tried = []
    with pytest.raises(PolicyFailure, match="refused"):
        for step in range(9):
            orders = policy.decide(view(stopped, enemy, 5200 + step * RETRY_MS))
            policy.acknowledge(refused(*orders), {})
            tried += [(order["x"], order["z"]) for order in orders]
    assert len(tried) == len(set(tried)) == 8


def test_only_able_units_get_orders():
    friendly = [unit("f1", 0, 0, "moving", "routing", "running"),
                unit("f2", 0, 0, "moving", "routing", "running", "shattered"),
                unit("f3", 0, 0, "idle", men=0), {"id": "f4", "error": "read failed"},
                unit("f5", 0, 0, "idle")]
    assert [order["unit"] for order in Evade().decide(view(friendly, [unit("e1", 400, 0)]))] == [
        "f5"]


def test_no_visible_enemy_means_no_order_even_for_a_stopped_unit():
    policy = Evade()
    friendly = [unit("f1", 0, 0, "idle")]
    assert policy.decide(view(friendly, [unit("e1", 400, 0)])) != []
    assert policy.decide(view(friendly, [], 5200 + 2 * RETRY_MS)) == []
    assert Evade().decide(view(friendly, [])) == []


def test_it_reads_no_hidden_key():
    observation = view([unit("f1", 0, 0, "idle")], [unit("e1", 400, 0)])
    expected = Evade().decide(observation)
    hidden = Public(observation, evaluation={"enemy": {"men": 1}}, final={"result": "won"},
                    setup={"enemy_unit_stats": {}}, native={"id": 1})
    assert Evade().decide(hidden) == expected


def test_missing_bounds_are_a_failure_rather_than_a_silent_hold():
    observation = view([unit("f1", 0, 0, "idle")], [unit("e1", 400, 0)])
    del observation["terrain"]
    with pytest.raises(PolicyFailure, match="bounds"):
        Evade().decide(observation)


def test_it_loads_as_an_outside_controller_with_its_own_metadata():
    name = "twwarhammer3.battle.evade:Evade"
    policy = controllers.factories({"policy": name})[name]()
    assert type(policy) is Evade and policy.metadata() == {"type": "evade"}
