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
    """Order bookkeeping shared by the small public-state diagnostics."""

    def __init__(self):
        self.sent = {}
        self.routing_at = {}
        self.now = 0
        self.bounds = {}

    def observe(self, observation):
        self.now = observation.get("time_ms", 0) / 1000
        self.bounds = (observation.get("terrain") or {}).get("bounds") or {}
        units = [unit for unit in _active(friendly_units(observation).values())
                 if self.now > self.routing_at.get(unit["id"], -math.inf)]
        return (units,
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
                if result.get("error") == "unit_routing":
                    self.routing_at[result["unit"]] = ack["applied_ms"] / 1000


class FeintFlank(SmallDiagnostic):
    """S1: approach on opposite sides, charge together, withdraw and swap roles."""

    card = {"purpose": "Can two light cavalry units beat a braced anti-large block?",
            "knowledge": "Disclosed S1 strategy: one rider waits 55 m in front while the "
                         "other goes via a 120 m side waypoint to 80 m behind. Both charge "
                         "when the flanker arrives; withdraw radially 120 m after 6 s of "
                         "observed contact, regroup for at least 12 s and swap roles. "
                         "If one rider routs but is not shattered, withdraw the other "
                         "until it rallies instead of charging alone. "
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
            recoverable = [unit for unit in friendly_units(observation).values()
                           if unit.get("men") and "shattered" not in unit.get("state", [])]
            if len(recoverable) >= 2:
                self.phase, self.axis = "rally", None
                return self.move(units[0], _offset(target, _direction(target, units[0]), 140),
                                 target)
            return self.attack(units[0], target)
        if self.phase == "rally":
            self.phase = "side"
            self.contact_s = None
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
            "knowledge": "S4: the gun stays in place and shoots cavalry before infantry "
                         "when in range, keeping one target until it routs or another is 30 m "
                         "nearer the gun. Its escort shares that target and waits "
                         "25 m toward the nearest cavalry and 20 m to the side, intercepts "
                         "within 120 m of the gun, and returns after the threat routes. "
                         "The early intercept allows for roughly 45 m of rider movement "
                         "during five seconds of observation age. "
                         "No abilities, hidden targets or predicted paths."}

    def __init__(self):
        super().__init__()
        self.target = None

    def decide(self, observation):
        units, enemies = self.observe(observation)
        if not units or not enemies:
            return []
        gun = next((unit for unit in units if unit.get("class") == "artillery"), None)
        if gun is None:
            return [order for unit in units for order in self.attack(
                unit, min(enemies, key=lambda enemy: distance(unit, enemy)))]
        riders = [enemy for enemy in enemies if "cavalry" in enemy.get("class", "")]
        # The first live run re-picked between two equidistant riders every decision.
        nearest = min(riders or enemies, key=lambda enemy: distance(gun, enemy))
        target = next((enemy for enemy in riders or enemies if enemy["id"] == self.target),
                      nearest)
        if distance(gun, nearest) < distance(gun, target) - 30:
            target = nearest
        self.target = target["id"]
        if gun.get("ammo") and distance(gun, target) <= gun.get("range", 0):
            orders = self.attack(gun, target, "ranged")
        else:
            # A ranged attack beyond range would walk this slow, fragile gun forward.
            previous = self.sent.get(gun["id"], ({}, 0))[0]
            orders = (self.issue(gun, {"unit": gun["id"], "type": "halt"})
                      if previous.get("type") == "attack" else [])
        for escort in units:
            if escort is gun:
                continue
            if distance(gun, target) < 120:
                orders += self.attack(escort, target)
            else:
                orders += self.move(escort, _offset(gun, _direction(gun, target), 25, 20), target)
        return orders

    def metadata(self):
        return {"type": "bodyguard", "target": self.target}


def _beside(target: dict, degrees: float, metres: float) -> dict:
    """A point ``metres`` from a unit, ``degrees`` clockwise from its bearing (0 = +z)."""
    angle = math.radians(target.get("bearing", 0) + degrees)
    return {"x": target["x"] + math.sin(angle) * metres,
            "z": target["z"] + math.cos(angle) * metres}


def _keep(enemies: list[dict], target_id, origin: dict) -> dict:
    """The committed target while it stays visible and unrouted, else the nearest."""
    return next((enemy for enemy in enemies if enemy["id"] == target_id), None) or min(
        enemies, key=lambda enemy: distance(origin, enemy))


class Crossfire(SmallDiagnostic):
    """S3: the spearmen pin one dwarf unit; then each gun fires into one of its flanks."""

    card = {"purpose": "Can two gun units find lines of fire past their own melee?",
            "knowledge": "S3: fire-at-will off. Spearmen attack the nearest visible enemy "
                         "and keep it until it routs. Guns wait 30 m behind them until that "
                         "target is in melee, then move 100 m from it at its bearing +-80 "
                         "degrees (one each side) and fire only at it. A gun within 50 m of "
                         "another enemy steps 120 m away from it; without ammunition it "
                         "joins the melee. No hidden state or line-of-sight test."}

    def __init__(self):
        super().__init__()
        self.target = None

    def decide(self, observation):
        units, enemies = self.observe(observation)
        if not units or not enemies:
            return []
        units.sort(key=lambda unit: unit["id"])
        guns = [unit for unit in units if unit.get("class") in SHOOTERS]
        line = [unit for unit in units if unit not in guns]
        anchor = _centre(line or guns)
        target = _keep(enemies, self.target, anchor)
        self.target = target["id"]
        orders = [order for unit in line for order in self.attack(unit, target)]
        pinned = "melee" in target.get("state", []) or not line
        for index, gun in enumerate(guns):
            if gun.get("behaviours", {}).get("fire_at_will"):
                orders.append({"unit": gun["id"], "type": "behaviour",
                               "behaviour": "fire_at_will", "enabled": False})
            if not gun.get("ammo"):
                orders += self.attack(gun, target)
                continue
            threat = min((enemy for enemy in enemies if enemy is not target),
                         key=lambda enemy: distance(gun, enemy), default=None)
            post = _beside(target, 80 if index % 2 else -80, 100)
            if threat and distance(gun, threat) < 50:
                orders += self.move(gun, _offset(threat, _direction(threat, gun), 120), threat)
            elif not pinned:
                behind = _offset(anchor, _direction(target, anchor), 30, 25 if index % 2 else -25)
                orders += self.move(gun, behind, target)
            elif distance(gun, post) > 25:
                orders += self.move(gun, post, target)
            else:
                orders += self.attack(gun, target, "ranged")
        return orders

    def metadata(self):
        return {"type": "crossfire", "target": self.target}


class SpellWindow(SmallDiagnostic):
    """S5: the spearmen fight; the wizard casts from behind them when its allies are clear."""

    card = {"purpose": "Can one wizard spend scarce magic without burning its own line?",
            "knowledge": "S5: spearmen attack the nearest visible enemy and keep it until it "
                         "routs. The wizard stays 100 m behind them and steps 120 m away "
                         "from an enemy within 50 m. Burning Head when two enemies are "
                         "within 40 m of each other and over 40 m from every friendly unit, "
                         "cast at the nearer one towards the other; else Flame Storm on an "
                         "enemy not in melee and over 40 m from friends; else Fireball, "
                         "preferring an enemy not in melee. The cheapest ready, affordable "
                         "variant by key name, within 95% of its range; 5 s between casts."}

    def __init__(self):
        super().__init__()
        self.target = None
        self.last_cast_s = -math.inf
        self.casts = []

    def spell(self, caster, name, magic):
        ready = [ability for ability in caster.get("abilities", [])
                 if name in ability["key"] and ability.get("ready") and ability.get("can_use")
                 and ability.get("mana", 0) <= magic]
        return min(ready, key=lambda ability: ability.get("mana", 0), default=None)

    def cast(self, caster, units, enemies, magic):
        """The first spell whose public conditions hold, as (ability, target, toward)."""
        def clear(enemy):
            return all(distance(enemy, unit) > 40 for unit in units)

        options = []
        pairs = [(a, b) for a in enemies for b in enemies
                 if a["id"] < b["id"] and distance(a, b) <= 40 and clear(a) and clear(b)]
        if pairs:
            pair = min(pairs, key=lambda pair: sum(distance(caster, enemy) for enemy in pair))
            near, far = sorted(pair, key=lambda enemy: distance(caster, enemy))
            options.append(("burning_head", near, far))
        free = sorted((enemy for enemy in enemies if "melee" not in enemy.get("state", [])),
                      key=lambda enemy: distance(caster, enemy))
        options += [("flame_storm", enemy, None) for enemy in free if clear(enemy)]
        options += [("fireball", enemy, None) for enemy in free + sorted(
            enemies, key=lambda enemy: distance(caster, enemy))]
        for name, enemy, toward in options:
            ability = self.spell(caster, name, magic)
            if ability and distance(caster, enemy) <= ability.get("cast_range", 0) * .95:
                return ability, enemy, toward
        return None

    def decide(self, observation):
        units, enemies = self.observe(observation)
        if not units or not enemies:
            return []
        units.sort(key=lambda unit: unit["id"])
        caster = next((unit for unit in units if any(
            ability.get("mana", 0) > 0 for ability in unit.get("abilities", []))), None)
        line = [unit for unit in units if unit is not caster]
        target = _keep(enemies, self.target, _centre(line or units))
        self.target = target["id"]
        orders = [order for unit in line for order in self.attack(unit, target)]
        if caster is None:
            return orders
        magic = (observation.get("magic") or {}).get("current", 0)
        choice = self.now - self.last_cast_s >= 5 and self.cast(caster, units, enemies, magic)
        if choice:
            ability, enemy, toward = choice
            order = {"unit": caster["id"], "type": "ability", "ability": ability["key"]}
            kinds = ability.get("target", "")
            if "Ground" in kinds and (toward or "Enemy" not in kinds):
                start = _offset(enemy, _direction(toward, enemy), 15) if toward else enemy
                order.update(x=start["x"], z=start["z"])
                if toward:
                    order["facing"] = math.degrees(math.atan2(
                        toward["x"] - start["x"], toward["z"] - start["z"])) % 360
            else:
                order["target"] = enemy["id"]
            self.last_cast_s = self.now
            self.sent.pop(caster["id"], None)  # a cast interrupts the wizard's movement
            self.casts.append({"time_s": self.now, "ability": ability["key"],
                               "target": enemy["id"]})
            return orders + [order]
        threat = min(enemies, key=lambda enemy: distance(caster, enemy))
        if distance(caster, threat) < 50:
            return orders + self.move(caster, _offset(threat, _direction(threat, caster), 120),
                                      threat)
        if line:
            centre = _centre(line)
            orders += self.move(caster, _offset(centre, _direction(target, centre), 100), target)
        return orders

    def metadata(self):
        return {"type": "spell_window", "target": self.target, "casts": len(self.casts),
                "last_cast": self.casts[-1] if self.casts else None}


class HammerAnvil(SmallDiagnostic):
    """S6: the infantry pins one unit; the knights charge its rear, pull out and repeat."""

    card = {"purpose": "Can an infantry pin and rear charges beat three equal units?",
            "knowledge": "S6: infantry attacks the nearest visible enemy and keeps it until "
                         "it routs. Cavalry waits 40 m behind and 60 m beside the infantry "
                         "until that target is in melee, then rides via a 90 m side "
                         "waypoint to 70 m behind it and charges. After 8 s of observed "
                         "contact, or the target's rout during the charge, it withdraws "
                         "120 m from the nearest enemy for 10 s (up to 20 s while enemies "
                         "stay within 80 m), then repeats on the infantry's current target. "
                         "Without infantry it charges the nearest enemy the same way. "
                         "No hidden state or path search."}

    def __init__(self):
        super().__init__()
        self.target = None
        self.phase = "wait"
        self.side = 1
        self.contact_s = None
        self.withdraw_s = None
        self.retreat = None
        self.charges = 0

    def decide(self, observation):
        units, enemies = self.observe(observation)
        if not units or not enemies:
            return []
        units.sort(key=lambda unit: unit["id"])
        riders = [unit for unit in units if "cavalry" in unit.get("class", "")]
        line = [unit for unit in units if unit not in riders]
        target = _keep(enemies, self.target, _centre(line or riders))
        routed = self.target not in (None, target["id"])
        self.target = target["id"]
        orders = [order for unit in line for order in self.attack(unit, target)]
        if not riders:
            return orders
        group = _centre(riders)
        front = _direction(target, _centre(line or riders))
        if routed and self.phase in ("side", "rear"):
            self.phase = "wait"
        if self.phase == "withdraw":
            elapsed = self.now - self.withdraw_s
            if elapsed >= 20 or elapsed >= 10 and all(
                    distance(group, enemy) >= 80 for enemy in enemies):
                self.phase = "wait"
        if self.phase == "wait" and ("melee" in target.get("state", []) or not line):
            self.phase = "side"
            self.side = 1 if distance(group, _offset(target, front, 0, 90)) <= distance(
                group, _offset(target, front, 0, -90)) else -1
        side = _offset(target, front, 0, 90 * self.side)
        rear = _offset(target, front, -70)
        if self.phase == "side" and distance(group, side) < 25:
            self.phase = "rear"
        if self.phase == "rear" and distance(group, rear) < 25:
            self.phase, self.contact_s = "charge", None
            self.charges += 1
        if self.phase == "charge":
            if self.contact_s is None and any("melee" in unit.get("state", []) for unit in riders):
                self.contact_s = self.now
            if routed or (self.contact_s is not None and self.now - self.contact_s >= 8):
                threat = min(enemies, key=lambda enemy: distance(group, enemy))
                self.phase, self.withdraw_s = "withdraw", self.now
                self.retreat = _offset(threat, _direction(threat, group), 120)
        if self.phase == "withdraw":
            return orders + [order for unit in riders
                             for order in self.move(unit, self.retreat, target)]
        if self.phase == "charge":
            return orders + [order for unit in riders for order in self.attack(unit, target)]
        goal = {"wait": _offset(_centre(line or riders), front, 40, 60 * self.side),
                "side": side, "rear": rear}[self.phase]
        return orders + [order for unit in riders for order in self.move(unit, goal, target)]

    def metadata(self):
        return {"type": "hammer_anvil", "phase": self.phase, "charges": self.charges,
                "target": self.target}


def _clear(terrain: dict, point: dict) -> bool:
    """Whether the terrain sample holding ``point`` is unrestricted (outside the grid: yes)."""
    rows, cell = terrain.get("rows") or [], terrain.get("cell_m")
    if not rows or not cell:
        return True
    row = round((point["z"] - terrain["z0"]) / cell)
    column = round((point["x"] - terrain["x0"]) / cell)
    return not (0 <= row < len(rows) and 0 <= column < len(rows[row])) or rows[row][column] != "#"


class CornerHold(SmallDiagnostic):
    """S7: walk both units into a map corner, face out in a line and hold."""

    card = {"purpose": "Can two outnumbered units deny an envelopment by backing into a corner?",
            "knowledge": "S7: from the public map bounds and blocked terrain cells, a post 30 m "
                         "inside each corner, stepped toward the map centre past blocked "
                         "cells. The army takes the post nearest to it among those nearer to "
                         "it than to the visible enemy (else the nearest), chosen once. Its "
                         "units stand 16 m either side of the post facing the map centre "
                         "(out of the corner) and hold. A unit in "
                         "melee attacks the nearest enemy within 20 m and does not move. No "
                         "elevation, path search or hidden state."}

    def __init__(self):
        super().__init__()
        self.corner = self.middle = None

    def choose(self, terrain: dict, army: dict, enemies: list[dict]) -> dict | None:
        bounds = self.bounds
        if not all(f"{edge}_{axis}" in bounds for edge in ("min", "max") for axis in "xz"):
            return None
        self.middle = {axis: (bounds[f"min_{axis}"] + bounds[f"max_{axis}"]) / 2 for axis in "xz"}
        posts = []
        for x in (bounds["min_x"] + 30, bounds["max_x"] - 30):
            for z in (bounds["min_z"] + 30, bounds["max_z"] - 30):
                post = {"x": x, "z": z}
                step = _direction(post, self.middle)
                for _ in range(8):
                    if _clear(terrain, post):
                        break
                    post = _offset(post, step, terrain.get("cell_m") or 32)
                posts.append(post)
        enemy = _centre(enemies) if enemies else None
        safe = [post for post in posts if enemy is None
                or distance(army, post) < distance(enemy, post)]
        return min(safe or posts, key=lambda post: distance(army, post))

    def decide(self, observation):
        units, enemies = self.observe(observation)
        if not units:
            return []
        units.sort(key=lambda unit: unit["id"])
        army = _centre(units)
        if self.corner is None:
            self.corner = self.choose(observation.get("terrain") or {}, army, enemies)
            if self.corner is None:
                return []
        # Fixed, so an approaching enemy cannot reshuffle the line; terrain may come only once.
        front = _direction(self.corner, self.middle)
        orders = []
        for index, unit in enumerate(units):
            if "melee" in unit.get("state", []):
                near = min(enemies, key=lambda enemy: distance(unit, enemy), default=None)
                if near and distance(unit, near) <= 20:
                    orders += self.attack(unit, near)
                continue
            spot = _offset(self.corner, front, 0, 16 if index % 2 else -16)
            orders += self.move(unit, spot, self.middle)
        return orders

    def metadata(self):
        return {"type": "corner_hold", "corner": self.corner}


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
