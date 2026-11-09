"""The camp attack's evaluator readings (camp_readings.py).

Public observations are test_wh3_camp.py's: every unit record from the battle Lua's own
unit_record, starting at the declared placements of emp-chd-camp-v1. Trace rows come from running
an arm's decide and acknowledge on those observations, written in the shape of play's
trace.jsonl rows (an observation, decision and ack row per batch); the kept-cover test adds one
batch by hand, since these units list no behaviours to validate. Private-record rows come from
the battle Lua's own private_unit on stub units, in the frames capture.copy_private_record
documents. Offline only: no game has run the camp, so nothing here shows what a battle reads.
"""

import json
from copy import deepcopy

import wh3_lua
from test_wh3_camp import (
    ENEMY,
    FRIENDLY,
    IDS,
    MEN,
    MOUNTED,
    START,
    at,
    battle,
    cue,
    no_cue,
    opening,
)
from wh3_lua import load_battle

from twwarhammer3.battle import camp, camp_readings, play
from twwarhammer3.protocol import validate_orders

LUA = wh3_lua.runtime()
LUA.execute("""
    function place(x, z)
        return {get_x = function() return x end, get_y = function() return 0 end,
                get_z = function() return z end}
    end
    -- A unit that answers only the getters it names, as on an engine without the others.
    function fake_unit(values)
        return setmetatable({}, {__index = function(_, method)
            local value = values[method]
            if value == nil then return nil end
            return function() return value end
        end})
    end
""")
*_, PRIVATE_UNIT = load_battle(LUA, "get", "round", "position_fields", "private_unit")
CODEC = LUA.execute((wh3_lua.MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())


def private_row(label, x, z, *, men, routing, melee, ammo):
    """The battle Lua's private_unit record for a stub unit; ``ammo`` None gives a unit without
    ammunition getters."""
    values = {"type": START[label]["type"], "position": LUA.globals().place(x, z),
              "number_of_men_alive": men, "is_routing": routing, "is_shattered": False,
              "is_in_melee": melee, "is_hidden": False}
    if ammo is not None:
        values.update(ammo_left=ammo, starting_ammo=25)
    unit = LUA.globals().fake_unit(LUA.table_from(values))
    return json.loads(CODEC.encode(PRIVATE_UNIT(IDS[label], unit, None)))


def private(seconds, changes, terminal=None):
    """One private-record frame per engine second in ``seconds``: each unit at its declared
    start with all its men (a war machine with 25 shots) unless ``changes(t)`` (label -> x, z,
    men, routing, melee, ammo; None for a unit with no row) says otherwise. The frame at
    ``terminal`` is the battle's last."""
    frames = []
    for t in seconds:
        moved, frame = changes(t), {"private_record": 1, "job": "camp-check", "battle": "b1",
                                    "time_ms": t * 1000, "friendly": [], "enemy": [],
                                    "sample_cpu_ms": 0.4}
        for label in FRIENDLY + ENEMY:
            change, place = moved.get(label, {}), START[label]
            if change is None:
                continue
            frame["friendly" if label in FRIENDLY else "enemy"].append(private_row(
                label, change.get("x", place["x"]), change.get("z", place["z"]),
                men=change.get("men", MEN[place["type"]]), routing=change.get("routing", False),
                melee=change.get("melee", False),
                ammo=change.get("ammo", 25 if place["type"] in camp.GUNS else None)))
        if t == terminal:
            frame["terminal"] = True
        frames.append(frame)
    return frames


def trace(policy, observations, refused=()):
    """trace.jsonl rows in play's shape for the orders ``policy`` gives on its public view of
    each observation, applied 300 ms after that view; the engine accepts every order except
    those in ``refused``."""
    rows = []
    for number, observation in enumerate(observations, 1):
        view = play.public(deepcopy(observation), {})
        orders = policy.decide(view)
        validate_orders(orders, view)
        request, latency = f"r{number}", {"think_s": 0.0, "roundtrip_s": 0.3, "delay_ms": 300}
        ack = {"request": request, "based_on": view["seq"], "applied_ms": view["time_ms"] + 300,
               "results": [{"index": index, "unit": order["unit"], "ok": order not in refused,
                            "queued": order.get("queue") is True}
                           for index, order in enumerate(orders, 1)]}
        rows += [{"kind": "observation", "observation": view},
                 {"kind": "decision", "seq": view["seq"], "time_ms": view["time_ms"],
                  "request": request, "orders": orders, "behavior": policy.metadata()},
                 {"kind": "ack", "request": request, "ack": ack, "latency": latency}]
        policy.acknowledge(ack, latency)
    return rows


def views(rows):
    return [row["observation"] for row in rows if row["kind"] == "observation"]


def test_lord_before_the_first_gun_reads_a_unit_whose_rows_stop_as_unknown():
    def gun_first(t):  # the west Magma Cannon's last shot at 80 s, the Overseer dead at 100 s
        return {"cannon_west": {"ammo": 0 if t >= 80 else 25 - t // 10},
                "overseer": {"men": 0} if t >= 100 else {}}

    def lord_first(t):  # the Overseer routs at 60 s and rallies at 70 s; a gun routs at 110 s
        return {"overseer": {"routing": 60 <= t < 70}, "cannon_east": {"routing": t >= 110}}

    def stopped(t):  # the Deathshrieker's rows stop at 70 s; Overseer dead 90 s, a gun 100 s
        return {"rockets": None if t >= 70 else {}, "overseer": {"men": 0} if t >= 90 else {},
                "cannon_west": {"men": 0} if t >= 100 else {}}

    def no_ammo(t):  # the east Magma Cannon's rows carry no ammo from 70 s; Overseer dead 90 s
        return {"cannon_east": {"ammo": None} if t >= 70 else {},
                "overseer": {"men": 0} if t >= 90 else {}}

    def tie(t):  # the Overseer and the east Magma Cannon both dead at 80 s
        return {"overseer": {"men": 0}, "cannon_east": {"men": 0}} if t >= 80 else {}

    read = camp_readings.lord_before_guns
    assert read(private(range(1, 121), gun_first, 120)) == {
        "lord_ms": 100000, "gun_ms": 80000, "lord_first": False, "unknown": []}
    assert read(private(range(1, 121), tie, 120)) == {
        "lord_ms": 80000, "gun_ms": 80000, "lord_first": False, "unknown": []}
    # A gun whose ammunition the record no longer reads may be silenced: not known up.
    assert read(private(range(1, 121), no_ammo, 120)) == {
        "lord_ms": 90000, "gun_ms": None, "lord_first": None, "unknown": [IDS["cannon_east"]]}
    frames = private(range(1, 121), lord_first, 120)
    assert read(frames) == {"lord_ms": 60000, "gun_ms": 110000, "lord_first": True,
                            "unknown": []}
    # The record ends at 50 s with no terminal frame: nothing is known to be up after it.
    assert read(frames[:50]) == {
        "lord_ms": None, "gun_ms": None, "lord_first": None,
        "unknown": sorted(IDS[label] for label in ("overseer", "cannon_west", "cannon_east",
                                                    "rockets"))}
    # The named wrong version counts the Deathshrieker silenced at 70 s and reads False.
    assert read(private(range(1, 121), stopped, 120)) == {
        "lord_ms": 90000, "gun_ms": 100000, "lord_first": None, "unknown": [IDS["rockets"]]}


def test_kept_cover_is_measured_from_the_nearest_levy_not_from_its_attacker():
    # CampSupport's mounted group takes the Bull Centaurs at the cue (50 s, applied at 50.3 s).
    # In the record the Bull Centaurs stand 19.2 m from the south Flagellants, and 15 m from the
    # dead Warrior Priest, until 60 s, then ride east at 9 m/s, the four mounted units 15 m
    # behind them, so a reading from the attacker stays at 15 m; they die at 86 s.
    def ride(t):
        x = -135 + 9 * max(0, t - 60)
        changes = {"centaurs": {"x": x, "z": -335, "melee": True, "men": 0 if t >= 86 else 12},
                   "priest": {"x": -120, "z": -335, "men": 0}}
        if t >= 51:
            changes.update(dict.fromkeys(MOUNTED, {"x": x - 15, "z": -335}))
        return changes

    # Applied at 60.3 s: a behaviour order, which keeps the target, a move with a queued attack
    # on the same Bull Centaurs, which keeps it from the batch's applied time, and a halt, which
    # ends the Reiksguard's (rests on JUDGEMENT? camp_readings.py Kept cover distance).
    orders = [{"unit": IDS["knights_a"], "type": "behaviour", "behaviour": "formed_attack",
               "enabled": True},
              {"unit": IDS["knights_b"], "type": "move", "x": -100, "z": -300, "queue": False},
              {"unit": IDS["knights_b"], "type": "attack", "target": IDS["centaurs"],
               "mode": "auto", "run": True, "queue": True},
              {"unit": IDS["reiksguard"], "type": "halt"}]
    rows = trace(camp.CampSupport(), cue())
    after = next(index for index, row in enumerate(rows)
                 if row["kind"] == "observation" and row["observation"]["time_ms"] > 60000)
    rows[after:after] = [
        {"kind": "decision", "request": "extra", "orders": orders},
        {"kind": "ack", "request": "extra", "ack": {"request": "extra", "applied_ms": 60300,
                                                   "results": [{"index": 1, "ok": True},
                                                               {"index": 2, "ok": True},
                                                               {"index": 3, "ok": True},
                                                               {"index": 4, "ok": True}]}}]
    readings = camp_readings.kept_cover_distance(rows, private(range(40, 96), ride))
    assert {identity: [row["time_ms"] for row in kept] for identity, kept in readings.items()} == {
        **{IDS[label]: list(range(51000, 86000, 1000)) for label in MOUNTED},
        IDS["reiksguard"]: list(range(51000, 61000, 1000))}
    knights = readings[IDS["knights_a"]]
    assert {row["target"] for row in knights} == {IDS["centaurs"]}
    assert [row["m"] for row in knights if row["time_ms"] in (51000, 70000, 85000)] == [
        19.2, 105.7, 240.3]


def fire_battle(t):
    """test_wh3_camp's opening (the north Flagellants fight the Cutthroats from 20 s), with the
    north Flagellants also under fire at 30, 50 and 60 s, losing 6 men at 30 s, none at 50 s and
    4 at 60 s; the middle Flagellants under fire out of melee at 40 s, losing 5, and losing 4 at
    50 s without either flag; the Bull Centaurs fighting 19 m from the south Flagellants from
    40 s to 58 s."""
    changes = opening(t, 999)
    changes["flagellants_a"]["men"] = 90 if t < 30 else 84 if t < 60 else 80
    if t in (30, 50, 60):
        changes["flagellants_a"]["flags"] = ("melee", "under_fire")
    changes["flagellants_b"] = {"flags": ("moving", "under_fire") if t == 40 else ("moving",),
                                "men": 90 if t < 40 else 85 if t < 50 else 81}
    if 40 <= t < 60:
        changes["centaurs"] = at(-135, -335, "melee")
    return changes


def test_fire_into_melee_needs_ammunition_spent_melee_fire_and_men_lost_in_one_second():
    # The west Magma Cannon spends a shot at 30, 40 and 50 s, none at 60 s. A reader that counts
    # under_fire without melee adds 40 s; one that needs no men lost, or men lost by any unit,
    # adds 50 s. Levy-cover melee: the Bull Centaurs' 20 s, not the dead Wolf Raiders' 10 s.
    def shots(t):
        changes = {"cannon_west": {"ammo": 25 - (t >= 30) - (t >= 40) - (t >= 50)},
                   "wolves_a": {"melee": True}}  # fighting at its start, far from every levy
        if 40 <= t < 60:
            changes["centaurs"] = {"x": -135, "z": -335, "melee": True}
        if 10 <= t < 20:
            changes["wolves_b"] = {"x": -135, "z": -335, "melee": True, "men": 0}
        return changes

    frames = private(range(1, 65), shots)
    assert camp_readings.melee_fire_seconds(battle(fire_battle, 64), frames) == [
        {"time_ms": 30000, "guns": [IDS["cannon_west"]], "friendly": [IDS["flagellants_a"]]}]
    assert camp_readings.cover_melee_seconds(frames) == 20


def attack(label, target):
    return {"unit": IDS[label], "type": "attack", "target": IDS[target], "mode": "auto",
            "run": True, "queue": False}


def adding(arm, extra):
    """An ``arm`` that also sends ``extra`` (battle ms -> orders) first in its batch then."""
    policy, decide = arm(), arm.decide
    policy.decide = lambda observation: extra.get(observation["time_ms"], []) + decide(
        policy, observation)
    return policy


def test_the_branch_is_the_first_gun_or_cover_attack_after_the_cue_the_reader_finds():
    # The reader's cue is the witness's on both battles: at 50 s, and none in the near misses.
    for observations in (cue(), no_cue()):
        witness = camp.CampStrike()
        rows = trace(witness, observations)
        assert camp_readings.cue_ms(views(rows)) == witness.metadata()["cue_ms"]

    def read(policy, observations, refused=()):
        rows = trace(policy, observations, refused)
        result = camp_readings.branch(rows, views(rows))
        return {key: result.get(key) for key in ("branch", "cue_ms", "start_ms", "target")}

    assert read(camp.CampStrike(), cue()) == {
        "branch": "guns", "cue_ms": 50000, "start_ms": 50000, "target": IDS["cannon_east"]}
    assert read(camp.CampSupport(), cue()) == {
        "branch": "cover", "cue_ms": 50000, "start_ms": 50000, "target": IDS["centaurs"]}
    # A levy's attack on the Bull Centaurs at the cue, sent before the knights', is no branch.
    levy = adding(camp.CampStrike, {50000: [attack("flagellants_c", "centaurs")]})
    assert read(levy, cue())["branch"] == "guns"
    # A knight attack on a gun at 30 s comes before the cue; a reader that takes it reads guns.
    # Without a cue the start is 180 s, after which the mounted group attacks only the
    # Cutthroats, and the engine refuses a knight attack on a gun at 184 s.
    early, late = attack("knights_a", "cannon_east"), attack("knights_a", "cannon_west")
    assert read(adding(camp.CampSupport, {30000: [early]}), cue())["branch"] == "cover"
    assert read(adding(camp.CampSupport, {30000: [early], 184000: [late]}), no_cue(), [late]) == {
        "branch": "neither", "cue_ms": None, "start_ms": 180000, "target": None}
