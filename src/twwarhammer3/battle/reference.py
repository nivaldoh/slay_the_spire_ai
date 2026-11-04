"""A scripted coordinated reference for the suite: gather, pick one enemy, hit it together.

It reads only the public view, and it knows no scenario. It exists to show whether a battle
can be won by the coordination the battle asks for, and whether the suite's coordination
readings rise when an army really does concentrate; it is not a model of good play.
"""

from statistics import mean

from twwarhammer3.battle.scripted import distance
from twwarhammer3.battle.skills import CHARGERS, OUT, SHOOTERS
from twwarhammer3.protocol import friendly_units, visible_enemies

# JUDGEMENT: Concentrate limits — Claude, 2026-11-04, overnight goal: gather while any unit is
# over 120 m from the army's centre and no enemy is within 80 m of a unit; fast units join when
# something is in melee. Other distances change when the army commits, so what this script wins
# or loses, and any scenario called winnable because of it, rests on these values.
GATHER_M = 120
CLOSE_M = 80


def able(unit):
    return unit.get("men", 0) > 0 and not OUT & set(unit.get("state") or [])


class Concentrate:
    """Keep the army together until the enemy is close, then attack one enemy at a time."""

    def __init__(self):
        self.target = None
        self.sent = {}
        self.gathering = True

    def send(self, unit, order):
        """An order only when it changes, or when the engine dropped the last one."""
        states = set(unit.get("state") or [])
        key = (order["type"], order.get("target"), order.get("x"), order.get("z"))
        if self.sent.get(unit["id"]) == key and not (
                order["type"] == "attack" and (not unit.get("target") or "idle" in states)):
            return []
        self.sent[unit["id"]] = key
        return [order]

    def decide(self, observation):
        units = [unit for unit in friendly_units(observation).values() if able(unit)]
        enemies = {key: enemy for key, enemy in visible_enemies(observation).items()
                   if able(enemy)}
        if not units:
            return []
        centre = {"x": mean(unit["x"] for unit in units), "z": mean(unit["z"] for unit in units)}
        close = any(distance(unit, enemy) <= CLOSE_M for unit in units
                    for enemy in enemies.values())
        apart = max(distance(unit, centre) for unit in units) > GATHER_M
        self.gathering = apart and not close
        if self.gathering:
            spot = {"x": round(centre["x"]), "z": round(centre["z"])}
            return [order for unit in units for order in self.send(unit, {
                "unit": unit["id"], "type": "move", **spot, "facing": None, "width": None,
                "run": True, "queue": False})]
        if not enemies:
            return []
        if self.target not in enemies:
            self.target = min(enemies, key=lambda key: distance(enemies[key], centre))
        contact = any("melee" in (unit.get("state") or []) for unit in units)
        orders = []
        for unit in units:
            fast = unit.get("class") in CHARGERS
            if fast and not contact:
                continue  # the fast units arrive once the line has fixed the enemy
            orders += self.send(unit, {
                "unit": unit["id"], "type": "attack", "target": self.target,
                "mode": "ranged" if unit.get("class") in SHOOTERS and unit.get("ammo") else "auto",
                "run": fast or distance(unit, enemies[self.target]) <= CLOSE_M, "queue": False})
        return orders

    def acknowledge(self, ack, latency):
        for result in ack.get("results", []):
            if not result.get("ok"):
                self.sent.pop(result.get("unit"), None)

    def metadata(self):
        return {"type": "concentrate", "target": self.target, "gathering": self.gathering}
