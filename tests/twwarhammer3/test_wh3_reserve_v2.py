"""B's observed outside-route timing failure: release on own arrival, not elapsed guess.

Numerical v2 cases rest on JUDGEMENT src/twwarhammer3/battle/reserve.py
Reserve route completion; proposed procedure in runs/cannae-build/card-b2.md.
"""

from copy import deepcopy

import pytest
from test_wh3_reserve import engine, scenario

from twwarhammer3.battle import reserve, setup


def draw_v2():
    draw = next(d for seed in range(100) if (d := reserve.materialize(scenario(), seed=seed))
                and d["region"] == "outside" and d["count"] == 1)
    return {**draw, "version": 2, "release_ms": 360000, "arrival_m": 25}


def positions(lua, x, z):
    lua.globals().test_x, lua.globals().test_z = x, z
    lua.execute("""
        for _, entry in ipairs(state.reserve.entries) do
            entry.unit.test_x, entry.unit.test_z = test_x, test_z
            function entry.unit:position()
                local u = self
                return {get_x=function() return u.test_x end,
                        get_z=function() return u.test_z end}
            end
        end
    """)


def test_v2_holds_past_old_deadline_then_releases_only_the_arrived_committed_unit():
    draw = draw_v2()
    lua, tick = engine(draw)
    positions(lua, 355, -225)
    tick(draw["trigger_ms"])
    tick(165000)
    controllers = list(lua.globals().controllers.values())[:2]
    assert [c["released"] for c in controllers] == [0, 0]
    final = draw["route"][-1]
    positions(lua, final["x"], final["z"])
    tick(180000)
    assert [c["released"] for c in controllers] == [1, 0]
    evidence = lua.globals().state["reserve"]["evidence"]
    assert evidence["releases"][1]["reason"] == "arrived"
    assert evidence["releases"][1]["released_ms"] == 180000
    assert evidence["releases"][1]["x"] == final["x"]
    assert evidence["releases"][1]["z"] == final["z"]
    tick(draw["release_ms"])
    assert [c["released"] for c in controllers] == [1, 1]
    assert evidence["releases"][2]["reason"] == "deadline"
    assert evidence["released_ms"] == draw["release_ms"]


def test_versioned_profile_changes_only_release_semantics_and_preserves_v1():
    v1 = scenario()
    v2 = setup.scenarios()["emp-envelopment-b-v2"]
    for key in ("player", "enemy", "deployment", "map", "expect"):
        assert v1[key] == v2[key]
    old = reserve.materialize(v1, seed=99)
    new = reserve.materialize(v2, seed=99)
    assert old["release_ms"] == 165000 and "arrival_m" not in old
    assert new["release_ms"] == 360000 and new["arrival_m"] == 25
    for key in ("region", "side", "count", "seed", "route", "trigger_ms"):
        assert old[key] == new[key]


def test_private_sequence_seed_reproduces_each_fresh_draw_without_touching_the_opening():
    v2 = setup.scenarios()["emp-envelopment-b-v2"]
    before = deepcopy(v2)
    first = reserve.sequence(v2, 8, seed=31337)
    assert first == reserve.sequence(v2, 8, seed=31337)
    assert len({draw["seed"] for draw in first}) == 8
    assert first != reserve.sequence(v2, 8, seed=31338)
    assert v2 == before
    for draw in first:
        assert draw == reserve.materialize(v2, seed=int(draw["seed"]))
    with pytest.raises(ValueError, match="nonnegative integer"):
        reserve.sequence(v2, 1, seed=-1)


@pytest.mark.parametrize("offset,released", ((25, True), (25.01, False)))
def test_arrival_uses_actual_engine_position_at_the_declared_region_boundary(offset, released):
    draw = draw_v2()
    lua, tick = engine(draw)
    target = draw["route"][-1]
    positions(lua, target["x"] + offset, target["z"])
    tick(draw["trigger_ms"])
    assert (list(lua.globals().controllers.values())[0]["released"] == 1) is released


def test_accepted_but_ineffective_route_ends_at_the_bound_and_records_the_actual_position():
    draw = draw_v2()
    lua, tick = engine(draw)
    positions(lua, 355, -225)
    tick(draw["trigger_ms"])
    tick(draw["release_ms"])
    evidence = lua.globals().state["reserve"]["evidence"]
    assert len(evidence["orders"]) == draw["count"]
    assert evidence["orders"][1]["ok"] is True
    assert len(evidence["releases"]) == 2
    assert all(r["reason"] == "deadline" and r["x"] == 355 and r["z"] == -225
               for r in evidence["releases"].values())


@pytest.mark.parametrize("condition", ("destroyed", "routing", "shattered", "unreadable"))
def test_unavailable_units_are_released_without_inventing_a_route_effect(condition):
    draw = draw_v2()
    lua, tick = engine(draw)
    lua.globals().condition = condition
    lua.execute("""
        for _, entry in ipairs(state.reserve.entries) do
            function entry.unit:number_of_men_alive()
                if condition == 'destroyed' then return 0 end
                if condition == 'unreadable' then error('read failed') end
                return 90
            end
            function entry.unit:is_routing() return condition == 'routing' end
            function entry.unit:is_shattered() return condition == 'shattered' end
        end
    """)
    tick(draw["trigger_ms"])
    records = list(lua.globals().state["reserve"]["evidence"]["releases"].values())
    assert len(records) == (2 if condition == "unreadable" else draw["count"])
    assert all(r["ok"] is (condition != "unreadable") for r in records)
    assert all(r["reason"] == (None if condition == "unreadable" else condition) for r in records)
    if condition != "unreadable":
        controllers = list(lua.globals().controllers.values())[:2]
        assert controllers[1]["released"] == 0  # the uncommitted unit remains under hold
        tick(draw["release_ms"])
        records = list(lua.globals().state["reserve"]["evidence"]["releases"].values())
        assert len(records) == 2 and records[1]["released_ms"] == draw["release_ms"]
