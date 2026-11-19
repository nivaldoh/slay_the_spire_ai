"""The base class's and the four kept diagnostics' commitments; game execution still needs the
live checks.

The tests of the 20 diagnostics deleted on 2026-11-15 went with them (owner: "Delete all of
it"; tag wh3-legacy-20261115). Three tests that reached the base class through a deleted
subclass now call SmallDiagnostic itself, and the base class's order bookkeeping has its own
tests below.
"""

import math
from copy import deepcopy

from twwarhammer3.controllers.calibration import (
    CornerHold,
    LineTeam,
    LineTeamReserve,
    PriorityStrike,
    SmallDiagnostic,
    _keep,
    _offset,
)
from twwarhammer3.protocol import validate_orders


def unit(uid, kind, x, z, speed=5, **extra):
    return {"id": uid, "type": kind, "x": x, "z": z, "men": 30, "men0": 30,
            "speed": [2, speed], "class": "infantry", "state": [], **extra}


def test_small_diagnostics_do_not_use_hidden_enemies_or_order_routers():
    for cls in (CornerHold, PriorityStrike, LineTeam, LineTeamReserve):
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


ATTACK = {"unit": "f1", "type": "attack", "run": True, "mode": "melee", "target": "e1"}


def test_an_unchanged_order_waits_three_seconds_and_for_an_idle_unit_before_it_goes_again():
    """SmallDiagnostic.issue: "Keep a moving goal until it changes materially; retry
    dropped/rejected orders". These bookkeeping tests were added on 2026-11-15, when a review
    found that only tests of deleted subclasses had covered it. Wrong versions: an unchanged
    order is never sent again; it is sent again to a unit still carrying it out."""
    policy, rider = SmallDiagnostic(), unit("f1", "knights", 0, 0, state=["idle"])
    policy.now = 10
    assert policy.issue(rider, ATTACK) == [ATTACK]
    policy.now = 12
    assert policy.issue(rider, ATTACK) == []  # sent two seconds ago
    policy.now = 14
    assert policy.issue({**rider, "state": ["moving"]}, ATTACK) == []  # still carrying it out
    assert policy.issue(rider, ATTACK) == [ATTACK]  # idle again after three seconds: dropped
    move = {"unit": "f1", "type": "move", "run": True, "facing": 0, "x": 100, "z": 100}
    policy.now = 20
    assert policy.issue(rider, move) == [move]
    policy.now = 21
    assert policy.issue(rider, {**move, "x": 110}) == []  # under 15 m: the same goal
    assert policy.issue(rider, {**move, "x": 120}) == [{**move, "x": 120}]


def test_a_refused_order_is_forgotten_and_an_accepted_one_is_kept():
    """Wrong versions: a refused order stays on record, so it is not sent again; an accepted
    order is dropped from the record, so it is sent again at once."""
    policy, rider = SmallDiagnostic(), unit("f1", "knights", 0, 0, state=["idle"])
    policy.now = 10
    assert policy.issue(rider, ATTACK) == [ATTACK]
    policy.acknowledge({"applied_ms": 10500, "results": [{"unit": "f1", "ok": True}]}, {})
    policy.now = 11
    assert policy.issue(rider, ATTACK) == []
    policy.acknowledge({"applied_ms": 11500, "results": [
        {"unit": "f1", "ok": False, "error": "refused"}]}, {})
    assert policy.issue(rider, ATTACK) == [ATTACK]


