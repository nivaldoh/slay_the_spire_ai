"""The base class and geometry helpers of the small public-state diagnostics, and the four
diagnostics still named by current work.

Twenty other diagnostics of the October small scenarios and tactic cards were deleted on
2026-11-15 (owner: "Delete all of it"; tag wh3-legacy-20261115 has them). Kept: SmallDiagnostic
and the helpers, which lines.py and lines_readings.py are built on; CornerHold, which
lines.LinesCornerCamp extends; PriorityStrike, the air relief's selected optional witness
(tactics-reference.md); and LineTeam and LineTeamReserve, which the parked team-structures
plan builds on. Select one by dotted class name, e.g.
``twwarhammer3.battle.calibration:CornerHold``. They use only public observations.
"""

import math

from twwarhammer3.battle.scripted import Hold
from twwarhammer3.battle.skills import SHOOTERS
from twwarhammer3.protocol import friendly_units, visible_enemies
from twwarhammer3.units import active_units, centre, direction, distance

# Steps to the eight neighbouring terrain cells.
NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


def _offset(origin: dict, direction: tuple, forward: float, across: float = 0) -> dict:
    dx, dz = direction
    return {"x": origin["x"] + dx * forward - dz * across,
            "z": origin["z"] + dz * forward + dx * across}


class SmallDiagnostic(Hold):
    """Order bookkeeping shared by the small public-state diagnostics.

    Every move steps off restricted terrain cells and refused destinations to the nearest
    open spot within two cells, or the unit holds (disclosed for all diagnostics). Those
    spots stay 30 m inside the map bounds like the destination, and points off the map
    count as blocked.
    """

    def __init__(self):
        self.sent = {}
        self.routing_at = {}
        self.now = 0
        self.bounds = {}
        self.terrain = {}
        self.unreachable = []

    def observe(self, observation):
        self.now = observation.get("time_ms", 0) / 1000
        self.terrain = observation.get("terrain") or self.terrain
        self.bounds = self.terrain.get("bounds") or {}
        units = [unit for unit in active_units(friendly_units(observation).values())
                 if self.now > self.routing_at.get(unit["id"], -math.inf)]
        return (units,
                active_units(visible_enemies(observation).values()))

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

    def inside(self, point: dict) -> dict:
        """``point`` moved to at least 30 m inside the map bounds the observation reports."""
        point = dict(point)
        for axis in ("x", "z"):
            if f"min_{axis}" in self.bounds and f"max_{axis}" in self.bounds:
                point[axis] = max(self.bounds[f"min_{axis}"] + 30,
                                  min(self.bounds[f"max_{axis}"] - 30, point[axis]))
        return point

    def move(self, unit, point, target):
        point = self.inside(point)
        # Live S6: a wait post inside the map's central rock was refused 147 times. Take the
        # nearest open spot within two terrain cells, or hold where the unit is. Live S3 r3:
        # 13 refusals were ring points past the map's edge (x -514/-546, min_x -512).
        cell = self.terrain.get("cell_m") or 32
        point = self.open_point([point] + [
            self.inside({"x": point["x"] + dx * cell * ring, "z": point["z"] + dz * cell * ring})
            for ring in (1, 2) for dx, dz in NEIGHBOURS])
        if point is None or distance(unit, point) < 12:
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
                order = self.sent.pop(result.get("unit"), ({},))[0]
                if result.get("error") == "unreachable" and order.get("type") == "move":
                    self.unreachable.append({"x": order["x"], "z": order["z"]})
                if result.get("error") == "unit_routing":
                    self.routing_at[result["unit"]] = ack["applied_ms"] / 1000

    def open_point(self, points: list[dict]) -> dict | None:
        """The first point on clear terrain and away from refused moves, if any."""
        # Live S2/S3 runs retried posts inside the map's central rock hundreds of times;
        # with no open point the caller acts from where it stands instead.
        return next((point for point in points if _clear(self.terrain, point) and all(
            distance(point, bad) >= 30 for bad in self.unreachable)), None)


def _keep(enemies: list[dict], target_id, origin: dict) -> dict:
    """The committed target while it stays visible and unrouted, else the nearest."""
    return next((enemy for enemy in enemies if enemy["id"] == target_id), None) or min(
        enemies, key=lambda enemy: distance(origin, enemy))


