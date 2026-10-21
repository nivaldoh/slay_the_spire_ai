"""Scripted battle policies: the no-model round trip and the fixed baselines.

Each policy has ``decide(observation) -> orders``, ``acknowledge(ack, latency)`` and
``metadata() -> dict`` (recorded with each logged decision; quiet ones are logged once per
``observe_ms``).
"""

import math

from twwarhammer3.protocol import friendly_units, visible_enemies


class Hold:
    """Never issues an order: the game AI fights an army left on the game's defaults
    (missile units still fire at will and skirmish away by themselves)."""

    def decide(self, observation: dict) -> list[dict]:
        return []

    def acknowledge(self, ack: dict, latency: dict) -> None:
        pass

    def metadata(self) -> dict:
        return {"type": "hold"}


class AttackNearest:
    """Every able unit attacks its nearest visible enemy.

    An order repeats on a new nearest enemy, after a refused order, or when the unit shows
    no target or is idle: attacks end when the target dies or leaves sight, and sometimes
    while it is still in sight.
    """

    def __init__(self):
        self.targets = {}

    def decide(self, observation: dict) -> list[dict]:
        enemies = visible_enemies(observation)
        orders = []
        for unit_id, unit in friendly_units(observation).items():
            states = set(unit.get("state", []))
            if not enemies or unit.get("men") == 0 or {"routing", "shattered"} & states:
                continue
            nearest = min(enemies.values(), key=lambda enemy: distance(unit, enemy))
            lapsed = not unit.get("target") or "idle" in states
            if lapsed or self.targets.get(unit_id) != nearest["id"]:
                self.targets[unit_id] = nearest["id"]
                orders.append({"unit": unit_id, "type": "attack", "target": nearest["id"],
                               "run": False})
        return orders

    def acknowledge(self, ack: dict, latency: dict) -> None:
        for result in ack.get("results", []):
            if not result.get("ok"):
                self.targets.pop(result.get("unit"), None)

    def metadata(self) -> dict:
        return {"type": "attack_nearest"}


class RushNearest(AttackNearest):
    """AttackNearest with running enabled; no flanking, target priorities or abilities."""

    def decide(self, observation: dict) -> list[dict]:
        orders = super().decide(observation)
        for order in orders:
            order["run"] = True
        return orders

    def metadata(self) -> dict:
        return {"type": "rush_nearest"}


def distance(a: dict, b: dict) -> float:
    """Metres between two things with x and z (units, points, orders); inf if one is unplaced."""
    if None in (a.get("x"), a.get("z"), b.get("x"), b.get("z")):
        return math.inf
    return math.hypot(a["x"] - b["x"], a["z"] - b["z"])


POLICIES = {"hold": Hold, "attack_nearest": AttackNearest, "rush_nearest": RushNearest}
