"""Evaluator readings for the camp attack (emp-chd-camp-v1), descriptive only
(docs/twwarhammer3/camp-eval.md, Measurements; runs/siege-evals-20261108/second-look.json).

They read a finished battle's records: public views (the trace's logged "observation" rows or
1 Hz replay frames), its trace (trace.jsonl's "decision" and "ack" rows) and the private record
(``private.jsonl``, fields in capture.copy_private_record), which lists every unit of both sides
once per engine second, hidden enemies included. Nothing here runs during a battle or reaches a
controller. Units are chosen by type key with camp.py's groups, never by class. A field the
record lacks is unknown: lord_before_guns lists such a unit as unknown, and the other readers
leave it out. The pattern is wall_readings.py's.
"""

from math import inf

from twwarhammer3.battle.camp import COVER, CUE_HOLD_MS, CUE_M, FALLBACK_MS, GUNS, LEVIES, MOUNTED
from twwarhammer3.battle.evidence_rules import accepted_orders, in_melee
from twwarhammer3.battle.scripted import distance
from twwarhammer3.protocol import SIEGE_ORDER_TYPES

LORD = "wh3_dlc23_chd_cha_overseer"
# The fields that tell whether a unit is down; a war machine also needs ammo to read silenced.
DOWN_FIELDS = ("men", "routing", "shattered")
# The orders that set or end a unit's attack target, as protocol.validate_orders counts them.
MOVEMENT = ("move", "attack", "halt", *SIEGE_ORDER_TYPES)


def _alive(unit):
    return (unit.get("men") or 0) > 0


def _down(unit):
    return unit.get("men") == 0 or unit.get("routing") is True or unit.get("shattered") is True


# JUDGEMENT?: Lord down — Claude, 2026-11-09 (second look B1): the Overseer is down at his first row
# reading men 0, routing or shattered; a rally does not undo it, and a same-second tie reads False.
# Death alone, or a tie as unknown, moves the split; 'lord down before the first gun' rests on it.
def lord_before_guns(frames):
    """From the private record's frames in order: ``lord_ms``, the battle ms at which the Overseer
    first reads down (men 0, routing or shattered); ``gun_ms``, the first at which a war machine
    reads silenced (men 0, routing, shattered or ammo 0, as camp-eval.md Measurements defines
    it); and ``lord_first``, the exploratory label 'lord down before the first gun': True, False,
    or None while unknown. A same-second tie is False. A unit whose rows stop (missing from a frame
    on, or still undecided in a record without its terminal frame) or whose row lacks a field the
    label needs (men, routing or shattered; ammo for a war machine) without reading down is
    unknown from its last full row, never down, silenced or up, and is listed in ``unknown``."""
    roles = {unit["id"]: unit["type"] == LORD for frame in frames
             for unit in frame.get("enemy") or [] if unit.get("type") in GUNS | {LORD}}
    down, known, stopped = {}, dict.fromkeys(roles, -inf), set()
    for frame in frames:
        rows = {unit["id"]: unit for unit in frame.get("enemy") or []}
        for identity, lord in roles.items():
            if identity in down or identity in stopped:
                continue
            unit = rows.get(identity)
            if unit is None:
                stopped.add(identity)
            elif _down(unit) or not lord and unit.get("ammo") == 0:
                down[identity] = frame["time_ms"]
            elif any(unit.get(field) is None
                     for field in DOWN_FIELDS + (() if lord else ("ammo",))):
                stopped.add(identity)
            else:
                known[identity] = frame["time_ms"]
    if frames and frames[-1].get("terminal") is True:
        known.update((identity, inf) for identity in roles if identity not in stopped)
    lords = [identity for identity, lord in roles.items() if lord]
    guns = [identity for identity, lord in roles.items() if not lord]
    lord = lords[0] if len(lords) == 1 else None
    lord_ms = down.get(lord)
    gun_ms = min((down[gun] for gun in guns if gun in down), default=None)
    if lord is None:
        first = None
    elif lord_ms is not None:
        first = (False if gun_ms is not None and gun_ms <= lord_ms
                 else True if all(known[gun] >= lord_ms for gun in guns) else None)
    else:
        first = False if known[lord] >= (inf if gun_ms is None else gun_ms) else None
    return {"lord_ms": lord_ms, "gun_ms": gun_ms, "lord_first": first,
            "unknown": sorted(identity for identity in roles
                              if identity not in down and known[identity] < inf)}


