"""Small, disclosed tactical diagnostics for calibration, not general benchmark policies.

Select by dotted class name, e.g. ``twwarhammer3.battle.calibration:CentralDefence``.
They use only public observations and the existing executors. Each tests one named
hypothesis; failures of its simple geometry/timing are not evidence of impossibility.
"""

import math

from twwarhammer3.battle.scripted import Hold, RushNearest, distance
from twwarhammer3.battle.skills import OUT, SHOOTERS, Skills
from twwarhammer3.protocol import friendly_units, visible_enemies


def _active(units) -> list[dict]:
    return [unit for unit in units if unit.get("men") and unit.get("x") is not None
            and unit.get("z") is not None and not OUT.intersection(unit.get("state", []))]


def _direction(origin: dict, target: dict) -> tuple[float, float]:
    dx, dz = target["x"] - origin["x"], target["z"] - origin["z"]
    length = math.hypot(dx, dz)
    return (dx / length, dz / length) if length else (0, 1)


def _offset(origin: dict, direction: tuple, forward: float, across: float = 0) -> dict:
    dx, dz = direction
    return {"x": origin["x"] + dx * forward - dz * across,
            "z": origin["z"] + dz * forward + dx * across}


class SmallDiagnostic(Hold):
    """Order bookkeeping shared by the three small public-state diagnostics."""

    def __init__(self):
        self.sent = {}
        self.now = 0
        self.bounds = {}

    def observe(self, observation):
        self.now = observation.get("time_ms", 0) / 1000
        self.bounds = (observation.get("terrain") or {}).get("bounds") or {}
        return (_active(friendly_units(observation).values()),
                _active(visible_enemies(observation).values()))

    def issue(self, unit, order):
        """Keep a moving goal until it changes materially; retry dropped/rejected orders."""
        previous, when = self.sent.get(unit["id"], ({}, -math.inf))
        same = order == previous
        if order["type"] == previous.get("type") == "move":
            same = distance(order, previous) < 15
        if same and (self.now - when < 3 or "idle" not in unit.get("state", [])):
            return []
        self.sent[unit["id"]] = (order, self.now)
        return [order]

    def move(self, unit, point, target):
        point = dict(point)
        for axis in ("x", "z"):
            if f"min_{axis}" in self.bounds and f"max_{axis}" in self.bounds:
                point[axis] = max(self.bounds[f"min_{axis}"] + 30,
                                  min(self.bounds[f"max_{axis}"] - 30, point[axis]))
        if distance(unit, point) < 12:
            return []
        facing = math.degrees(math.atan2(target["x"] - point["x"],
                                        target["z"] - point["z"])) % 360
        return self.issue(unit, {"unit": unit["id"], "type": "move", "run": True,
                                 "facing": facing, **point})

    def attack(self, unit, target, mode="melee"):
        return self.issue(unit, {"unit": unit["id"], "type": "attack", "run": True,
                                 "mode": mode, "target": target["id"]})

    def acknowledge(self, ack, latency):
        for result in ack.get("results", []):
            if not result.get("ok"):
                self.sent.pop(result.get("unit"), None)


class FeintFlank(SmallDiagnostic):
    """S1: approach on opposite sides, charge together, withdraw and swap roles."""

    card = {"purpose": "Can two light cavalry units beat a braced anti-large block?",
            "knowledge": "Disclosed S1 strategy: one rider waits 55 m in front while the "
                         "other goes via a 120 m side waypoint to 80 m behind. Both charge "
                         "when the flanker arrives; withdraw radially 120 m after 6 s of "
                         "observed contact, regroup for at least 12 s and swap roles. "
                         "Only visible positions/states; no hidden targets or path search."}

    def __init__(self):
        super().__init__()
        self.phase = "side"
        self.cycle = 0
        self.axis = None
        self.contact_s = None
        self.withdraw_s = None
        self.retreats = {}

    def decide(self, observation):
        units, enemies = self.observe(observation)
        if not units or not enemies:
            return []
        units.sort(key=lambda unit: unit["id"])
        target = min(enemies, key=lambda enemy: distance(_centre(units), enemy))
        if len(units) < 2:
            return self.attack(units[0], target)
        bait, flanker = units[self.cycle % 2], units[(self.cycle + 1) % 2]
        if self.axis is None:
            self.axis = _direction(target, bait)
        side = _offset(target, self.axis, 0, 120)
        rear = _offset(target, self.axis, -80)
        if self.phase == "side" and distance(flanker, side) < 25:
            self.phase = "rear"
        if self.phase == "rear" and distance(flanker, rear) < 25:
            self.phase = "charge"
            self.contact_s = None
        if self.phase == "charge":
            if any("melee" in unit.get("state", []) for unit in units):
                if self.contact_s is None:
                    self.contact_s = self.now
            if self.contact_s is not None and self.now - self.contact_s >= 6:
                self.phase, self.withdraw_s = "withdraw", self.now
                self.retreats = {unit["id"]: _offset(target, _direction(target, unit), 120)
                                 for unit in units}
        if self.phase == "withdraw":
            if (self.now - self.withdraw_s >= 12
                    and all(distance(unit, target) >= 80 for unit in units)):
                self.cycle += 1
                self.phase, self.axis = "side", None
            return [order for unit in units
                    for order in self.move(unit, self.retreats[unit["id"]], target)]
        if self.phase == "charge":
            return [order for unit in units for order in self.attack(unit, target)]
        front = _offset(target, self.axis, 55)
        return (self.move(bait, front, target)
                + self.move(flanker, side if self.phase == "side" else rear, target))

    def metadata(self):
        return {"type": "feint_flank", "phase": self.phase, "cycles": self.cycle}


