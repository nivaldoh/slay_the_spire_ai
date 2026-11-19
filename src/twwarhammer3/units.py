"""Geometry, identity and eligibility of public WH3 units."""

import math

ROUTED = {"routing", "shattered"}
UNAVAILABLE = ROUTED | {"leaving", "not_deployed", "deploying"}


def distance(a: dict, b: dict) -> float:
    """Metres between two things with x and z (units, points, orders); inf if one is unplaced."""
    if None in (a.get("x"), a.get("z"), b.get("x"), b.get("z")):
        return math.inf
    return math.hypot(a["x"] - b["x"], a["z"] - b["z"])


def nearest(unit: dict, others) -> dict | None:
    """The one of ``others`` nearest ``unit``; ties go to the smaller x, then z, never to id or
    list order."""
    return min(others, key=lambda other: (distance(unit, other), other["x"], other["z"]),
               default=None)


def find(units, uid) -> dict | None:
    """The unit of ``units`` whose id is ``uid``, or None."""
    return next((unit for unit in units if unit["id"] == uid), None)


def active_units(units) -> list[dict]:
    return [unit for unit in units if unit.get("men") and unit.get("x") is not None
            and unit.get("z") is not None and not ROUTED.intersection(unit.get("state", []))]


def direction(origin: dict, target: dict) -> tuple[float, float]:
    dx, dz = target["x"] - origin["x"], target["z"] - origin["z"]
    length = math.hypot(dx, dz)
    return (dx / length, dz / length) if length else (0, 1)


def centre(units: list[dict]) -> dict:
    return {axis: sum(unit[axis] for unit in units) / len(units) for axis in ("x", "z")}


def able(unit):
    return (unit.get("men", 0) > 0 and not unit.get("error")
            and not UNAVAILABLE.intersection(unit.get("state", [])))


# JUDGEMENT: Contact rule — Claude, 2026-11-08 (portfolio S7a): the engine's melee flag on a unit
# with men left. A distance, the flag plus a distance, or flagged dead units give other contact
# times; Alesia's group contact, Belgrade's cue, Haengju's reserve response, Izmail's I6 rest on it.
def in_melee(frame) -> set[str]:
    """Ids of the units on both sides that the engine flags as in melee (``is_in_melee``, the
    "melee" state) and that still have men. The flag outlives the men: Helmgart's Magma Cannon
    read men 0 and melee from 413.8 s to the end at 708.7 s. A unit's own flag counts even when
    no opponent is near it: Helmgart's enemy orc boyz e5 read melee 167.7 m from every friendly
    unit at 703.9 s. A reader that needs to know where a fight is adds its own distance test,
    as Belgrade's cue does."""
    return {unit["id"] for side in ("friendly", "enemy") for unit in frame[side]
            if "melee" in (unit.get("state") or []) and unit["men"] > 0}


def ids_by_type(units, keys) -> list[str]:
    """Ids of the units (unit records or ``enemy_roster`` entries) whose type key is in
    ``keys``. Never select by ``class``: the Magma Cannon reads missile_chariot and the Bull
    Centaurs read infantry."""
    return [unit["id"] for unit in units if unit.get("type") in keys]