# JUDGEMENT?: Kept cover distance — Claude, 2026-11-09 (second look B1): a mounted unit's target is
# its last accepted movement order's, a queued attack's from its batch, measured to the nearest live
# levy; a queued attack read after its move gives fewer rows. The 60 m drop proposal rests on it.
def kept_cover_distance(trace, frames):
    """For each mounted unit (camp.MOUNTED, from the first private-record frame) whose current
    accepted attack target is a cover unit (camp.COVER) with men left, one row per private-record
    frame: [{"time_ms", "target", "m"}], ``m`` the target's centre distance to the nearest levy
    unit (camp.LEVIES) with men left, to 0.1 m, or None with no such levy placed. The current
    target is that of the unit's last accepted movement order (move, attack, halt or a siege
    order) the engine applied at or before the frame: an attack's target, none for the others.
    A queued attack after a move counts from its batch's applied time, as ``branch`` reads it,
    although the unit first ends the move; behaviour, ability and flight orders leave the target
    as it was. The record places hidden cover too. Read in stage 3 to see whether kept cover
    leads the mounted group away from the levies."""
    first = next((frame for frame in frames if frame.get("friendly")), {})
    mounted = {unit["id"] for unit in first.get("friendly") or [] if unit.get("type") in MOUNTED}
    accepted, current, result = list(accepted_orders(trace)), {}, {}
    for frame in frames:
        while accepted and accepted[0][0] <= frame["time_ms"]:
            order = accepted.pop(0)[1]
            if order.get("unit") in mounted and order.get("type") in MOVEMENT:
                current[order["unit"]] = order.get("target") if order["type"] == "attack" else None
        enemies = {unit["id"]: unit for unit in frame.get("enemy") or []}
        levies = [unit for unit in frame.get("friendly") or []
                  if unit.get("type") in LEVIES and _alive(unit)]
        for identity, target in current.items():
            cover = enemies.get(target)
            if cover is None or cover.get("type") not in COVER or not _alive(cover):
                continue
            near = min((distance(cover, levy) for levy in levies), default=inf)
            result.setdefault(identity, []).append({
                "time_ms": frame["time_ms"], "target": target,
                "m": None if near == inf else round(near, 1)})
    return result