def test_a_move_refused_as_unreachable_is_remembered_and_the_next_open_spot_is_taken():
    """SmallDiagnostic.move: "the nearest open spot within two terrain cells", away from refused
    moves. Wrong version: the refusal is not remembered and the same spot is ordered again."""
    obs = {"time_ms": 1000, "friendly": [unit("f1", "knights", 200, 200)],
           "enemy": [unit("e1", "swordsmen", 0, 0)],
           "terrain": {"rows": ["." * 32 for _ in range(32)], "cell_m": 32, "x0": -496,
                       "z0": -496,
                       "bounds": {"min_x": -512, "max_x": 512, "min_z": -512, "max_z": 512}}}
    policy = SmallDiagnostic()
    policy.observe(obs)
    rider, goal = obs["friendly"][0], {"x": 16, "z": 16}
    (first,) = policy.move(rider, goal, obs["enemy"][0])
    assert (first["x"], first["z"]) == (16, 16)
    policy.acknowledge({"applied_ms": 1500, "results": [
        {"unit": "f1", "ok": False, "error": "unreachable"}]}, {})
    (second,) = policy.move(rider, goal, obs["enemy"][0])
    assert (second["x"], second["z"]) == (48, 16)  # one 32 m cell on, 30 m clear of the refusal


def test_keep_holds_the_committed_target_while_it_is_listed_and_otherwise_takes_the_nearest():
    """_keep: "The committed target while it stays visible and unrouted, else the nearest"."""
    near, far, origin = unit("e1", "boyz", 10, 0), unit("e2", "boyz", 100, 0), {"x": 0, "z": 0}
    assert _keep([near, far], "e2", origin) is far
    assert _keep([far, near], "gone", origin) is near
    assert _keep([far, near], None, origin) is near


def test_offset_goes_forward_along_the_direction_and_across_to_its_left():
    """The convention CornerHold's line and LineTeam's posts are built on, as at the tag
    wh3-legacy-20261115: facing north (+z) a positive across is west (-x)."""
    assert _offset({"x": 0, "z": 0}, (0, 1), 10, 4) == {"x": -4, "z": 10}
    assert _offset({"x": 5, "z": 5}, (1, 0), 10, 4) == {"x": 15, "z": 9}


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


def by_unit(orders, uid):
    return [order for order in orders if order["unit"] == uid]


def test_priority_strike_flyers_take_the_enemy_with_the_lowest_men_fraction():
    """Its recorded card: "with neither visible, the enemy with the lowest men fraction". Added
    on 2026-11-15: the helper came back from the tag with only a deleted class's test covering
    it. Wrong version: the fraction is inverted, so the flyers go for the fullest unit."""
    obs = {"time_ms": 1000, "friendly": [unit("f1", "screamers", 0, 0, can_fly=True)],
           "enemy": [unit("e1", "clanrats", 0, 40), unit("e2", "clanrats", 0, 200, men=10)]}
    orders = PriorityStrike().decide(obs)
    validate_orders(orders, obs)
    assert [(order["unit"], order["target"]) for order in orders] == [("f1", "e2")]


def test_priority_strike_sends_flyers_past_the_screen_and_holds_the_ground_unit():
    obs = {"time_ms": 1000,
           "friendly": [unit("f1", "forsaken", 0, 0), unit("f2", "screamers", 10, 0,
                                                           can_fly=True, flying=True)],
           "enemy": [unit("e1", "stormvermin", 0, 60),
                     unit("e2", "warp_lightning_cannon", 0, 300, **{"class": "artillery"})]}
    policy = PriorityStrike()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert [(order["unit"], order["target"]) for order in orders] == [("f2", "e2")]
    obs["enemy"].pop()
    orders = policy.decide(obs)
    assert {order["unit"] for order in orders} == {"f1", "f2"}


