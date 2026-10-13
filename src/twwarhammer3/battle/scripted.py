"""Scripted battle policies: the no-model round trip and the fixed baselines.

Each policy has ``decide(observation) -> orders``, ``acknowledge(ack, latency)`` and
``metadata() -> dict`` (recorded with every decision).
"""

import math

from twwarhammer3.protocol import friendly_units, visible_enemies


class Hold:
    """Never issues an order: the game AI's opponent fights a standing army."""

    def decide(self, observation: dict) -> list[dict]:
        return []

    def acknowledge(self, ack: dict, latency: dict) -> None:
        pass

    def metadata(self) -> dict:
        return {"type": "hold"}


class AttackNearest:
    """Every able unit attacks its nearest visible enemy.

    An order repeats on a new nearest enemy, or when the engine dropped the old one (the
    unit shows no target, or idle): attacks end when the target dies or leaves sight.
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
            nearest = min(enemies.values(), key=lambda enemy: _distance(unit, enemy))
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


class ProbeMove:
    """Milestone 3: move the first unit east, then north, then halt, to pin the axes."""

    STEPS = (("x", 60.0), ("z", 60.0), None)

    def __init__(self):
        self.step = 0

    def decide(self, observation: dict) -> list[dict]:
        units = friendly_units(observation)
        if self.step >= len(self.STEPS) or not units:
            return []
        unit_id, unit = next(iter(units.items()))
        move = self.STEPS[self.step]
        if move is None:
            return [{"unit": unit_id, "type": "halt"}]
        axis, distance = move
        target = {"x": unit["x"], "z": unit["z"], axis: unit[axis] + distance}
        return [{"unit": unit_id, "type": "move", "x": target["x"], "z": target["z"], "run": True}]

    def acknowledge(self, ack: dict, latency: dict) -> None:
        self.step += 1

    def metadata(self) -> dict:
        return {"type": "probe_move", "step": self.step}


def _distance(a: dict, b: dict) -> float:
    if None in (a.get("x"), a.get("z"), b.get("x"), b.get("z")):
        return math.inf
    return math.hypot(a["x"] - b["x"], a["z"] - b["z"])


POLICIES = {"hold": Hold, "attack_nearest": AttackNearest, "probe_move": ProbeMove}