class CrossKite(SmallDiagnostic):
    """S2: split horse archers around the target and preserve shooting distance."""

    card = {"purpose": "Can separated horse archers spend their ammunition effectively?",
            "knowledge": "S2: enable skirmish/fire-at-will, split to opposite sides at "
                         "120 m, shoot while at 85-145 m and withdraw radially when closer. "
                         "With no ammunition, charge the remaining visible target. "
                         "Fixed initial approach axis; no hidden state or path search."}

    def __init__(self):
        super().__init__()
        self.axis = None
        self.positioned = set()

    def decide(self, observation):
        units, enemies = self.observe(observation)
        if not units or not enemies:
            return []
        units.sort(key=lambda unit: unit["id"])
        target = min(enemies, key=lambda enemy: distance(_centre(units), enemy))
        if self.axis is None:
            self.axis = _direction(target, _centre(units))
        orders = []
        for index, unit in enumerate(units):
            for key in ("skirmish", "fire_at_will"):
                if unit.get("behaviours", {}).get(key) is False:
                    orders.append({"unit": unit["id"], "type": "behaviour",
                                   "behaviour": key, "enabled": True})
            if not unit.get("ammo"):
                orders += self.attack(unit, target)
                continue
            gap = distance(unit, target)
            post = _offset(target, self.axis, 30, 115 if index % 2 else -115)
            if distance(unit, post) <= 25:
                self.positioned.add(unit["id"])
            if gap < 85:
                orders += self.move(unit, _offset(target, _direction(target, unit), 125), target)
            elif unit["id"] not in self.positioned or gap > 145:
                orders += self.move(unit, post, target)
            else:
                orders += self.attack(unit, target, "ranged")
        return orders

    def metadata(self):
        return {"type": "cross_kite", "positioned": sorted(self.positioned)}


class Bodyguard(SmallDiagnostic):
    """S4: shoot the nearest cavalry and intercept beside the gun."""

    card = {"purpose": "Can a single halberd escort preserve a fragile artillery unit?",
            "knowledge": "S4: the gun shoots cavalry before infantry. Its escort waits "
                         "25 m toward the nearest cavalry and 20 m to the side, intercepts "
                         "within 65 m of the gun, and returns after the threat routes. "
                         "No abilities, hidden targets or predicted paths."}

    def decide(self, observation):
        units, enemies = self.observe(observation)
        if not units or not enemies:
            return []
        gun = next((unit for unit in units if unit.get("class") == "artillery"), None)
        if gun is None:
            return [order for unit in units for order in self.attack(
                unit, min(enemies, key=lambda enemy: distance(unit, enemy)))]
        riders = [enemy for enemy in enemies if "cavalry" in enemy.get("class", "")]
        target = min(riders or enemies, key=lambda enemy: distance(gun, enemy))
        orders = self.attack(gun, target, "ranged" if gun.get("ammo") else "melee")
        for escort in units:
            if escort is gun:
                continue
            if distance(gun, target) < 65:
                orders += self.attack(escort, target)
            else:
                orders += self.move(escort, _offset(gun, _direction(gun, target), 25, 20), target)
        return orders

    def metadata(self):
        return {"type": "bodyguard"}


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
