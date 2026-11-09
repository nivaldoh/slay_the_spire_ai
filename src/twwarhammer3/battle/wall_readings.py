"""Evaluator readings for the walled siege defence (cth-emp-siege-a-v1 and cth-emp-siege-a-all-v1),
descriptive only (runs/siege-evals-20261108/final-haengju.md, Measurements and Infrastructure).

They read a finished battle's records: its observations, whose hidden sections a reader may use,
its trace (trace.jsonl's decisions and acks) and the private record (``private.jsonl``, fields in
capture.copy_private_record). Nothing here runs during a battle or reaches a controller. Capture
holders and tickets follow evidence_rules (a holder of None is neither side's; tickets are the
defender's row). Divisions are lists of enemy ids fixed at the first observation
(evidence_rules.group_ids). The wall line is the public one the witness uses
(wall_defence.wall_line); the breach polygon is a private one, frozen from stage 1's terrain grid
and on_wall readings, and until then absent.
"""

from twwarhammer3.battle.evidence_rules import defender_tickets, holds, ids_by_type, in_melee
from twwarhammer3.battle.scripted import distance
from twwarhammer3.battle.wall_defence import RESERVE, inside, wall_distance

# JUDGEMENT?: Approach distance — Claude, 2026-11-08 (design, decision 1 and Measurements): a
# division approaches when one of its visible units is 150 m or nearer the wall line or inside it.
# Another distance moves the ammunition reading; the S-ammo condition rests on it.
APPROACH_M = 150


def enemy_held(observations, points=("c1", "c2", "c7")):
    """Battle ms of the first observation in which the enemy holds each capture point, or None."""
    times = dict.fromkeys(points)
    for observation in observations:
        for point in (observation.get("mode") or {}).get("capture_points") or []:
            if point.get("id") in times and times[point["id"]] is None and holds(point, "enemy"):
                times[point["id"]] = observation["time_ms"]
    return times


def ticket_onset(observations):
    """Battle ms of the first observation whose defender tickets are below the first reading's,
    or None."""
    first = None
    for observation in observations:
        mode = observation.get("mode") or {}
        tickets = defender_tickets(mode) if mode.get("role") else None
        if tickets is None:
            continue
        if first is None:
            first = tickets
        elif tickets < first:
            return observation["time_ms"]
    return None


def first_sightings(observations, divisions):
    """Battle ms of the first observation whose public ``enemy`` list holds a unit of each
    division ({name: [enemy ids]}), or None. Never the private record, which also lists the
    units nobody can see."""
    times = dict.fromkeys(divisions)
    for observation in observations:
        seen = {unit.get("id") for unit in observation.get("enemy") or []}
        for name, ids in divisions.items():
            if times[name] is None and seen.intersection(ids):
                times[name] = observation["time_ms"]
    return times


def approach_ammunition(observations, divisions, line):
    """At each division's first approach (APPROACH_M), the battle ms and the friendly missile
    units' summed ``ammo`` and ``ammo0``; None for a division that never approached. Spent shots
    do not prove hits."""
    result = dict.fromkeys(divisions)
    for observation in observations:
        seen = {unit["id"]: unit for unit in observation.get("enemy") or []}
        for name, ids in divisions.items():
            near = [seen[i] for i in ids if i in seen
                    and (inside(line, seen[i]) or wall_distance(line, seen[i]) <= APPROACH_M)]
            if result[name] is None and near:
                missile = [u for u in observation.get("friendly") or [] if u.get("ammo0")]
                result[name] = {"time_ms": observation["time_ms"],
                                "ammo": sum(u.get("ammo") or 0 for u in missile),
                                "ammo0": sum(u["ammo0"] for u in missile)}
    return result


def _in_polygon(point, polygon):
    # Even-odd crossing test (W. R. Franklin, pnpoly).
    x, z, result = point["x"], point["z"], False
    for (ax, az), (bx, bz) in zip(polygon, polygon[-1:] + polygon[:-1]):
        if (az > z) != (bz > z) and x < (bx - ax) * (z - az) / (bz - az) + ax:
            result = not result
    return result


