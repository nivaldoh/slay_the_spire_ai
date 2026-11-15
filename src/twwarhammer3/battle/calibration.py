"""The base class and geometry helpers of the small public-state diagnostics, and CornerHold.

The 23 other diagnostics of the October small scenarios and tactic cards were deleted on
2026-11-15 (owner: "Delete all of it"; tag wh3-legacy-20261115 has them). What is left is what
lines.py and lines_readings.py are built on. Select CornerHold by dotted class name,
``twwarhammer3.battle.calibration:CornerHold``. It uses only public observations.
"""

import math

from twwarhammer3.battle.scripted import Hold, distance
from twwarhammer3.battle.skills import OUT
from twwarhammer3.protocol import friendly_units, visible_enemies

# Steps to the eight neighbouring terrain cells.
NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


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