def _line_battle():
    def inf(uid, kind, x, z, **extra):
        return unit(uid, kind, x, z, behaviours={"defend": False, "fire_at_will": True,
                                                  "skirmish": False}, **extra)
    def gun(uid, x, z):
        return unit(uid, "handgunners", x, z, cls="missile", ammo=1496, range=145,
                    behaviours={"defend": False, "fire_at_will": True, "skirmish": True})
    friendly = [inf("f1", "spearmen_1", 0, 20), inf("f2", "swordsmen", -30, 0),
                inf("f3", "swordsmen", 0, 0), inf("f4", "halberdiers", 30, 0),
                gun("f5", -20, 15), gun("f6", 20, 15),
                unit("f7", "empire_knights", 40, 40, cls="cavalry")]
    for u in friendly:
        if "cls" in u:
            u["class"] = u.pop("cls")
    enemy = [unit("e1", "goblin_spearmen", -20, -400), unit("e2", "orc_boyz", 20, -400),
             unit("e5", "orc_arrer_boyz", 0, -450, cls="missile"),
             unit("e6", "goblin_wolf_riders_0", 60, -380, cls="cavalry")]
    for u in enemy:
        if "cls" in u:
            u["class"] = u.pop("cls")
    return {"time_ms": 1000, "friendly": friendly, "enemy": enemy}


def test_line_team_opens_with_guard_mode_posts_and_skirmish_off_then_counter_charges():
    obs = _line_battle()
    policy = LineTeam()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    by_unit = {}
    for order in orders:
        by_unit.setdefault(order["unit"], []).append(order)
    assert {o["behaviour"] for o in by_unit["f2"] + by_unit["f3"] + by_unit["f4"]} == {"defend"}
    assert [o for o in by_unit["f5"] if o["type"] == "behaviour"][0]["enabled"] is False
    gun_post = next(o for o in by_unit["f5"] if o["type"] == "move")
    assert gun_post["z"] > 20  # behind the line, away from the enemy
    knights_post = next(o for o in by_unit["f7"] if o["type"] == "move")
    assert knights_post["z"] > gun_post["z"]
    assert all(o["type"] != "attack" for o in orders)
    # The wolves come within 120 m of the knights: counter-charge, kept until they rout.
    obs["enemy"][3].update(x=60, z=-60)
    obs["time_ms"] = 60000
    for u in obs["friendly"]:
        u["state"] = ["idle"]
    orders = policy.decide(obs)
    charge = next(o for o in orders if o["unit"] == "f7")
    assert charge["type"] == "attack" and charge["target"] == "e6"
    # The guns shoot the cavalry first when it is in range.
    shots = [o for o in orders if o["unit"] in ("f5", "f6") and o["type"] == "attack"]
    assert shots and all(o["target"] == "e6" and o["mode"] == "ranged" for o in shots)
    # Cavalry gone: the knights go for the archers.
    obs["enemy"].pop(3)
    obs["time_ms"] = 120000
    orders = policy.decide(obs)
    assert next(o for o in orders if o["unit"] == "f7")["target"] == "e5"
    # A rallied rider remnant 124 m away does not take the archers target away (b44/b45:
    # the knights alternated targets and were recalled mid-melee in all six launches).
    obs["enemy"].append(unit("e7", "goblin_wolf_riders_1", 40, -84, cls="cavalry"))
    obs["enemy"][-1]["class"] = obs["enemy"][-1].pop("cls")
    obs["time_ms"] = 124000
    assert next(o for o in policy.decide(obs) if o["unit"] == "f7")["target"] == "e5"
    # The archers rout under the charge: the knights finish that melee, then ride back.
    obs["enemy"].pop(2)
    obs["friendly"][6]["state"] = ["melee"]
    obs["time_ms"] = 128000
    assert not [o for o in policy.decide(obs) if o["unit"] == "f7"]
    obs["friendly"][6]["state"] = ["idle"]
    obs["time_ms"] = 132000
    assert next(o for o in policy.decide(obs) if o["unit"] == "f7")["type"] == "move"


