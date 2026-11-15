"""The base class's and CornerHold's commitments; game execution still needs the live checks.

The tests of the 23 diagnostics deleted on 2026-11-15 went with them (owner: "Delete all of
it"; tag wh3-legacy-20261115). Three tests that reached the base class through a deleted
subclass now call SmallDiagnostic itself.
"""

import math
from copy import deepcopy

from twwarhammer3.battle.calibration import CornerHold, SmallDiagnostic
from twwarhammer3.protocol import validate_orders


def unit(uid, kind, x, z, speed=5, **extra):
    return {"id": uid, "type": kind, "x": x, "z": z, "men": 30, "men0": 30,
            "speed": [2, speed], "class": "infantry", "state": [], **extra}


def test_small_diagnostics_do_not_use_hidden_enemies_or_order_routers():
    for cls in (CornerHold,):  # the only diagnostic left here; lines.py's are in its tests
        obs = {"time_ms": 1000, "friendly": [unit("f1", "horse", 0, 0)],
               "enemy": [], "evaluation": {"enemy": [unit("e1", "hidden", 5, 5)]},
               "enemy_roster": [unit("e1", "hidden", 5, 5)]}
        policy = cls()
        assert policy.decide(obs) == []
        obs["enemy"] = obs["enemy_roster"]
        obs["friendly"][0]["state"] = ["routing"]
        assert policy.decide(obs) == []


def test_routing_refusal_is_newer_than_a_delayed_snapshot():
    obs = {"time_ms": 1000, "friendly": [unit("f1", "horse", 0, 100)],
           "enemy": [unit("e1", "halberds", 0, 0)]}
    policy = SmallDiagnostic()
    assert policy.observe(obs)[0]
    policy.acknowledge({"applied_ms": 6000, "results": [
        {"unit": "f1", "ok": False, "error": "unit_routing"}]}, {})
    # The live delayed run repeatedly retried a known router from five-second-old state.
    obs["time_ms"] = 5000
    assert policy.observe(obs)[0] == []
    obs["time_ms"] = 7000
    obs["friendly"][0]["state"] = ["routing"]
    assert policy.observe(obs)[0] == []
    obs["friendly"][0]["state"] = []  # rallied: later public evidence permits orders again
    assert policy.observe(obs)[0]


REFUSED_EVERYWHERE = [{"x": x, "z": z} for x in range(-150, 151, 20)
                      for z in range(-140, 161, 20)]


def test_moves_step_off_restricted_cells_or_hold():
    # Live S6: HammerAnvil's wait post inside the central rock was refused 147 times.
    rows = ["." * 32 for _ in range(32)]
    rows[16] = "." * 16 + "#" + "." * 15  # the cell holding (16, 16)
    obs = {"time_ms": 1000, "friendly": [unit("f1", "knights", 200, 200)],
           "enemy": [unit("e1", "swordsmen", 0, 0)],
           "terrain": {"rows": rows, "cell_m": 32, "x0": -496, "z0": -496,
                       "bounds": {"min_x": -512, "max_x": 512, "min_z": -512, "max_z": 512}}}
    policy = SmallDiagnostic()
    policy.observe(obs)
    order = policy.move(obs["friendly"][0], {"x": 16, "z": 16}, obs["enemy"][0])[0]
    spot = (order["x"], order["z"])
    assert spot != (16, 16) and math.dist(spot, (16, 16)) <= 64
    policy.sent.clear()
    policy.unreachable = REFUSED_EVERYWHERE
    assert policy.move(obs["friendly"][0], {"x": 16, "z": 16}, obs["enemy"][0]) == []