# JUDGEMENT?: Breach reading — Claude, 2026-11-08 (design, Measurements): on_wall in the private
# record, or the centre inside the private polygon in two frames in a row. One frame or the public
# line gives earlier breaches; the breach time and the reserve response readings rest on it.
def breach(frames, polygon=None):
    """The first private-record frame at which an enemy reads ``on_wall`` true, or (given the
    stage 1 polygon, [(x, z), ...]) has had its centre inside it in two frames in a row:
    {"time_ms", "id", "by"}; None if no enemy breached."""
    inside_before = set()
    for frame in frames:
        now = set()
        for unit in frame.get("enemy") or []:
            if unit.get("on_wall") is True:
                return {"time_ms": frame["time_ms"], "id": unit["id"], "by": "on_wall"}
            if polygon and unit.get("x") is not None and unit.get("z") is not None \
                    and _in_polygon(unit, polygon):
                if unit["id"] in inside_before:
                    return {"time_ms": frame["time_ms"], "id": unit["id"], "by": "polygon"}
                now.add(unit["id"])
        inside_before = now
    return None


# JUDGEMENT?: Reserve response — Claude, 2026-11-08 (design, Measurements): any accepted attack by a
# reserve unit the engine applied at or after the breach, and evidence_rules.in_melee. Counting
# only attacks on the breaching unit, or decision times, moves both readings; reports rest on it.
def reserve_response(trace, frames, breached):
    """Ms from a breach (``breach``'s reading) to the reserve's answer: ``attack_ms`` until the
    engine applied (the ack's ``applied_ms``) the first accepted attack order of a reserve unit,
    the Lord or a Jade Warriors unit by type (wall_defence.RESERVE), and ``melee_ms`` until the
    first frame in which one of them is in melee (evidence_rules.in_melee: the flag, with men
    left). Both count from the breach on; None for an answer that never came, and None with no
    breach. ``trace`` holds the episode's trace.jsonl rows (its "decision" and "ack" rows);
    ``frames`` are observations or 1 Hz replay frames, whose first with friendly units gives the
    reserve's ids."""
    if breached is None:
        return None
    start = breached["time_ms"]
    first = next((frame for frame in frames if frame.get("friendly")), {})
    reserve = set(ids_by_type(first.get("friendly") or [], RESERVE))
    orders = {row["request"]: row["orders"] for row in trace if row.get("kind") == "decision"}
    attack = None
    for row in trace:
        ack = row.get("ack") if row.get("kind") == "ack" else None
        if not ack or ack.get("applied_ms") is None or ack["applied_ms"] < start:
            continue
        sent = orders.get(row.get("request", ack.get("request"))) or []
        if any(result.get("ok") is True and isinstance(result.get("index"), int)
               and 0 < result["index"] <= len(sent)
               and sent[result["index"] - 1].get("type") == "attack"
               and sent[result["index"] - 1].get("unit") in reserve
               for result in ack.get("results") or []):
            attack = ack["applied_ms"]
            break
    melee = next((frame["time_ms"] for frame in frames
                  if frame["time_ms"] >= start and reserve & in_melee(frame)), None)
    return {"attack_ms": None if attack is None else attack - start,
            "melee_ms": None if melee is None else melee - start}


def damage_releases(observations):
    """The waves releases damage caused, from the last observation's evaluation, each with the
    friendly units then in their public ``range`` of a released unit (the observation at or just
    before the release). Releases on time are left out."""
    if not observations:
        return []
    evidence = (observations[-1].get("evaluation") or {}).get("reserve") or {}
    result = []
    for release in evidence.get("releases") or []:
        if release.get("reason") != "damage":
            continue
        before = [o for o in observations if o["time_ms"] <= release["released_ms"]]
        friendly = before[-1].get("friendly") or [] if before else []
        placed = [u for u in release.get("units") or [] if u.get("x") is not None]
        near = sorted(f["id"] for f in friendly if f.get("range") and any(
            distance(f, unit) <= f["range"] for unit in placed))
        result.append({"group": release["group"], "time_ms": release["released_ms"],
                       "damaged": [d["id"] for d in release.get("damaged") or []],
                       "friendly_in_range": near})
    return result