def test_line_team_guns_and_reserve_keep_a_target_while_it_stays_in_their_set():
    obs = _line_battle()
    policy = LineTeam()
    policy.decide(obs)
    for u in obs["friendly"]:
        u["state"] = ["idle"]

    def target(unit_id):
        return next(o for o in policy.decide(obs)
                    if o["unit"] == unit_id and o["type"] == "attack")["target"]
    # Two infantry units in range of the left gun, the goblins a little nearer: the gun
    # shoots them, and keeps shooting them when the Boyz edge nearer (b44: 8-46 target
    # changes a battle between near-equidistant enemies), until the goblins leave range.
    obs["enemy"][0].update(x=-20, z=-100)
    obs["enemy"][1].update(x=20, z=-100)
    obs["time_ms"] = 60000
    assert target("f5") == "e1"
    obs["enemy"][1].update(x=-20, z=-95)
    obs["time_ms"] = 64000
    assert target("f5") == "e1"
    obs["enemy"][0].update(z=-200)
    obs["time_ms"] = 68000
    assert target("f5") == "e2"
    # The reserve's base rule keeps its close infantry target the same way.
    obs["enemy"][0].update(x=10, z=34)
    obs["enemy"][1].update(x=-10, z=35)
    obs["time_ms"] = 72000
    assert target("f1") == "e1"
    obs["enemy"][1].update(x=-8, z=33)
    obs["time_ms"] = 76000
    assert target("f1") == "e1"


def test_line_team_reserve_replaces_the_first_broken_line_unit():
    obs = _line_battle()
    fixed, reserve = LineTeam(), LineTeamReserve()
    fixed.decide(obs)
    reserve.decide(obs)
    obs["time_ms"] = 200000
    obs["enemy"][1].update(x=-30, z=-10, state=["melee"])  # Boyz on the left Swordsmen
    obs["friendly"][1].update(state=["routing"])
    for u in obs["friendly"]:
        if u["id"] != "f2":
            u["state"] = ["idle"]
    fixed_orders = fixed.decide(obs)
    reserve_orders = reserve.decide(obs)
    validate_orders(reserve_orders, obs)
    assert all(o["type"] != "attack" for o in fixed_orders if o["unit"] == "f1")
    fill = next(o for o in reserve_orders if o["unit"] == "f1" and o["type"] != "behaviour")
    assert fill["type"] == "attack" and fill["target"] == "e2"
    assert reserve.metadata()["gaps"][0]["unit"] == "f2"
    # The Boyz rout while the Swordsmen are still gone: the next infantry unit nearest the
    # gap. Once the Swordsmen are back and that target is gone too, the reserve waits again.
    obs["time_ms"] = 230000
    obs["enemy"][1]["state"] = ["routing"]
    assert next(o for o in reserve.decide(obs)
                if o["unit"] == "f1" and o["type"] == "attack")["target"] == "e1"
    obs["time_ms"] = 260000
    obs["friendly"][1]["state"] = ["idle"]
    obs["enemy"][0]["state"] = ["routing"]
    assert all(o["type"] != "attack" for o in reserve.decide(obs) if o["unit"] == "f1")
    assert reserve.metadata()["gaps"] == [{"unit": "f2", "at": 200.0}]


def test_line_team_reserve_measures_the_next_target_from_the_latest_gap():
    obs = _line_battle()
    obs["enemy"].append(unit("e3", "orc_boyz_1", 30, -12))
    obs["enemy"][0].update(x=-30, z=-10)
    obs["enemy"][1].update(x=30, z=-10)
    reserve = LineTeamReserve()
    reserve.decide(obs)
    obs["time_ms"] = 200000
    for u in obs["friendly"]:
        u["state"] = ["idle"]
    obs["friendly"][3]["state"] = ["routing"]  # the Halberdiers on the right break first
    reserve.decide(obs)
    obs["time_ms"] = 210000
    obs["friendly"][1]["state"] = ["routing"]  # then the left Swordsmen
    obs["enemy"][1]["state"] = ["routing"]  # and the reserve's target routs
    fill = next(o for o in reserve.decide(obs) if o["unit"] == "f1" and o["type"] == "attack")
    assert fill["target"] == "e1"  # nearest the left gap, the latest one, not the right