def test_step_ring_stays_inside_the_map_and_off_map_points_are_blocked():
    # Live S3 r3 (b23): 13 of 14 refusals were ring points at x -514/-546, past min_x -512.
    bounds = {"min_x": -512, "max_x": 512, "min_z": -512, "max_z": 512}
    obs = {"time_ms": 1000, "friendly": [unit("f1", "handgunners", -400, -255)],
           "enemy": [unit("e1", "warriors", 0, 0)],
           "terrain": {"rows": [], "cell_m": 32, "x0": -496, "z0": -496, "bounds": bounds}}
    policy = SmallDiagnostic()
    policy.observe(obs)
    policy.unreachable = [{"x": -482, "z": -255}, {"x": -450, "z": -255}]
    (order,) = policy.move(obs["friendly"][0], {"x": -600, "z": -255}, obs["enemy"][0])
    assert (order["x"], order["z"]) == (-482, -223)  # b23: (-514, -255)
    # Every on-map spot within two cells of (-482, -255) is restricted: hold, not step off it.
    rows = ["." * 32 for _ in range(32)]
    rows[5:12] = ["###" + "." * 29] * 7
    obs["terrain"]["rows"] = rows
    policy = SmallDiagnostic()
    policy.observe(obs)
    assert policy.move(obs["friendly"][0], {"x": -600, "z": -255}, obs["enemy"][0]) == []
    # Posts are not clamped: one past the map's edge is blocked (b23: open), so the next is used.
    assert policy.open_point([{"x": -514, "z": 0}, {"x": -450, "z": 0}]) == {"x": -450, "z": 0}


def corner_terrain():
    rows = ["." * 25 for _ in range(25)]
    rows[0] = "#" + rows[0][1:]  # the sample holding the south-west corner post
    return {"x0": -384, "z0": -384, "cell_m": 32, "sample_width_m": 8, "rows": rows,
            "bounds": {"min_x": -400, "max_x": 400, "min_z": -400, "max_z": 400}}


def test_corner_hold_takes_its_own_side_corner_past_blocked_cells_and_faces_out():
    obs = {"time_ms": 1000, "terrain": corner_terrain(),
           "friendly": [unit("f1", "longbeards", -300, -310), unit("f2", "longbeards", -310, -300)],
           "enemy": [unit("e1", "swordsmen", 300, 300), unit("e2", "swordsmen", 320, 280)]}
    original = deepcopy(obs)
    policy = CornerHold()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert obs == original
    # 30 m inside the south-west corner is restricted; one 32 m step toward the centre.
    assert all(math.isclose(policy.corner[axis], -370 + 32 / math.sqrt(2)) for axis in "xz")
    assert [order["type"] for order in orders] == ["move", "move"]
    for order in orders:
        assert math.isclose(math.hypot(order["x"] - policy.corner["x"],
                                       order["z"] - policy.corner["z"]), 16, abs_tol=1e-6)
        assert 40 < order["facing"] < 50
    corner = dict(policy.corner)
    obs["enemy"][0].update(x=-300, z=300)
    policy.decide(obs)
    assert policy.corner == corner  # chosen once


def test_corner_hold_clamps_its_line_holds_and_fights_only_in_contact():
    obs = {"time_ms": 1000, "terrain": {**corner_terrain(), "rows": []},
           "friendly": [unit("f1", "longbeards", -330, -330), unit("f2", "longbeards", -340, -320)],
           "enemy": [unit("e1", "swordsmen", -370, 300)]}
    policy = CornerHold()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert policy.corner == {"x": -370, "z": -370}
    assert all(-370 <= order["x"] and -370 <= order["z"] for order in orders)
    for order in orders:
        next(u for u in obs["friendly"] if u["id"] == order["unit"]).update(
            x=order["x"], z=order["z"])
    obs["time_ms"] = 5000
    del obs["terrain"]  # later observations may omit the terrain snapshot
    assert policy.decide(obs) == []
    obs["enemy"][0].update(x=obs["friendly"][0]["x"] + 5, z=obs["friendly"][0]["z"] + 5)
    obs["friendly"][0]["state"] = ["melee"]
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert orders == [{"unit": "f1", "type": "attack", "run": True, "mode": "melee",
                       "target": "e1"}]
