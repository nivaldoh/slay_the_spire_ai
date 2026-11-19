"""Scripted battle policies: the no-model round trip and the fixed baselines.

Each policy has ``decide(observation) -> orders``, ``acknowledge(ack, latency)`` and
``metadata() -> dict`` (recorded with every decision).
"""

from twwarhammer3.protocol import friendly_units, visible_enemies
from twwarhammer3.units import distance


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
            nearest = min(enemies.values(), key=lambda enemy: distance(unit, enemy))
            lapsed = not unit.get("target") or "idle" in states
            if lapsed or self.targets.get(unit_id) != nearest["id"]:
                self.targets[unit_id] = nearest["id"]
                orders.append({"unit": unit_id, "type": "attack", "target": nearest["id"],
                               "run": False})
        return orders

    def acknowledge(self, ack: dict, latency: dict) -> None:
        forget_refused(self.targets, ack)

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


def forget_refused(sent: dict, ack: dict) -> None:
    """Drop from ``sent`` each unit whose order the engine refused, so it is sent again."""
    for result in ack.get("results", []):
        if not result.get("ok"):
            sent.pop(result.get("unit"), None)


POLICIES = {"hold": Hold, "attack_nearest": AttackNearest, "rush_nearest": RushNearest}
