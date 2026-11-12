"""Evaluator readings for the two-front land defence (ksl-nor-lines-a-v1, -b-v1), descriptive only
(docs/twwarhammer3/lines-eval.md, Measurements and proposed checks 2-4 and 2b).

They read a finished battle's records: the private record (``private.jsonl``, fields in
capture.copy_private_record), the trace's "decision" and "ack" rows, and the public observations
(trace.jsonl's observation rows). Nothing here runs during a battle or reaches a controller. The
geometry is the witness's (battle/lines.py) taken from the declared placements: the outer line's
centre and front, and the split at that centre's x (130), which is also the cases' mirror axis.
The midpoint between the two lines' centres, (130, -230) in both cases, separates the outer front
from the town side.
H is the page's heavy relief group (two Marauder Champions, the Berserkers and the Fimir), on
the side of the split where the declaration places it; L is the other relief group. The tests use
synthetic records. The first case-a original-engine record and its independent recount are
documented in lines-eval.md, First construction battle (2026-11-12).
"""

import math

from twwarhammer3.battle.calibration import _active, _centre, _direction
from twwarhammer3.battle.evidence_rules import group_ids, ids_by_type
from twwarhammer3.battle.lines import AHEAD_M, BOYAR, GUARD, LANCERS, LINE, TRIGGER_UNITS
from twwarhammer3.protocol import ProtocolError, visible_enemies

HEAVY = {"wh_dlc08_nor_inf_marauder_champions_0", "wh_dlc08_nor_inf_marauder_berserkers_0",
         "wh_dlc08_nor_mon_fimir_0"}
# One-based friendly slots of the declared outer line's two westmost and two eastmost regiments
# (lines-eval.md Map and placements): the sectors lines.py binds from start positions.
SECTORS = {"west": [8, 9], "east": [11, 12]}
MOVERS = {GUARD, BOYAR, LANCERS}
# Rests on JUDGEMENT docs/twwarhammer3/lines-eval.md Lines layout and Lines deciding checks,
# and JUDGEMENT? src/twwarhammer3/battle/evidence_rules.py Group membership.
CONTACT_GROUPS = {"G": [1, 2, 3, 4], "H": [5, 6, 7, 8], "L": [9, 10, 11, 12]}


def _front(declaration):
    """The declared outer line's centre, its front (the unit direction from the inner line's
    centre to the outer line's: the rule of lines.LinesWitness._bind, on declared placements)
    and the midpoint between the two lines' centres."""
    line = [p for p in declaration["deployment"]["friendly"] if p["type"] in LINE]
    middle = (max(p["z"] for p in line) + min(p["z"] for p in line)) / 2
    outer = _centre([p for p in line if p["z"] <= middle])
    inner = _centre([p for p in line if p["z"] > middle])
    halfway = {"x": (outer["x"] + inner["x"]) / 2, "z": (outer["z"] + inner["z"]) / 2}
    return outer, _direction(inner, outer), halfway


def _ahead(point, origin, forward):
    """Metres ``point`` stands ahead of ``origin`` along ``forward``."""
    return (point["x"] - origin["x"]) * forward[0] + (point["z"] - origin["z"]) * forward[1]


def _side(point, split):
    return "west" if point["x"] < split else "east" if point["x"] > split else None


def h_side(declaration) -> str:
    """The side of the split ("west" or "east") on which the declaration places H."""
    split = _front(declaration)[0]["x"]
    sides = {_side(p, split) for p in declaration["deployment"]["enemy"] if p["type"] in HEAVY}
    if len(sides) != 1 or None in sides:
        raise ValueError("the declaration does not place H on one side of the split")
    return sides.pop()


