"""Evaluator readings for the siege attack (ksl-emp-siege-a-v1), descriptive only
(runs/siege-evals-20261108/final-izmail.md, Measurements and Infrastructure I8).

They read a finished battle's records: its public observations (trace.jsonl's observation rows,
whose own units carry ``on_wall``) and the private record (``private.jsonl``, fields in
capture.copy_private_record), which holds every enemy unit, hidden ones included. Nothing here
runs during a battle or reaches a controller. Contact is the engine's melee flag on a unit with
men left (evidence_rules.in_melee's rule, read from the private record's ``melee``), never the
distance between centres: in the 2026-10-14 attack smoke 6 friendly-enemy pairs stood within
40 m, 364 pair readings in all, the closest 10.1 m apart, and none carried the flag. A gate is
breached at public hp 0 or less (evidence_rules.gate_breached). The front line and ``inside``
are the witness's (escalade.front_line, rests on JUDGEMENT? escalade.py Front line).
"""

# The battle's page is docs/twwarhammer3/escalade-eval.md. Its proposed check 7 counts D1 as
# exercised from reallocation() over private frames that start at the end of staging, beside a
# reading from the battle's start, and lancer_losses() is D2's descriptive reading (rests on
# JUDGEMENT docs/twwarhammer3/escalade-eval.md Escalade deciding checks and Escalade claim).
from twwarhammer3.battle.escalade import inside
from twwarhammer3.battle.evidence_rules import gate_breached, holds
from twwarhammer3.battle.scripted import distance

# JUDGEMENT?: Escalade readings — Claude, 2026-11-08 (design Measurements, check 7): a sector is
# its target piece's x plus or minus 60 m; 150 m, 120 s and the gate's 20 m are the design's.
# Wider sectors count more defenders as moved; check 7's exercised reading rests on them.
SECTOR_HALF_M = 60
FAR_M = 150  # a defender that started this far (along x) outside a sector came from elsewhere
WINDOW_MS = 120000  # melee counted this long after the reading's start
GATE_M = 20  # a unit that first comes inside this close to g1 came in by the gate


def contact(unit) -> bool:
    """A private-record unit the engine flags in melee and that still has men."""
    return unit.get("melee") is True and (unit.get("men") or 0) > 0


def sectors(targets, pieces) -> dict:
    """{sector: (x_lo, x_hi)} from the witness's climbing targets ({sector: piece id}) and the
    public fortification list ({id: piece})."""
    return {name: (pieces[piece]["x"] - SECTOR_HALF_M, pieces[piece]["x"] + SECTOR_HALF_M)
            for name, piece in targets.items()}


def _gap(x, span):
    """Metres along x from ``x`` to the span; 0 inside it."""
    return max(span[0] - x, 0, x - span[1])


def reallocation(frames, spans, start_ms, window_ms=WINDOW_MS):
    """For each sector ({name: (x_lo, x_hi)}), the defender units (the private record's enemy
    units) in contact while their x lies in the sector, in the frames from ``start_ms`` to
    ``start_ms + window_ms``, and those of them whose x in the first frame lay more than FAR_M
    outside it: {name: {"melee": [ids], "far": [ids]}}. ``start_ms`` is the first on_wall
    reading, or the end of staging (the defenders moved before any climb in the smoke); None
    when it never came."""
    if start_ms is None:
        return None
    first = {unit["id"]: unit for unit in (frames[0].get("enemy") or [])} if frames else {}
    found = {name: {"melee": set(), "far": set()} for name in spans}
    for frame in frames:
        if not start_ms <= frame["time_ms"] <= start_ms + window_ms:
            continue
        for unit in frame.get("enemy") or []:
            if not contact(unit) or unit.get("x") is None:
                continue
            for name, span in spans.items():
                if _gap(unit["x"], span) == 0:
                    found[name]["melee"].add(unit["id"])
                    began = first.get(unit["id"], {}).get("x")
                    if began is not None and _gap(began, span) > FAR_M:
                        found[name]["far"].add(unit["id"])
    return {name: {key: sorted(ids) for key, ids in value.items()}
            for name, value in found.items()}


def entry_routes(frames, gate, line) -> dict:
    """Each own unit's way in: "ladder" once it reads on_wall true (the engine's flag, never a
    height or a distance), "gate" when it first comes inside ``line`` within GATE_M of
    ``gate`` (g1's public piece) without having read on_wall; units that did neither are left
    out. ``frames`` are public observations or private frames, in battle order."""
    routes, before = {}, {}
    for frame in frames:
        for unit in frame.get("friendly") or []:
            identity = unit["id"]
            if identity in routes or unit.get("x") is None or unit.get("z") is None:
                continue
            if unit.get("on_wall") is True:
                routes[identity] = "ladder"
                continue
            now = inside(line, unit)
            if now and before.get(identity) is False and distance(unit, gate) <= GATE_M:
                routes[identity] = "gate"
            before[identity] = now
    return routes


def lancer_losses(observations, lancers, gate):
    """Men the Lancers (own ids) lost from the first observation to the last one before the
    public gate nearest ``gate`` reads breached; nothing after counts. {"men0", "lost", "share",
    "breach_ms" (None: never breached)}, or None without an observation."""
    men0 = men = breach = None
    for observation in observations:
        gates = [g for g in (observation.get("mode") or {}).get("gates") or []
                 if g.get("x") is not None]
        nearest = min(gates, key=lambda g: distance(g, gate), default=None)
        if nearest is not None and gate_breached(nearest):
            breach = observation["time_ms"]
            break
        men = sum(unit.get("men") or 0 for unit in observation.get("friendly") or []
                  if unit["id"] in lancers)
        men0 = men if men0 is None else men0
    if men0 is None:
        return None
    return {"men0": men0, "lost": men0 - men, "share": (men0 - men) / men0 if men0 else None,
            "breach_ms": breach}


def wall_to_point(observations) -> dict:
    """Battle ms of the first observation in which one of our units reads on_wall, of the first
    in which we hold a victory point (a capture point with ``victory``), and the time from the
    first to the second (negative when a point fell first)."""
    on_wall = held = None
    for observation in observations:
        if on_wall is None and any(unit.get("on_wall") is True
                                   for unit in observation.get("friendly") or []):
            on_wall = observation["time_ms"]
        if held is None and any(point.get("victory") and holds(point, "us") for point in
                                (observation.get("mode") or {}).get("capture_points") or []):
            held = observation["time_ms"]
    return {"on_wall_ms": on_wall, "held_ms": held,
            "delta_ms": held - on_wall if None not in (held, on_wall) else None}
