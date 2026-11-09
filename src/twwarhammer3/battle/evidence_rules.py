"""Evidence rules shared by the siege-set readers and witnesses (portfolio S7).

Every rule except ``group_ids`` reads public fields: the unit records and ``mode`` of the
observation or of a 1 Hz replay frame, which carries the same fields (``unit_record`` and
``mode_section`` in the battle Lua; the field list is in engine/mailbox.py). ``group_ids`` reads
the private first reading in ``setup``, which holds the start position of every enemy unit,
hidden ones included, so it stays out of policy code. Facts recorded in the traces the tests copy:
- No unit flagged melee in an attack smoke with 364 friendly-enemy pairs within 40 m (closest
  10.1 m), nor in a defence pair 1.7 m apart, while a defender read melee with no visible enemy
  within 41 m.
- The melee flag stays on friendly units with no men left, and on live enemy units 61-168 m
  from every friendly unit.
- Two gates read hp 0 with ``destroyed`` false from that moment to the end of the battle.
- Engine unit classes mislead: the Magma Cannon reads missile_chariot, Bull Centaurs infantry.
"""

from twwarhammer3.battle.setup import match_deployment


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


# JUDGEMENT: Breach rule — Claude, 2026-11-08 (portfolio S7b): a gate is breached at public hp 0 or
# below, ignoring ``destroyed``. Whether hp 0 lets units through is unverified; Haengju's fallback
# cue, Malta's fall-back rule and Izmail's Horse rule, D2 cue and C5 control rest on it.
def gate_breached(gate) -> bool:
    """Whether a ``mode.gates`` entry is breached. Its ``hp`` is a whole percentage of the gate's
    maximum, rounded, so a gate under 0.5% of its maximum also reads 0; never compare it with raw
    native hit points. Gates share the name "Gatehouse"; tell them apart by position. A gate with
    no hp (no readable maximum) is not breached."""
    hp = gate.get("hp")
    return hp is not None and hp <= 0


def defender_tickets(mode) -> int | None:
    """The siege defender's tickets: our row when we defend, the enemy's when we attack. None
    when the battle has no row for the defender (a battle without tickets)."""
    side = {"defender": "us", "attacker": "enemy"}[mode["role"]]
    return next((row["tickets"] for row in mode.get("tickets") or [] if row["side"] == side),
                None)


def holds(point, side) -> bool:
    """Whether ``side`` ("us" or "enemy") holds a ``mode.capture_points`` entry. A neutral
    point has no ``holder`` key and is held by neither side."""
    return point.get("holder") == side


# JUDGEMENT?: Group membership — Claude, 2026-11-08 (portfolio S7d): fixed by the placement each
# unit matched at the first observation. Regrouping by current position gives other group contact
# times and spreads; Alesia's group readings and Haengju's division readings rest on it.
def group_ids(scenario, first, side, groups) -> dict[str, list[str]]:
    """Unit ids of each named group of one-based ``deployment`` slots on ``side``, in slot
    order. ``setup.match_deployment`` binds units to placements from the private reading in
    ``first`` (the first observation); an observation without that reading is refused, so a
    group never follows where its units are now."""
    placements = scenario["deployment"][side]
    # match_deployment returns the scenario's own placement dicts, so identity finds the slot.
    bound = {id(wanted): unit["id"] for wanted, unit, _ in match_deployment(scenario, first)}
    return {name: [bound[id(placements[slot - 1])] for slot in slots]
            for name, slots in groups.items()}


def ids_by_type(units, keys) -> list[str]:
    """Ids of the units (unit records or ``enemy_roster`` entries) whose type key is in
    ``keys``. Never select by ``class``: the Magma Cannon reads missile_chariot and the Bull
    Centaurs read infantry."""
    return [unit["id"] for unit in units if unit.get("type") in keys]
