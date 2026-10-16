"""Small, disclosed tactical diagnostics for calibration, not general benchmark policies.

Select by dotted class name, e.g. ``twwarhammer3.battle.calibration:CentralDefence``.
They use only public observations and the existing executors. Each tests one named
hypothesis; failures of its simple geometry/timing are not evidence of impossibility.
"""

import math

from twwarhammer3.battle.scripted import RushNearest, distance
from twwarhammer3.battle.skills import OUT, SHOOTERS, Skills
from twwarhammer3.protocol import friendly_units, visible_enemies


def _centre(units: list[dict]) -> dict:
    return {axis: sum(unit[axis] for unit in units) / len(units) for axis in ("x", "z")}


class CentralDefence(Skills):
    """Gather at the owned victory point nearest the initial garrison's centre.

    Place a short melee line toward visible enemies, shooters behind it and the lord
    behind the centre. Skills hold these posts and choose local targets. No towers,
    spells, path search or adaptation to a lost point: deliberately a simple fallback.
    """

    card = {"purpose": "Does a simple central fallback solve the siege anchor?",
            "knowledge": "Assumes a defensive garrison and public owned victory points; "
                         "35 m spacing, melee 30 m forward, shooters 15 m behind, "
                         "lord 25 m behind. "
                         "Uses the existing Skills targeting rules; no builds or abilities."}

    def __init__(self):
        super().__init__()
        self.point = None

    def decide(self, observation: dict) -> list[dict]:
        units = [unit for unit in friendly_units(observation).values()
                 if unit.get("men") and unit.get("x") is not None and unit.get("z") is not None]
        points = [point for point in (observation.get("mode") or {}).get("capture_points", [])
                  if point.get("victory") and point.get("holder") == "us"]
        if self.point is None and units and points:
            centre = _centre(units)
            self.point = dict(min(points, key=lambda point: distance(centre, point)))
            enemies = [enemy for enemy in visible_enemies(observation).values()
                       if enemy.get("x") is not None and enemy.get("z") is not None]
            toward = _centre(enemies) if enemies else centre
            dx, dz = toward["x"] - self.point["x"], toward["z"] - self.point["z"]
            length = math.hypot(dx, dz)
            dx, dz = (dx / length, dz / length) if length else (0, -1)
            ranks = {"lord": [], "shoot": [], "hold": []}
            for unit in units:
                role = "lord" if unit.get("commander") else (
                    "shoot" if unit.get("class") in SHOOTERS and unit.get("ammo") else "hold")
                ranks[role].append(unit)
            for role, rank in ranks.items():
                forward = {"lord": -25, "shoot": -15, "hold": 30}[role]
                for index, unit in enumerate(sorted(rank, key=lambda unit: unit["id"])):
                    across = (index - (len(rank) - 1) / 2) * 35
                    self.assign(unit, {"skill": "shoot" if role == "shoot" else "hold",
                        "x": self.point["x"] + dx * forward - dz * across,
                        "z": self.point["z"] + dz * forward + dx * across},
                        observation.get("time_ms", 0) / 1000)
        return super().decide(observation)

    def metadata(self) -> dict:
        return {**super().metadata(), "diagnostic": "central_defence", "point": self.point}


class CoordinatedRush(RushNearest):
    """Rush-nearest, with the Doomwheel and Rat Ogres following behind the infantry.

    Follow 25 m behind the slave/clanrat centre until any screen unit enters melee.
    Release is one-way; everything else is run-nearest, without abilities. This uses
    observed screen movement because straight-line speed estimates failed in the first
    live diagnostic: the Doomwheel arrived 45 s before the screen.
    """

    card = {"purpose": "Does following the infantry protect the swarm's first mobile commitment?",
            "knowledge": "Skavenslaves (excluding slingers) and Clanrats are the screen; "
                         "Rat Ogres and Doomwheel follow 25 m behind its centre, 30 m apart. "
                         "They attack after observed screen contact; "
                         "no path prediction or abilities."}

    def __init__(self):
        super().__init__()
        self.released = {}
        self.waiting = set()
        self.posts = {}

    def decide(self, observation: dict) -> list[dict]:
        units = [unit for unit in friendly_units(observation).values()
                 if unit.get("men") and not OUT.intersection(unit.get("state", []))]
        enemies = [unit for unit in visible_enemies(observation).values()
                   if unit.get("x") is not None and unit.get("z") is not None]
        screen = [unit for unit in units if unit.get("x") is not None
                  and unit.get("z") is not None and ("clanrats" in unit.get("type", "") or
                  ("skavenslaves" in unit.get("type", "") and "slingers" not in unit["type"]))]
        contact = any("melee" in unit.get("state", []) for unit in screen)
        waiting = []
        for unit in units:
            if not any(kind in unit.get("type", "") for kind in ("rat_ogres", "doomwheel")):
                continue
            if unit["id"] in self.released:
                continue
            if contact or not screen:
                self.released[unit["id"]] = observation.get("time_ms", 0) / 1000
            else:
                waiting.append(unit)
        waiting_ids = {unit["id"] for unit in waiting}
        orders = [order for order in super().decide(observation)
                  if order["unit"] not in waiting_ids]
        if waiting and enemies:
            centre, enemy = _centre(screen), _centre(enemies)
            dx, dz = enemy["x"] - centre["x"], enemy["z"] - centre["z"]
            length = math.hypot(dx, dz)
            dx, dz = (dx / length, dz / length) if length else (0, 1)
            for index, unit in enumerate(sorted(waiting, key=lambda unit: unit["id"])):
                across = (index - (len(waiting) - 1) / 2) * 30
                post = {"x": centre["x"] - dx * 25 - dz * across,
                        "z": centre["z"] - dz * 25 + dx * across}
                # Moving posts need not interrupt a path for every metre of screen travel.
                if distance(post, self.posts.get(unit["id"], {})) >= 20:
                    orders.append({"unit": unit["id"], "type": "move", "run": True, **post})
                    self.posts[unit["id"]] = post
        else:
            orders += [{"unit": uid, "type": "halt"}
                       for uid in sorted(waiting_ids - self.waiting)]
        self.waiting = waiting_ids
        return orders

    def metadata(self) -> dict:
        return {"type": "coordinated_rush", "waiting": sorted(self.waiting),
                "released_s": dict(self.released), "gate": "observed_screen_contact"}