# JUDGEMENT?: Complete contact record — Codex, 2026-11-10: this draft requires complete private
# enemy identities and men/melee fields in every frame; partial replay inference could change
# first-contact times. Adoption of this input contract remains for owner review.
def contacts(frames, declaration, first) -> dict:
    """Descriptive first living-melee samples and G/H/L contact times; no pass verdict.

    ``first`` is the original observation with its private setup.deployment_reading and battle
    identity. ``frames`` are that battle's private.jsonl rows, in battle order. They use boolean
    ``melee`` (capture.copy_private_record), not a public replay's state list. Each must contain
    every registered enemy, including dead units, with readable men and melee; unavailable
    evidence is refused. Missing point coordinates remain None. No timing is interpolated.

    Groups bind once to authored slots through group_ids. Stable episode identities follow
    SMACv2 smacv2/env/starcraft2/starcraft2.py init_units/update_units at 577ab5a (references.md);
    these WH3 records use the existing deployment matcher. The two-of-four contact rule rests
    on JUDGEMENT docs/twwarhammer3/lines-eval.md Lines deciding checks and on JUDGEMENT
    src/twwarhammer3/battle/evidence_rules.py Contact rule. No contact is None, never zero.
    """
    groups = group_ids(declaration, first, "enemy", CONTACT_GROUPS)
    identities = [identity for members in groups.values() for identity in members]
    if any(not isinstance(identity, str) or not identity for identity in identities):
        raise ProtocolError("private initial enemy identities must be nonempty strings")
    expected = set(identities)
    if len(expected) != len(identities):
        raise ProtocolError("private initial enemy identities are not unique")
    battle = first.get("battle")
    if not isinstance(battle, str) or not battle:
        raise ProtocolError("private contact reading needs its initial battle identity")
    contact_ms = dict.fromkeys(groups)
    first_melee = dict.fromkeys(identities)
    for frame in frames:
        version = frame.get("private_record")
        if isinstance(version, bool) or version != 1:
            raise ProtocolError("contact reading requires private_record version 1")
        if frame.get("battle") != battle:
            raise ProtocolError("contact reading contains a different battle")
        rows = frame.get("enemy") or []
        units = {unit.get("id"): unit for unit in rows}
        if len(units) != len(rows) or set(units) != expected:
            raise ProtocolError("private contact reading needs the exact unique enemy roster")
        for unit in rows:
            men = unit.get("men")
            if type(men) not in (int, float) or not math.isfinite(men) \
                    or type(unit.get("melee")) is not bool:
                raise ProtocolError("private contact reading has unreadable men/melee")
        engaged = {identity for identity, unit in units.items()
                   if unit["melee"] and unit["men"] > 0}
        for identity in engaged:
            if first_melee[identity] is None:
                first_melee[identity] = {"time_ms": frame["time_ms"],
                                         "x": units[identity].get("x"),
                                         "z": units[identity].get("z")}
        for name, members in groups.items():
            if contact_ms[name] is None and len(engaged.intersection(members)) >= 2:
                contact_ms[name] = frame["time_ms"]
    times = list(contact_ms.values())
    spread = max(times) - min(times) if all(time is not None for time in times) else None
    return {"battle": battle, "groups": groups, "contact_ms": contact_ms,
            "contact_spread_ms": spread, "first_melee": first_melee}


# JUDGEMENT?: Sector rout reading — Claude, 2026-11-09 (second look A1): a sector's first rout is
# its first unit reading routing true in the private record. Counting shattered or dead units
# moves the rout times; proposed check 2b rests on it.
def sector_routs(frames, declaration) -> dict:
    """Battle ms of the first private-record frame in which a unit of each sector reads
    ``routing`` true, and the same for every other friendly unit ("other": the middle regiment,
    the inner line, the reserve and the Lancers); None where no unit did. Membership is bound
    once, at the first frame with friendly units, to the declared placements by type and place
    (evidence_rules.group_ids, which refuses a unit more than 25 m from its place), so a unit
    stays in its sector wherever it stands when it routs. A unit read only as shattered or dead
    is not counted; whether the engine also reads routing on a shattered unit is unread."""
    routs = dict.fromkeys(("west", "east", "other"))
    first = next((frame for frame in frames if frame.get("friendly")), None)
    if first is None:
        return routs
    placed = {"deployment": {"friendly": declaration["deployment"]["friendly"]}}
    reading = {"setup": {"deployment_reading": {"friendly": first["friendly"]}}}
    member = {identity: name for name, ids in
              group_ids(placed, reading, "friendly", SECTORS).items() for identity in ids}
    for frame in frames:
        for unit in frame.get("friendly") or []:
            name = member.get(unit["id"], "other")
            if unit.get("routing") is True and routs[name] is None:
                routs[name] = frame["time_ms"]
    return routs


