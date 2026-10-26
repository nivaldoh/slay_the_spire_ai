"""The public candidate set of one checkpoint-RL decision (checkpoint-rl-plan.md, decision 3).

``candidates(context)`` is pure: the same public context gives the same list. Templates are
built in a fixed order; a later template whose batch equals an earlier one is dropped and
recorded. Each candidate has an id, the exact order batch (valid on the context) and a one-line
description made from that batch by ``describe``. The model never sees the canonical order:
a displayed slot maps to a candidate through ``slot_to_candidate`` only.

JUDGEMENT: candidate_set — Claude, 2026-10-25: these v1 templates, fall_back_m 60, the cap
of eight and seeded permutations, versus free-form orders or other templates; competes
with checkpoint-rl.md `candidate_task`. What a win can be attributed to rests on this.
"""
import hashlib
import json
import math
import random

from twwarhammer3.battle.scripted import AttackNearest, RushNearest, distance
from twwarhammer3.protocol import friendly_units, validate_orders, visible_enemies

CANDIDATES_VERSION = 1
FALL_BACK_M = 60
MAX_CANDIDATES = 8
CHARGE_CLASSES = {"infantry", "cavalry", "chariot", "monster", "lord", "hero"}
EVAL_ORDERINGS = 8


def describe(batch: list[dict]) -> str:
    """One public line naming every field of every order."""
    if not batch:
        return "no new orders"
    parts = []
    for order in batch:
        words = [order["unit"], order["type"]]
        if "target" in order:
            words.append(order["target"])
        if "x" in order:
            words.append(f"to x {order['x']:g} z {order['z']:g}")
        words.append("running" if order.get("run") else "walking")
        words += [f"{key} {order[key]}" for key in sorted(order)
                  if key not in ("unit", "type", "target", "x", "z", "run")]
        parts.append(" ".join(words))
    return "; ".join(parts)


def _away(unit: dict, enemy: dict, bounds: dict) -> tuple[float, float]:
    length = distance(unit, enemy) or 1.0
    x = unit["x"] + FALL_BACK_M * (unit["x"] - enemy["x"]) / length
    z = unit["z"] + FALL_BACK_M * (unit["z"] - enemy["z"]) / length
    return (round(min(max(x, bounds["min_x"]), bounds["max_x"]), 1),
            round(min(max(z, bounds["min_z"]), bounds["max_z"]), 1))


def candidates(context: dict) -> dict:
    """{"version", "candidates": [{id, orders, description}], "dropped": [...], "mapping"}."""
    enemies = list(visible_enemies(context).values())
    built = [("noop", []), ("attack_nearest", AttackNearest().decide(context)),
             ("rush_nearest", RushNearest().decide(context))]
    units = list(friendly_units(context).values())
    for unit in units:
        if unit.get("ammo", 0) > 0 and enemies and unit.get("x") is not None:
            nearest = min(enemies, key=lambda enemy: distance(unit, enemy))
            x, z = _away(unit, nearest, context["terrain"]["bounds"])
            built.append((f"fall_back_{unit['id']}",
                          [{"unit": unit["id"], "type": "move", "x": x, "z": z, "run": False}]))
    for unit in units:
        if unit.get("class") in CHARGE_CLASSES and unit.get("range") == 0 and enemies:
            nearest = min(enemies, key=lambda enemy: distance(unit, enemy))
            built.append((f"charge_{unit['id']}", [{"unit": unit["id"], "type": "attack",
                                                    "target": nearest["id"], "run": True}]))
    kept, dropped = [], []
    for name, batch in built:
        twin = next((other for other, orders in kept if orders == batch), None)
        if twin is not None:
            dropped.append({"id": name, "duplicate_of": twin})
        elif len(kept) == MAX_CANDIDATES:
            dropped.append({"id": name, "reason": "cap"})
        else:
            kept.append((name, batch))
    listed = []
    for name, batch in kept:
        validate_orders(batch, context)
        listed.append({"id": name, "orders": batch, "description": describe(batch)})
    if len({c["description"] for c in listed}) != len(listed):
        raise ValueError("two candidates share a description")
    return {"version": CANDIDATES_VERSION, "candidates": listed, "dropped": dropped,
            "mapping": mapping_hash(listed)}


def mapping_hash(listed: list[dict]) -> str:
    text = json.dumps([[c["id"], c["orders"], c["description"]] for c in listed],
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def slot_to_candidate(permutation: list[int], slot: int) -> int:
    """The canonical candidate shown at displayed slot ``slot``: the one mapping everything uses."""
    return permutation[slot]


def evaluation_orderings(n: int, task_hash: str) -> list[list[int]]:
    """A task's evaluation orderings: min(8, n!/2) distinct permutations, seeded by its hash."""
    if n < 2:
        raise ValueError("a decision needs at least two candidates")
    count, rng, drawn = min(EVAL_ORDERINGS, math.factorial(n) // 2), random.Random(
        f"eval:{task_hash}"), []
    while len(drawn) < count:
        permutation = rng.sample(range(n), n)
        if permutation not in drawn:
            drawn.append(permutation)
    return drawn


def training_orderings(n: int, task_hash: str, update: int, count: int,
                       excluded: list[list[int]]) -> list[list[int]]:
    """``count`` fresh permutations for one update, never one of the evaluation orderings."""
    drawn = []
    for k in range(count):
        rng = random.Random(f"train:{task_hash}:{update}:{k}")
        permutation = rng.sample(range(n), n)
        while permutation in excluded:
            permutation = rng.sample(range(n), n)
        drawn.append(permutation)
    return drawn
