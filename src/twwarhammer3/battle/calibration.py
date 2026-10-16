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


class CasterSkirmish(Skills):
    """Keep escorts at their opening posts while Kairos flies out to cast and returns.

    Use ordinary Blue Fire (artillery first), or ordinary Firestorm on a group of at
    least three visible units within 30 m. Return during cooldowns or to recover a low
    barrier. This is a fixed spell-selection diagnostic, without melee orders for Kairos.
    """

    BLUE_FIRE = "wh3_main_spell_tzeentch_blue_fire_of_tzeentch"
    FIRESTORM = "wh3_main_spell_tzeentch_tzeentchs_firestorm"
    card = {"purpose": "Can simple airborne cast-and-retreat solve the caster anchor?",
            "knowledge": "Kairos uses Blue Fire (artillery first) and Firestorm on 3+ units "
                         "within 30 m. Escorts hold their starting posts. Return home during "
                         "cooldowns or below 25% barrier, resuming at 80%. Allow 5 s after "
                         "each cast command before moving; an issue does not prove a hit. "
                         "Approach to 80% of spell range; cast within 95%."}

    def __init__(self):
        super().__init__()
        self.home = None
        self.recovering = False
        self.last_cast_s = -math.inf
        self.last_move = None
        self.stage = "opening"

    def decide(self, observation: dict) -> list[dict]:
        units = friendly_units(observation)
        lord = next((u for u in units.values() if "kairos" in u.get("type", "")), None)
        now = observation.get("time_ms", 0) / 1000
        if self.home is None and lord and lord.get("x") is not None:
            self.home = {axis: lord[axis] for axis in ("x", "z")}
            for unit in units.values():
                if unit["id"] != lord["id"] and unit.get("x") is not None:
                    self.assign(unit, {"skill": "shoot" if unit.get("ammo") else "hold",
                                       "x": unit["x"], "z": unit["z"]}, now)
        escorts = {**observation, "friendly": [u for u in units.values() if u is not lord]}
        orders = super().decide(escorts)
        if (not lord or not lord.get("men") or self.home is None
                or OUT.intersection(lord.get("state", []))):
            self.stage = "caster unavailable"
            return orders
        if not lord.get("flying"):
            self.stage = "take off"
            if (lord.get("flight") or {}).get("can_toggle"):
                orders.append({"unit": lord["id"], "type": "flight", "flying": True})
            return orders
        barrier = lord["barrier"]
        fraction = barrier["hp"] / barrier["max_hp"]
        if fraction <= .25:
            self.recovering = True
        elif fraction >= .8:
            self.recovering = False
        if now - self.last_cast_s < 5 and not self.recovering:
            self.stage = "allow cast to execute"
            return orders
        enemies = [u for u in visible_enemies(observation).values()
                   if u.get("men") and u.get("x") is not None and u.get("z") is not None
                   and not OUT.intersection(u.get("state", []))]
        magic = (observation.get("magic") or {}).get("current", 0)
        ready = {a["key"]: a for a in lord.get("abilities", [])
                 if a.get("ready") and a.get("can_use") is not False
                 and a.get("mana", 0) <= magic}
        spell, target = None, None
        if enemies and not self.recovering:
            cluster = max(enemies, key=lambda u: sum(distance(u, e) <= 30 for e in enemies))
            if self.FIRESTORM in ready and sum(distance(cluster, e) <= 30 for e in enemies) >= 3:
                spell, target = ready[self.FIRESTORM], cluster
            elif self.BLUE_FIRE in ready:
                spell = ready[self.BLUE_FIRE]
                target = min(enemies, key=lambda u: (u.get("class") != "artillery",
                                                     distance(lord, u)))
        goal = self.home
        self.stage = "recover barrier" if self.recovering else "return during cooldown"
        if spell:
            if distance(lord, target) <= spell["cast_range"] * .95:
                order = {"unit": lord["id"], "type": "ability", "ability": spell["key"]}
                if spell["key"] == self.FIRESTORM:
                    order.update(x=target["x"], z=target["z"])
                else:
                    order["target"] = target["id"]
                orders += [{"unit": lord["id"], "type": "halt"}, order]
                self.last_cast_s, self.last_move, self.stage = now, None, "cast " + spell["key"]
                return orders
            dx, dz = self.home["x"] - target["x"], self.home["z"] - target["z"]
            length = math.hypot(dx, dz)
            dx, dz = (dx / length, dz / length) if length else (0, -1)
            radius = spell["cast_range"] * .8
            goal = {"x": target["x"] + dx * radius, "z": target["z"] + dz * radius}
            self.stage = "approach for " + spell["key"]
        if goal and distance(lord, goal) <= 10:
            if lord.get("dest") and math.dist(lord["dest"], (goal["x"], goal["z"])) > 10:
                orders.append({"unit": lord["id"], "type": "halt"})
                self.last_move = None
        elif goal and (
                distance(goal, self.last_move or {}) >= 20
                or ("idle" in lord.get("state", [])
                    and now - (self.last_move or {}).get("time_s", -math.inf) >= 2)):
            orders.append({"unit": lord["id"], "type": "move", "run": True, **goal})
            self.last_move = {**goal, "time_s": now}
        return orders

    def metadata(self) -> dict:
        return {"type": "caster_skirmish", "stage": self.stage,
                "recovering": self.recovering,
                "last_cast_s": self.last_cast_s if math.isfinite(self.last_cast_s) else None}