# JUDGEMENT?: Fire into melee — Claude, 2026-11-09 (second look ER7): a second in which a gun's
# record ammo falls and one friendly unit flagged melee and under_fire loses men. Dropping melee or
# the men test counts more seconds; Belgrade's stage 1 D1 rule rests on it.
def melee_fire_seconds(observations, frames):
    """Engine seconds consistent with fire into melee: in the same second a war machine's
    ``ammo`` in the private record is below its reading in the frame before, and a friendly unit
    in a public observation carries both "melee" and "under_fire" with fewer men than in the
    observation before. [{"time_ms": second * 1000, "guns": [ids], "friendly": [ids]}]. It cannot
    tell a shot aimed at the melee from splash of one aimed nearby, nor the guns' fire from the
    Free Company's own pistols, so the first such second is checked against video."""
    fired, before = {}, {}
    for frame in frames:
        ammo = {unit["id"]: unit.get("ammo") for unit in frame.get("enemy") or []
                if unit.get("type") in GUNS}
        falling = [identity for identity, left in ammo.items() if left is not None
                   and before.get(identity) is not None and left < before[identity]]
        if falling:
            fired.setdefault(frame["time_ms"] // 1000, set()).update(falling)
        before = ammo
    hit, before = {}, {}
    for observation in observations:
        men = {unit["id"]: unit.get("men") for unit in observation.get("friendly") or []}
        hit.setdefault(observation["time_ms"] // 1000, set()).update(
            unit["id"] for unit in observation.get("friendly") or []
            if {"melee", "under_fire"} <= set(unit.get("state") or [])
            and men[unit["id"]] is not None and before.get(unit["id"]) is not None
            and men[unit["id"]] < before[unit["id"]])
        before = men
    return [{"time_ms": second * 1000, "guns": sorted(fired[second]),
             "friendly": sorted(hit[second])} for second in sorted(fired) if hit.get(second)]


def cover_melee_seconds(frames):
    """How many engine seconds of the private record hold a cover unit with men left that reads
    ``melee`` within camp.CUE_M of a levy unit with men left (the cue's test, hidden cover
    included): the levy-cover melee that the stage 1 fire-into-melee rule needs 60 s of."""
    seconds = set()
    for frame in frames:
        levies = [unit for unit in frame.get("friendly") or []
                  if unit.get("type") in LEVIES and _alive(unit)]
        if any(unit.get("type") in COVER and unit.get("melee") is True and _alive(unit)
               and any(distance(unit, levy) <= CUE_M for levy in levies)
               for unit in frame.get("enemy") or []):
            seconds.add(frame["time_ms"] // 1000)
    return len(seconds)


def cue_ms(observations):
    """The battle ms of camp.py's cue in these public observations, or None: one cover unit
    flagged in melee with men left (evidence_rules.in_melee) and within camp.CUE_M of a levy unit
    with men left, in observations spanning camp.CUE_HOLD_MS, each cover unit with its own streak
    that ends at the first observation without that state. Levies are found by type at each
    observation, as CampStrike binds them by type."""
    streaks = {}
    for observation in observations:
        now, visible = observation["time_ms"], observation.get("enemy") or []
        levies = [unit for unit in observation.get("friendly") or []
                  if unit.get("type") in LEVIES and unit.get("men", 0) > 0]
        fighting = in_melee({"friendly": [], "enemy": visible})
        streaks = {enemy["id"]: streaks.get(enemy["id"], now) for enemy in visible
                   if enemy.get("type") in COVER and enemy["id"] in fighting
                   and any(distance(enemy, levy) <= CUE_M for levy in levies)}
        if any(now - since >= CUE_HOLD_MS for since in streaks.values()):
            return now
    return None


# JUDGEMENT?: Camp branch — Claude, 2026-11-09 (second look B1): the first gun or cover target of a
# mounted unit's accepted attack applied at or after the cue (or 180 s). The most-attacked type or
# decision times label some launches otherwise; a model's branch shares rest on it.
def branch(trace, observations):
    """Which D1 branch any controller took, a model included: "guns" or "cover" by the type of
    the first war machine or cover unit that a mounted unit's (camp.MOUNTED) accepted attack
    targets, applied at or after the start, and "neither" when no such attack came. The start is
    the cue camp.py's rule finds in these public observations (``cue_ms``), or 180 s
    (camp.FALLBACK_MS) without a cue by then. Attacks on other enemies, the Overseer included,
    are passed over. ``observations`` are the trace's logged views or 1 Hz replay frames; views
    sparser or denser than the controller's can find an earlier or later cue than it saw."""
    cue = cue_ms(observations)
    start = cue if cue is not None and cue <= FALLBACK_MS else FALLBACK_MS
    first = next((observation for observation in observations if observation.get("friendly")), {})
    mounted = {unit["id"] for unit in first.get("friendly") or [] if unit.get("type") in MOUNTED}
    kinds = {unit["id"]: unit.get("type") for observation in observations
             for unit in (observation.get("enemy_roster") or []) + (observation.get("enemy") or [])}
    for applied, order in accepted_orders(trace):
        kind = kinds.get(order.get("target"))
        if (applied >= start and order.get("type") == "attack" and order.get("unit") in mounted
                and kind in GUNS | COVER):
            return {"branch": "guns" if kind in GUNS else "cover", "cue_ms": cue,
                    "start_ms": start, "unit": order["unit"], "target": order["target"],
                    "applied_ms": applied}
    return {"branch": "neither", "cue_ms": cue, "start_ms": start}