def _trigger_ms(observations, declaration):
    """Battle ms of the first public observation in which TRIGGER_UNITS visible enemies with men,
    not routing, stand more than AHEAD_M ahead of the declared outer line along its front: the
    witness's cue (lines.py, rule 4), computed for any controller. None if it never came."""
    outer, forward, _ = _front(declaration)
    for observation in observations:
        ahead = sum(_ahead(enemy, outer, forward) > AHEAD_M
                    for enemy in _active(visible_enemies(observation).values()))
        if ahead >= TRIGGER_UNITS:
            return observation["time_ms"]
    return None


# JUDGEMENT?: Lines branch reading — Claude, 2026-11-09 (second look B1): the side of x = 130 of
# the first accepted reserve or Lancer order at or after the cue that aims past the lines' midpoint.
# Positions, a later order, or town-side orders by x or as "other" change a model's branch shares.
def branch(trace, observations, declaration) -> dict:
    """Which relief group a controller, any controller, sent the reserve or the Lancers to first:
    {"label": "H", "L" or "neither", "side", "trigger_ms", "unit", "applied_ms"}. The order is
    the first accepted one (its ack result ok) that moves or attacks with the Tzar Guard, the
    Boyar or a Winged Lancers unit (by type at the first observation), in a decision based on an
    observation at or after the cue (``_trigger_ms``), taken in trace and list order, whose point
    stands ahead of the midpoint between the two lines. Its point is its destination, or for an
    attack its target's position in the decision's observation. An order toward the inner line or
    the town side, an order on the split and a target that observation lacks are skipped. A
    Lancers move back to its start post (z -245) counts by its side. "neither" when no such order
    came: C until a leash fight, or a controller that never sends those units past the midpoint.
    ``trace`` holds the episode's trace.jsonl rows; ``observations`` are its public observations,
    in battle order."""
    outer, forward, halfway = _front(declaration)
    split, heavy = outer["x"], h_side(declaration)
    trigger = _trigger_ms(observations, declaration)
    first = next((o for o in observations if o.get("friendly")), {})
    movers = set(ids_by_type(first.get("friendly") or [], MOVERS))
    seen = {o["seq"]: o for o in observations}
    acks = {row["request"]: row["ack"] for row in trace if row.get("kind") == "ack"}
    for row in trace:
        if trigger is None or row.get("kind") != "decision" or row["time_ms"] < trigger:
            continue
        ack = acks.get(row["request"]) or {}
        accepted = {r.get("index") for r in ack.get("results") or [] if r.get("ok") is True}
        for index, order in enumerate(row.get("orders") or [], 1):
            if index not in accepted or order.get("unit") not in movers \
                    or order.get("type") not in ("move", "attack"):
                continue
            point = order if order["type"] == "move" else visible_enemies(
                seen.get(row["seq"], {})).get(order.get("target"))
            if not point or point.get("x") is None or point.get("z") is None \
                    or _ahead(point, halfway, forward) <= 0:
                continue
            side = _side(point, split)
            if side:
                return {"label": "H" if side == heavy else "L", "side": side,
                        "trigger_ms": trigger, "unit": order["unit"],
                        "applied_ms": ack.get("applied_ms")}
    return {"label": "neither", "side": None, "trigger_ms": trigger, "unit": None,
            "applied_ms": None}
