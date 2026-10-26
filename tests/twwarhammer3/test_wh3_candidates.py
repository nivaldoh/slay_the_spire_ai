"""The checkpoint-RL candidate set and orderings (checkpoint-rl-plan.md, decision 3)."""
import copy
import itertools

import pytest

from twwarhammer3.battle import candidates as cand
from twwarhammer3.protocol import validate_orders

BOUNDS = {"min_x": -512, "max_x": 512, "min_z": -512, "max_z": 512}


def context(**changes):
    """Spearmen f1 and handgunners f2 against one visible orc unit e1, 30 m from f2."""
    value = {
        "phase": "Deployed", "time_ms": 120100, "terrain": {"bounds": dict(BOUNDS)},
        "friendly": [
            {"id": "f1", "class": "infantry", "range": 0, "ammo": 0, "men": 90, "x": 0, "z": 0,
             "state": ["idle"]},
            {"id": "f2", "class": "missile", "range": 145, "ammo": 900, "men": 68, "x": 10,
             "z": 0, "state": ["idle"]}],
        "enemy": [{"id": "e1", "class": "infantry", "men": 80, "x": 40, "z": 0, "state": []}],
        "enemy_roster": [{"id": "e1", "type": "wh_main_grn_inf_savage_orcs"}],
    }
    value.update(changes)
    return value


def triples(listed):
    return [(c["id"], c["description"], c["orders"]) for c in listed["candidates"]]


def test_an_ordinary_context_gives_the_five_templates_in_order():
    assert triples(cand.candidates(context())) == [
        ("noop", "no new orders", []),
        ("attack_nearest", "f1 attack e1 walking; f2 attack e1 walking",
         [{"unit": "f1", "type": "attack", "target": "e1", "run": False},
          {"unit": "f2", "type": "attack", "target": "e1", "run": False}]),
        ("rush_nearest", "f1 attack e1 running; f2 attack e1 running",
         [{"unit": "f1", "type": "attack", "target": "e1", "run": True},
          {"unit": "f2", "type": "attack", "target": "e1", "run": True}]),
        ("fall_back_f2", "f2 move to x -50 z 0 walking",
         [{"unit": "f2", "type": "move", "x": -50.0, "z": 0.0, "run": False}]),
        ("charge_f1", "f1 attack e1 running",
         [{"unit": "f1", "type": "attack", "target": "e1", "run": True}]),
    ]


def test_a_later_template_equal_to_an_earlier_one_is_dropped_and_recorded():
    routing = context()
    routing["friendly"][1]["state"] = ["routing"]
    listed = cand.candidates(routing)
    assert [c["id"] for c in listed["candidates"]] == [
        "noop", "attack_nearest", "rush_nearest", "fall_back_f2"]
    assert listed["dropped"] == [{"id": "charge_f1", "duplicate_of": "rush_nearest"}]


def test_candidates_are_pure_valid_and_read_public_fields_only():
    base = cand.candidates(context())
    assert cand.candidates(context()) == base
    hidden = context(evaluation={"enemy": "sentinel"}, final={"x": 1}, setup={"y": 2}, job="j",
                     battle="b", seq=9, orders={"request": "r"})
    hidden["friendly"][0].update(dest=[1, 2], attack_mode="melee", command_queue=[{"x": 1}])
    hidden["enemy_roster"].append({"id": "e2", "type": "unseen", "dead": True})
    assert cand.candidates(hidden) == base
    moved = context()
    moved["enemy"][0]["z"] = 30
    assert cand.candidates(moved)["mapping"] != base["mapping"]
    for c in base["candidates"]:
        validate_orders(c["orders"], context())
    assert len({str(c["orders"]) for c in base["candidates"]}) == len(base["candidates"])


def test_a_fall_back_point_is_clamped_inside_the_public_bounds():
    edge = context()
    edge["friendly"][1]["x"], edge["enemy"][0]["x"] = 500, 530
    order = next(c for c in cand.candidates(edge)["candidates"]
                 if c["id"] == "fall_back_f2")["orders"][0]
    assert order["x"] == 440.0
    edge["friendly"][1]["x"], edge["enemy"][0]["x"] = -500, -470
    order = next(c for c in cand.candidates(edge)["candidates"]
                 if c["id"] == "fall_back_f2")["orders"][0]
    assert order["x"] == -512


def test_equal_descriptions_are_refused(monkeypatch):
    monkeypatch.setattr(cand, "describe", lambda batch: "same")
    with pytest.raises(ValueError, match="share a description"):
        cand.candidates(context())


def test_slot_to_candidate_and_its_index_mistake_differ_on_a_cycle():
    p = [1, 2, 3, 4, 0]
    assert [cand.slot_to_candidate(p, k) for k in range(5)] == [1, 2, 3, 4, 0]
    assert [p.index(k) for k in range(5)] == [4, 0, 1, 2, 3]


def test_evaluation_orderings_are_distinct_seeded_and_never_drawn_for_training():
    three = cand.evaluation_orderings(3, "task")
    assert len(three) == 3 and len({tuple(p) for p in three}) == 3
    assert three == cand.evaluation_orderings(3, "task") != cand.evaluation_orderings(3, "other")
    five = cand.evaluation_orderings(5, "task")
    assert len({tuple(p) for p in five}) == 8
    drawn = [p for update in range(30)
             for p in cand.training_orderings(3, "task", update, 4, three)]
    assert all(p not in three for p in drawn)
    assert {tuple(p) for p in drawn} == {p for p in itertools.permutations(range(3))
                                        if list(p) not in three}
    assert copy.deepcopy(drawn[:4]) == cand.training_orderings(3, "task", 0, 4, three)
    with pytest.raises(ValueError):
        cand.evaluation_orderings(1, "task")