def _clear(terrain: dict, point: dict) -> bool:
    """Whether the terrain sample holding ``point`` is unrestricted (off the map: no)."""
    rows, cell = terrain.get("rows") or [], terrain.get("cell_m")
    if not rows or not cell:
        return True
    row = round((point["z"] - terrain["z0"]) / cell)
    column = round((point["x"] - terrain["x0"]) / cell)
    # The grid spans the map bounds; b23 counted points past its edge as open.
    return 0 <= row < len(rows) and 0 <= column < len(rows[row]) and rows[row][column] != "#"


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
                step = direction(post, self.middle)
                for _ in range(8):
                    if _clear(terrain, post):
                        break
                    post = _offset(post, step, terrain.get("cell_m") or 32)
                posts.append(post)
        enemy = centre(enemies) if enemies else None
        safe = [post for post in posts if enemy is None
                or distance(army, post) < distance(enemy, post)]
        return min(safe or posts, key=lambda post: distance(army, post))

    def decide(self, observation):
        units, enemies = self.observe(observation)
        if not units:
            return []
        units.sort(key=lambda unit: unit["id"])
        army = centre(units)
        if self.corner is None:
            self.corner = self.choose(observation.get("terrain") or {}, army, enemies)
            if self.corner is None:
                return []
        # Fixed, so an approaching enemy cannot reshuffle the line; terrain may come only once.
        front = direction(self.corner, self.middle)
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


def _fraction(unit: dict) -> float:
    return unit["men"] / unit["men0"] if unit.get("men0") else 1


class PriorityStrike(SmallDiagnostic):
    """Flyers ignore the screen for the enemy's artillery or commander; the ground waits."""

    card = {"purpose": "Can flyers skip a screen that beats them to kill the decisive target?",
            "knowledge": "Flying units attack the visible enemy artillery, else a visible "
                         "enemy lord, kept until it routs, dies or leaves sight; with neither "
                         "visible, the enemy with the lowest men fraction. Ground units hold "
                         "until no artillery or lord is visible, then attack the nearest "
                         "enemy. No hidden state or path search."}

    def __init__(self):
        super().__init__()
        self.target = None

    def decide(self, observation):
        units, enemies = self.observe(observation)
        if not units or not enemies:
            return []
        # A lordless army's commander flag sits on its first card, so only a real lord counts.
        priority = [enemy for enemy in enemies if enemy.get("class") in ("artillery", "lord")]
        priority.sort(key=lambda enemy: enemy.get("class") != "artillery")
        flyers = [unit for unit in units if unit.get("can_fly")]
        target = next((enemy for enemy in priority if enemy["id"] == self.target), None) or (
            priority[0] if priority else min(enemies, key=_fraction))
        self.target = target["id"]
        orders = [order for unit in flyers for order in self.attack(unit, target)]
        if not priority:
            orders += [order for unit in units if unit not in flyers
                       for order in self.attack(unit, min(
                           enemies, key=lambda enemy: distance(unit, enemy)))]
        return orders

    def metadata(self):
        return {"type": "priority_strike", "target": self.target}


