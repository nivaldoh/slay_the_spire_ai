"""Evidence rules shared by the siege-set readers and witnesses (portfolio S7).

Deployment matching reads the private initial positions of all units, including hidden enemies.
Readers also use the public ticket counts and the trace of orders the engine acknowledged.
"""


from twwarhammer3.battle.setup import match_deployment


def accepted_orders(trace):
    """(applied ms, order) in acknowledgement order from one episode's trace.jsonl.

    Match a decision's request and its one-based result indices, as play._drive writes them.
    Missing acknowledgements, unreadable indices and rejected orders contribute nothing.
    An accepted order (including a queued order) is not evidence that the unit acted on it.
    """
    orders = {row["request"]: row["orders"] for row in trace if row.get("kind") == "decision"}
    for row in trace:
        ack = row.get("ack") if row.get("kind") == "ack" else None
        if not ack or ack.get("applied_ms") is None:
            continue
        sent = orders.get(row.get("request", ack.get("request"))) or []
        for result in ack.get("results") or []:
            index = result.get("index")
            if result.get("ok") is True and isinstance(index, int) and 0 < index <= len(sent):
                yield ack["applied_ms"], sent[index - 1]


def defender_tickets(mode) -> int | None:
    """The siege defender's tickets: our row when we defend, the enemy's when we attack. None
    when the battle has no row for the defender (a battle without tickets)."""
    side = {"defender": "us", "attacker": "enemy"}[mode["role"]]
    return next((row["tickets"] for row in mode.get("tickets") or [] if row["side"] == side),
                None)


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