class LineTeam(SmallDiagnostic):
    """Empire line battle: fixed jobs for a line, two gun units, a reserve and the knights."""

    card = {"purpose": "Does a fixed assignment of jobs win the 7 v 7 Empire line battle, "
                       "and does a reserve that replaces a broken line unit do better?",
            "knowledge": "Roles by card key and class: infantry whose key holds 'spearmen' is "
                         "the reserve, other infantry the line, missile units the guns, "
                         "cavalry the knights. The line keeps its deployment in guard mode. "
                         "Forward is from the line's centre toward the visible enemies' "
                         "centre, read once. Guns stand 30 m behind the line centre, 18 m "
                         "either side, skirmish off, and shoot the nearest enemy cavalry in "
                         "range, else the nearest enemy in range, keeping a target while it "
                         "stays in that set and halting with none. The reserve waits 35 m "
                         "behind the line centre in guard mode and attacks an enemy infantry "
                         "unit within 25 m of it, preferring its last target while that is "
                         "within 25 m. The "
                         "knights wait 50 m behind the line centre and charge the nearest "
                         "enemy cavalry once one is within 120 m of them; with no enemy "
                         "cavalry left they charge the nearest enemy missile unit, else the "
                         "enemy infantry unit in melee with the lowest men fraction. A "
                         "target is kept until it routs or vanishes; with none the knights "
                         "ride back to their post unless they are in melee. No hidden state "
                         "or predicted paths."}
    variant = "fixed"

    def __init__(self):
        super().__init__()
        self.forward = None
        self.centre = None
        self.knights_target = None
        self.reserve_target = None
        self.gaps = []

    def roles(self, units):
        line = [u for u in units if u.get("class") == "infantry" and "spearmen" not in u["type"]]
        reserve = [u for u in units if u.get("class") == "infantry" and "spearmen" in u["type"]]
        guns = [u for u in units if u.get("class") in SHOOTERS]
        knights = [u for u in units if u.get("class") == "cavalry"]
        return line, reserve, guns, knights

    def decide(self, observation):
        units, enemies = self.observe(observation)
        if not units or not enemies:
            return []
        line, reserve, guns, knights = self.roles(units)
        if self.forward is None:
            self.centre = centre(line or units)
            self.forward = direction(self.centre, centre(enemies))
        back = (-self.forward[0], -self.forward[1])
        orders = []
        for unit in line + reserve:
            if unit.get("behaviours", {}).get("defend") is False:
                orders.append({"unit": unit["id"], "type": "behaviour",
                               "behaviour": "defend", "enabled": True})
        cavalry = [e for e in enemies if e.get("class") == "cavalry"]
        for index, gun in enumerate(sorted(guns, key=lambda u: u["id"])):
            if gun.get("behaviours", {}).get("skirmish"):
                orders.append({"unit": gun["id"], "type": "behaviour",
                               "behaviour": "skirmish", "enabled": False})
            in_range = [e for e in enemies if distance(gun, e) <= gun.get("range", 0)]
            near = [e for e in in_range if e in cavalry] or in_range
            if gun.get("ammo") and near:
                orders += self.attack(gun, self.kept(gun, near), "ranged")
            elif self.sent.get(gun["id"], ({}, 0))[0].get("type") == "attack":
                orders += self.issue(gun, {"unit": gun["id"], "type": "halt"})
            else:
                post = _offset(self.centre, back, 30, 18 if index == 0 else -18)
                orders += self.move(gun, post, centre(enemies))
        orders += self.reserve_orders(reserve, line, enemies, back)
        for unit in knights:
            orders += self.knights_orders(unit, enemies, cavalry, back)
        return orders

    def kept(self, unit, candidates):
        """The unit's last sent target while it is still a candidate, else the nearest."""
        # Six b44/b45 launches: the guns re-picked between enemies at almost the same
        # distance every decision (8-46 target changes a gun) and the reserve alternated in melee.
        return _keep(candidates, self.sent.get(unit["id"], ({}, 0))[0].get("target"), unit)

    def reserve_orders(self, reserve, line, enemies, back):
        orders = []
        for unit in reserve:
            close = [e for e in enemies if e.get("class") == "infantry" and distance(unit, e) < 25]
            if close:
                orders += self.attack(unit, self.kept(unit, close))
            else:
                orders += self.move(unit, _offset(self.centre, back, 35), centre(enemies))
        return orders

    def knights_orders(self, unit, enemies, cavalry, back):
        target = next((e for e in enemies if e["id"] == self.knights_target), None)
        if target is None:
            close = [e for e in cavalry if distance(unit, e) <= 120]
            shooters = [e for e in enemies if e.get("class") in SHOOTERS]
            engaged = [e for e in enemies if "melee" in e.get("state", [])]
            if close:
                target = min(close, key=lambda e: distance(unit, e))
            elif not cavalry and shooters:
                target = min(shooters, key=lambda e: distance(unit, e))
            elif not cavalry and engaged:
                target = min(engaged, key=_fraction)
        self.knights_target = target["id"] if target else None
        if target:
            return self.attack(unit, target)
        if "melee" in unit.get("state", []):
            return []  # the target broke under them: finish that fight before riding back
        return self.move(unit, _offset(self.centre, back, 50), centre(enemies))

    def metadata(self):
        return {"type": "line_team", "variant": self.variant,
                "knights_target": self.knights_target,
                "reserve_target": self.reserve_target, "gaps": list(self.gaps)}


class LineTeamReserve(LineTeam):
    """LineTeam whose reserve attacks the enemy infantry nearest the latest gap in the line."""

    card = {"purpose": LineTeam.card["purpose"],
            "knowledge": LineTeam.card["knowledge"] + " Replacement rule: when a line unit "
                         "is seen routing or is gone, the reserve attacks the visible enemy "
                         "infantry unit nearest to where the line unit that broke most "
                         "recently was last seen, kept until it routs or vanishes; while a "
                         "line unit is still missing it takes the next such target, and once "
                         "the line is whole again and its target gone it goes back to its "
                         "waiting rule."}
    variant = "reserve"

    def __init__(self):
        super().__init__()
        self.seen = {}
        self.missing = set()

    def reserve_orders(self, reserve, line, enemies, back):
        present = {unit["id"] for unit in line}
        for unit in line:
            self.seen[unit["id"]] = {"x": unit["x"], "z": unit["z"]}
        missing = [uid for uid in self.seen if uid not in present]
        self.gaps += [{"unit": uid, "at": self.now} for uid in missing if uid not in self.missing]
        self.missing = set(missing)
        gone = [gap["unit"] for gap in self.gaps if gap["unit"] not in present]
        target = next((e for e in enemies if e["id"] == self.reserve_target), None)
        if target is None and gone:
            gap = self.seen[gone[-1]]
            infantry = [e for e in enemies if e.get("class") == "infantry"]
            if infantry:
                target = min(infantry, key=lambda e: distance(gap, e))
        self.reserve_target = target["id"] if target else None
        if target is None:
            return super().reserve_orders(reserve, line, enemies, back)
        return [order for unit in reserve for order in self.attack(unit, target)]
