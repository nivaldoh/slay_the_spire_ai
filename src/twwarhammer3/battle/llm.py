"""API language-model commander over battle observations: the prompt, memory and replies.

This file and ``configs/twwarhammer3/`` are the autoresearch loop's editable surface;
transport, prices and spend live in ``gameai.llm``. Memory is bounded: model-written
notes (rewritten through the reply's ``notes`` field), the last few decisions with the
engine's verdict on them, and where enemies were last seen. No transcript accumulates.
"""

import hashlib
import json
import re
from collections import deque

from gameai.ledger import Ledger
from gameai.llm import InvalidReply, Model
from gameai.provenance import REPO_ROOT
from twwarhammer3.battle.scripted import distance
from twwarhammer3.protocol import (
    ATTACK_MODES,
    BEHAVIOURS,
    IllegalActionError,
    PolicyFailure,
    friendly_units,
    validate_orders,
    visible_enemies,
)

SYSTEM_PROMPT_PATH = REPO_ROOT / "configs/twwarhammer3/system_prompt.md"
RULES_PROMPT_PATH = SYSTEM_PROMPT_PATH.with_name("rules_prompt.md")
# Every WH3 job shares this spend file, and so one budget; Spire keeps its own.
LEDGER_PATH = REPO_ROOT / "runs/twwarhammer3/llm-spend.jsonl"
MAX_OUTPUT_TOKENS = 4000
NOTES_LIMIT = 2000
HISTORY_LENGTH = 8
INVALID_RETRIES = 2
ARRIVED_M = 15  # a move whose unit stopped this close to the point has been carried out
NUMBER_OR_NULL = {"type": ["number", "null"]}
STRING_OR_NULL = {"type": ["string", "null"]}


def _order_schema(kind: str, **fields) -> dict:
    properties = {"unit": {"type": "string"}, "type": {"type": "string", "enum": [kind]}, **fields}
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


ABILITY_SCHEMA = _order_schema("ability", ability={"type": "string"}, target=STRING_OR_NULL,
                               x=NUMBER_OR_NULL, z=NUMBER_OR_NULL, facing=NUMBER_OR_NULL,
                               width=NUMBER_OR_NULL)
BUILD_SCHEMA = _order_schema("build", slot={"type": "string"}, option={"type": "string"})
FLIGHT_SCHEMA = _order_schema("flight", flying={"type": "boolean"})
REINFORCE_SCHEMA = _order_schema("reinforce", reinforcement={"type": "string"},
                                 zone={"type": "integer"})  # a unit type from the pool
REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "orders": {"type": "array", "items": {"anyOf": [
            _order_schema("move", x={"type": "number"}, z={"type": "number"},
                          facing=NUMBER_OR_NULL, width=NUMBER_OR_NULL,
                          run={"type": "boolean"}, queue={"type": "boolean"}),
            _order_schema("attack", target={"type": "string"},
                          mode={"type": "string", "enum": list(ATTACK_MODES)},
                          run={"type": "boolean"}, queue={"type": "boolean"}),
            _order_schema("halt"),
            _order_schema("behaviour", behaviour={"type": "string", "enum": list(BEHAVIOURS)},
                          enabled={"type": "boolean"}),
            ABILITY_SCHEMA,
            BUILD_SCHEMA,
            REINFORCE_SCHEMA,
            FLIGHT_SCHEMA,
        ]}},
        "reason": {"type": "string"},
        "notes": STRING_OR_NULL,
    },
    "required": ["orders", "reason", "notes"],
    "additionalProperties": False,
}


def short_type(key: str) -> str:
    """``wh3_main_kho_inf_chaos_warriors_0`` -> ``chaos_warriors_0``."""
    return re.sub(r"^wh\d?_[a-z0-9]+_[a-z]{3}_[a-z]{3}_", "", key or "?")


def _position(unit: dict) -> str:
    if unit.get("x") is None or unit.get("z") is None:
        return "unknown position"
    return f"at ({unit['x']:.0f}, {unit['z']:.0f}) facing {unit.get('bearing', 0):.0f}"


def _hp(unit: dict) -> int:
    return round(100 * (unit.get("hp") or 0))


def _change(now: int, before: int | None) -> str:
    return f" ({now - before:+d})" if before is not None and now != before else ""


def _distance_text(unit: dict, other: dict | None) -> str:
    if not other or None in (unit.get("x"), unit.get("z"), other.get("x"), other.get("z")):
        return ""
    return f" {distance(unit, other):.0f} m"


def holds(unit: dict, order: dict) -> bool:
    """Whether the game still carries out ``order`` as far as the state shows: an attack
    while the unit has a target, a move until contact or arrival (or while it stopped
    short, which the state reports); nothing once the unit routs or dies."""
    states = set(unit.get("state") or [])
    if not unit.get("men") or {"routing", "shattered"} & states or order["type"] == "halt":
        return False
    if order["type"] == "attack":
        return bool(unit.get("target"))
    if "melee" in states or unit.get("x") is None:
        return False
    return bool(unit.get("dest")) or distance(unit, order) > ARRIVED_M


def render_target(unit: dict, enemies: dict, order: dict | None) -> str:
    """The enemy the unit is fighting now, against the order it holds."""
    shown = unit.get("target")
    here = f"target {shown}{_distance_text(unit, enemies.get(shown))}" if shown else ""
    if unit.get("command_queue"):
        return here
    order = order or {}
    if order.get("type") == "attack":
        if shown == order["target"]:
            return f"{here} (your order, {order['time_s']:.0f} s)"
        return (f"{here}, game's choice; your order at {order['time_s']:.0f} s was"
                f" {order['target']}{_distance_text(unit, enemies.get(order['target']))}")
    if order.get("type") == "move" and not unit.get("dest"):
        stopped = (f"stopped {distance(unit, order):.0f} m short of your move"
                   f" ({order['time_s']:.0f} s)")
        return f"{here}, game's choice; {stopped}" if shown else stopped
    return f"{here}, game's choice" if shown else ""


def render_unit(unit: dict, mine: bool, before: tuple | None = None,
                enemies: dict | None = None, ordered: dict | None = None) -> str:
    """``before`` is (men, hp %) at the previous decision; ``enemies`` and ``ordered`` (the
    move or attack order it still holds, see ``holds``) annotate a friendly unit's target."""
    if "error" in unit:
        return f"{unit['id']}: unreadable ({unit['error']})"
    if mine and not unit.get("men"):
        return f"{unit['id']} {short_type(unit.get('type'))}: destroyed"
    men0, hp0 = before or (None, None)
    side = f" of alliance {unit['alliance']}" if unit.get("alliance") else ""
    parts = [
        f"{unit['id']} {short_type(unit.get('type'))}{side} ({unit.get('class', '?')})"
        f" {_position(unit)}",
        f"{unit.get('men', 0)}/{unit.get('men0', 0)} men{_change(unit.get('men', 0), men0)}",
        f"hp {_hp(unit)}%{_change(_hp(unit), hp0)}",
    ]
    if unit.get("barrier"):
        barrier = unit["barrier"]
        parts.append(f"barrier {barrier.get('hp', '?')}/{barrier['max_hp']}")
    if unit.get("can_fly"):
        parts.append("can fly, " + ("airborne" if unit.get("flying") else "on the ground"))
    if mine and unit.get("ammo0"):
        parts.append(f"ammo {unit['ammo']}/{unit['ammo0']} range {unit.get('range') or 0:.0f}")
    elif not mine and unit.get("range"):
        parts.append(f"range {unit['range']:.0f}")
    if mine or unit.get("speed"):
        walk, run = unit.get("speed") or (0, 0)
        # The game's Lua numbers are 32-bit floats: 1.9 arrives as 1.8999999761581.
        parts.append(f"walk {walk or 0:.1f} run {run or 0:.1f}")
    if mine:
        parts.append(unit.get("fatigue") or "fresh")
        if unit.get("morale"):
            morale = unit["morale"]
            fraction = morale.get("fraction")
            amount = f"{fraction:.0%}" if fraction is not None else "unknown"
            parts.append(f"leadership {amount}; largest effect: "
                         + (morale.get("effect") or "unknown"))
        if unit.get("flight"):
            flight = unit["flight"]
            parts.append("flight change " + ("available" if flight.get("can_toggle")
                                             else "unavailable")
                         + f"; cooldown {flight.get('cooldown_s', '?')} s")
        if unit.get("width"):
            parts.append(f"formation width {unit['width']:.0f} m")
        if unit.get("attack_mode"):
            parts.append(f"last requested attack mode {unit['attack_mode']}")
        if unit.get("behaviours"):
            parts.append("toggles " + " ".join(
                f"{key}={'on' if value else 'off'}" for key, value in unit["behaviours"].items()))
        if unit.get("abilities"):
            parts.append("abilities " + "; ".join(render_ability(a) for a in unit["abilities"]))
        if unit.get("command_queue"):
            parts.append("last submitted sequence (completion unconfirmed): "
                         + describe_orders(unit["command_queue"]))
    if unit.get("state"):
        parts.append(" ".join(unit["state"]))
    target = (render_target(unit, enemies or {}, ordered) if mine
              else f"target {unit['target']}" if unit.get("target") else "")
    if target:
        parts.append(target)
    if unit.get("dest"):
        parts.append(f"heading to ({unit['dest'][0]:.0f}, {unit['dest'][1]:.0f})")
    if mine and unit.get("navigation"):
        navigation = unit["navigation"]
        rejected = navigation["rejected"]
        alternatives = ", ".join(f"({p['x']:.0f},{p['z']:.0f})"
                                 for p in navigation.get("alternatives") or []) or "none found"
        parts.append(f"unreachable move ({rejected['x']:.0f},{rejected['z']:.0f}); "
                     f"nearby reachable destinations at {navigation['sampled_ms'] / 1000:.1f}s: "
                     + alternatives)
    leaving = {"routing", "shattered"} & set(unit.get("state") or [])
    if mine and not unit.get("target") and not leaving:
        if not (target or unit.get("dest")):
            parts.append("no order")
        if nearest := _nearest(unit, enemies or {}):
            parts.append(f"nearest enemy {nearest['id']}{_distance_text(unit, nearest)}")
    return ", ".join(parts)


def render_ability(ability: dict) -> str:
    """``key (Ground; 8 magic; recharging, 42 s left; last issued 61 s)``: target type, cost
    and readiness as the game's ability panel shows them."""
    facts = [ability["target"]] if ability.get("target") else []
    if ability.get("cast_range", 0) > 0:
        facts.append(f"cast range {ability['cast_range']:.0f} m")
    if ability.get("radius"):
        facts.append(f"radius {ability['radius']:.0f} m")
    if ability.get("duration_s", 0) > 0:
        facts.append(f"duration {ability['duration_s']:.0f} s")
    if ability.get("mana"):
        facts.append(f"{ability['mana']} magic")
    if ability.get("unlocked") is False:
        facts.append(f"locked, unlocks at {ability['cost']:.0f} points" if ability.get("cost")
                     else "locked")
    elif ability.get("can_use") is False:
        facts.append("blocked")
    elif ability.get("active"):
        facts.append("active now")
    elif ability.get("recharge_s"):
        facts.append(f"recharging, {ability['recharge_s']:.0f} s left")
    elif ability.get("timer"):
        # An army ability's HUD timer counts its active time, then its recharge.
        phase = "active now" if ability.get("button") == "selected_inactive" else "recharging"
        facts.append(f"{phase}, {ability['timer']} s left")
    elif ability.get("ready"):
        facts.append("ready")
    elif ability.get("ready") is False:
        facts.append("not available now")
    else:
        facts.append("readiness unknown")
    if ability.get("uses") is not None:
        facts.append(f"{ability['uses']} uses left")
    if ability.get("cooldown_s", 0) > 0:
        facts.append(f"cooldown {ability['cooldown_s']:.0f} s")
    if ability.get("last_issued_ms") is not None:
        facts.append(f"last issued {ability['last_issued_ms'] / 1000:.0f} s")
    return f"{ability['key']} ({'; '.join(facts)})"


def render_army(army: dict) -> str:
    points = f"; points {army['currency']}" if army.get("currency") is not None else ""
    if army.get("next_unlock") is not None:
        points += f", next unlock at {army['next_unlock']}"
    return (f"Army abilities (order with unit \"army\"{points}): "
            + "; ".join(render_ability(a) for a in army.get("abilities", [])))


def _side(side: str | None) -> str:
    return {"us": "you", None: "nobody", "none": "nobody"}.get(side, side)


def render_mode(mode: dict | None) -> str | None:
    """The battle type and what wins it: role, objectives in the game's words, tickets,
    capture points, gates and supplies, as far as the type has them."""
    if not mode or not mode.get("type"):
        return None
    head = f"Battle: {mode['type']}"
    if mode.get("role"):
        head += f"; you are the {mode['role']}"
    winner = mode.get("timeout_winner")
    if winner:
        head += "; if time runs out, " + {"us": "you win", "none": "it is a draw"}.get(
            winner, f"{winner} wins")
    lines = [head + "."]
    if mode.get("objectives"):
        lines.append("The game's description: " + mode["objectives"])
    if mode.get("tickets"):
        # Without a goal (a siege defender's tickets) the income figure does not apply.
        goal = mode.get("tickets_goal")
        lines.append(f"Tickets{f' ({goal} wins)' if goal else ''}: " + ", ".join(
            f"{_side(row['side'])} {row['tickets']}"
            + (f" ({row.get('per_s', 0):+d}/s)" if goal else "")
            for row in mode["tickets"]) + ".")
    if mode.get("capture_points"):
        lines.append("Capture points (units standing on a point capture it):")
        for point in mode["capture_points"]:
            flags = [flag for flag in ("contested", "locked") if point.get(flag)]
            if point.get("victory"):
                flags.append("counts for victory")
            # The engine reads 100% for held and for neutral points alike; less is progress.
            if point.get("percent", 100) < 100:
                flags.insert(0, f"{point['percent']}% captured")
            lines.append(f"- {point['id']} {point.get('name', '')} at ({point['x']:.0f},"
                         f" {point['z']:.0f}): held by {_side(point.get('holder'))}"
                         + "".join(f", {f}" for f in flags))
    for gate in mode.get("gates") or []:
        state = "destroyed" if gate.get("destroyed") else f"{gate.get('hp')}% health"
        lines.append(f"{gate.get('name') or 'Gate'} at ({gate['x']:.0f}, {gate['z']:.0f}):"
                     f" {state}.")
    if mode.get("supplies") is not None:
        lines.append(f"Supplies: {mode['supplies']}.")
    if mode.get("reinforcements") is not None:
        lines.append("Reinforcement pool (order with unit \"army\", type \"reinforce\", the unit"
                     " type as written here and one of your spawn zones; each costs supplies): "
                     + (", ".join(f"{unit.get('type')} {unit.get('cost')}"
                                  for unit in mode["reinforcements"]) or "empty") + ".")
        lines.append("Your spawn zones: " + (", ".join(
            f"{zone['id']} at ({zone['x']:.0f}, {zone['z']:.0f})"
            + (" (refuses purchases now)" if zone.get("usable") is False else "")
            for zone in mode.get("spawn_zones") or []) or "none") + ".")
    if mode.get("slots"):
        lines.append("Building slots (order with unit \"army\", type \"build\", slot and option):")
        for slot in mode["slots"]:
            if slot.get("building_s") is not None:
                state = f"building {slot.get('built')}, {slot['building_s']:.0f} s left"
            elif slot.get("built"):
                state = "built " + slot["built"] + (" (destroyed)" if slot.get("destroyed") else "")
            else:
                state = "empty, options " + ", ".join(
                    f"{option['name']} {option['cost']}" for option in slot.get("options") or [])
                if not slot.get("usable"):
                    state += " (cannot build now)"
            lines.append(f"- {slot['id']} {slot.get('type')} at ({slot['x']:.0f},"
                         f" {slot['z']:.0f}): {state}")
    return "\n".join(lines)


def _nearest(unit: dict, enemies: dict) -> dict | None:
    placed = [enemy for enemy in enemies.values() if enemy.get("x") is not None]
    if unit.get("x") is None or not placed:
        return None
    return min(placed, key=lambda enemy: distance(unit, enemy))


def render_state(observation: dict, last_seen: dict, before: dict | None = None,
                 ordered: dict | None = None) -> str:
    """``before`` maps unit ids to (men, hp %) at the previous decision, ``ordered`` our
    units to the move or attack order they still hold (see ``holds``)."""
    visible = visible_enemies(observation)
    before, ordered = before or {}, ordered or {}
    lines = []
    if observation.get("terrain"):
        terrain = observation["terrain"]
        lines.append(f"Terrain samples: first cell centre ({terrain['x0']},{terrain['z0']}), "
                     f"columns increase x and rows increase z by {terrain['cell_m']} m. "
                     f"'.' = {terrain['sample_width_m']} m square clear of path restrictions; "
                     "'#' = restricted. Coarse deployment snapshot, not a path or a guarantee "
                     "for this unit. Narrow crossings can lie between samples. "
                     "Do not repeat an unreachable move: select a reported reachable "
                     "alternative or another goal.\n" + "\n".join(terrain["rows"]))
    mode = render_mode(observation.get("mode"))
    if mode:
        lines.append(mode)
    if (observation.get("army") or {}).get("abilities"):
        lines.append(render_army(observation["army"]))
    magic = observation.get("magic") or {}
    if magic:
        lines.append(f"Winds of Magic: {magic.get('current', 'unknown')} available, "
                     f"{magic.get('reserve', 'unknown')} reserve.")
    lines.append("Your units:")
    lines += ["- " + render_unit(unit, True, before.get(unit["id"]), visible,
                                 ordered.get(unit["id"]))
              for unit in observation.get("friendly", [])]
    roster = observation.get("enemy_roster") or []
    lines.append("Enemy roster: " + (", ".join(
        f"{unit['id']} {short_type(unit.get('type'))}"
        f"{' of alliance ' + str(unit['alliance']) if unit.get('alliance') else ''}"
        f"{' (destroyed)' if unit.get('dead') else ''}"
        for unit in roster) or "unknown"))
    lines.append("Visible enemies:")
    lines += ["- " + render_unit(unit, False, before.get(unit["id"]))
              for unit in visible.values()] or ["- none"]
    unseen = [
        f"- {unit_id} {_describe_last_seen(seen, observation)}"
        for unit_id, seen in last_seen.items() if unit_id not in visible
    ]
    if unseen:
        lines.append("Last seen, not visible now:")
        lines += unseen
    return "\n".join(lines)


def _describe_last_seen(seen: dict, observation: dict) -> str:
    age = max(0, observation.get("time_ms", 0) - seen["time_ms"]) / 1000
    return f"at ({seen['x']:.0f}, {seen['z']:.0f}) {age:.0f} s ago, {seen['men']} men"


def render_clock(observation: dict) -> str:
    """``Timing: battle time 45 s, 855 s left``, the start of both controllers' timing line."""
    remaining = observation.get("remaining_ms", -1)
    limit = f", {remaining / 1000:.0f} s left" if remaining and remaining >= 0 else ""
    return f"Timing: battle time {observation.get('time_ms', 0) / 1000:.0f} s{limit}"


def render_timing(observation: dict, latency: dict | None) -> str:
    text = f"{render_clock(observation)}, speed {observation.get('speed', 1)}."
    if latency:
        return text + (" Your last batch was issued to the engine"
                       f" {latency['delay_ms'] / 1000:.1f} s after the"
                       f" state you saw (you took {latency['think_s']:.1f} s to reply). Expect a"
                       " similar delay now.")
    return text + " Your batch will reach the engine a few seconds after this state."


def render_ack(ack: dict | None) -> str:
    if not ack:
        return "Last orders: none yet."
    results = ack.get("results") or []
    if not results:
        return "Last orders: none (units continued)."
    verdicts = []
    for result in results:
        label = result["unit"] + (f" #{result['index']}" if "index" in result else "")
        verdict = "queued" if result.get("queued") else "issued"
        if not result.get("ok"):
            verdict = "rejected: " + str(result.get("error"))
        verdicts.append(f"{label} {verdict}")
    return "Last orders: " + "; ".join(verdicts) + "."


def remember(last_seen: dict, observation: dict) -> None:
    """Where each enemy was last seen, until it is reported destroyed."""
    for unit in observation.get("enemy", []):
        if unit.get("x") is not None:
            last_seen[unit["id"]] = {
                "x": unit["x"], "z": unit["z"], "men": unit.get("men", 0),
                "time_ms": observation.get("time_ms", 0),
            }
    for unit in observation.get("enemy_roster", []):
        if unit.get("dead"):
            last_seen.pop(unit["id"], None)


def render_prompt(observation: dict, notes: str, history: list[str], last_seen: dict,
                  latency: dict | None, ack: dict | None, before: dict | None = None,
                  ordered: dict | None = None) -> str:
    return "\n\n".join([
        "Battle notes:\n" + (notes or "(none)"),
        "Recent decisions, oldest first:\n" + ("\n".join(history) or "(none)"),
        render_timing(observation, latency),
        render_ack(ack),
        render_state(observation, last_seen, before, ordered),
    ])


def parse_reply(text: str, observation: dict) -> dict:
    reply = json.loads(text)
    try:
        validate_orders(reply["orders"], observation)
    except IllegalActionError as error:
        raise ValueError(str(error)) from None
    return reply


def split_valid(orders: list[dict], observation: dict) -> tuple[list[dict], list[str]]:
    """The orders that stay valid in turn, and each other one with why it was dropped."""
    kept, dropped = [], []
    for order in orders:
        try:
            validate_orders(kept + [order], observation)
            kept.append(order)
        except IllegalActionError as error:
            dropped.append(f"{describe_orders([order])}: {error}")
    return kept, dropped


def salvage(attempts: list[dict], observation: dict) -> tuple[dict, list[str]] | None:
    """The last attempt's reply without the orders that are still invalid, so one order
    the model keeps repeating (a cast on cooldown, say) does not end the battle; None if
    that reply is not even JSON."""
    try:
        reply = json.loads(attempts[-1]["text"])
    except ValueError:
        return None
    kept, dropped = split_valid(reply["orders"], observation)
    return dict(reply, orders=kept), dropped


def strengths(observation: dict) -> dict[str, tuple]:
    """(men, hp %) of every unit, to show the change at the next decision."""
    return {unit["id"]: (unit.get("men", 0), _hp(unit))
            for unit in observation.get("friendly", []) + observation.get("enemy", [])}


def invalid_reply(error: InvalidReply) -> PolicyFailure:
    return PolicyFailure(str(error), failure={"kind": "invalid_reply", "attempts": error.attempts})


def describe_orders(orders: list[dict]) -> str:
    if not orders:
        return "no new orders"
    parts = []
    for order in orders:
        run = " run" if order.get("run") else ""
        if order["type"] == "move":
            facing = order.get("facing")
            parts.append(f"{order['unit']} move ({order['x']:.0f}, {order['z']:.0f})"
                         + (f" facing {facing:.0f}" if facing is not None else "")
                         + (f" width {order['width']:.0f}" if order.get("width") else "") + run)
        elif order["type"] == "attack":
            mode = "" if order.get("mode", "auto") == "auto" else f" {order['mode']}"
            parts.append(f"{order['unit']} attack {order['target']}{mode}{run}")
        elif order["type"] == "behaviour":
            parts.append(f"{order['unit']} {order['behaviour']} "
                         + ("on" if order["enabled"] else "off"))
        elif order["type"] == "flight":
            parts.append(f"{order['unit']} " + ("take off" if order["flying"] else "land"))
        elif order["type"] == "ability":
            target = order.get("target") or "self"
            if order.get("x") is not None and order.get("z") is not None:
                target = f"({order['x']:.0f}, {order['z']:.0f})"
            parts.append(f"{order['unit']} ability {order['ability']} at {target}")
        elif order["type"] == "build":
            parts.append(f"{order['unit']} build {order['option']} on {order['slot']}")
        elif order["type"] == "reinforce":
            parts.append(f"{order['unit']} reinforce {short_type(order['reinforcement'])}"
                         f" at zone {order['zone']}")
        else:
            parts.append(f"{order['unit']} halt")
        if order.get("queue"):
            parts[-1] += " [queued]"
    return ", ".join(parts)


class LLMPolicy:
    """One instance per episode: its notes, history and last-seen map are the memory."""

    def __init__(self, model: str, effort: str, ledger: Ledger, *, send=None,
                 system_prompt: str | None = None):
        self.api = Model(model, effort, ledger, send=send,
                         instructions=system_prompt or SYSTEM_PROMPT_PATH.read_text(),
                         max_output_tokens=MAX_OUTPUT_TOKENS)
        self.totals = self.api.totals
        self.notes = ""
        self.history: deque[str] = deque(maxlen=HISTORY_LENGTH)
        self.last_seen: dict[str, dict] = {}
        self.latency = None
        self.ack = None
        self.before: dict[str, tuple] = {}
        self.sent: list[dict] = []
        self.ordered: dict[str, dict] = {}
        self._metadata = {}

    def decide(self, observation: dict) -> list[dict]:
        remember(self.last_seen, observation)
        friendly = friendly_units(observation)
        self.ordered = {unit_id: order for unit_id, order in self.ordered.items()
                        if unit_id in friendly and holds(friendly[unit_id], order)}
        prompt = render_prompt(observation, self.notes, list(self.history), self.last_seen,
                               self.latency, self.ack, self.before, self.ordered)
        self.before = strengths(observation)
        self._metadata = metadata = {
            "type": "llm", "model": self.api.name, "effort": self.api.effort,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "prompt": prompt,
        }
        try:
            reply, metadata["attempts"] = self.api.ask(
                prompt, REPLY_SCHEMA, lambda text: parse_reply(text, observation),
                INVALID_RETRIES)
        except InvalidReply as error:
            salvaged = salvage(error.attempts, observation)
            if salvaged is None:
                raise invalid_reply(error) from None
            reply, metadata["dropped"] = salvaged
            metadata["attempts"] = error.attempts
        if reply["notes"] is not None:
            self.notes = reply["notes"][:NOTES_LIMIT]
            metadata["notes"] = self.notes
        seconds = observation.get("time_ms", 0) / 1000
        self.sent = [dict(order, time_s=seconds) for order in reply["orders"]]
        summary = describe_orders(reply["orders"])
        if metadata.get("dropped"):
            summary += "; dropped as still invalid: " + "; ".join(metadata["dropped"])
        self.history.append(f"{seconds:.0f} s: {summary} ({reply['reason']})")
        metadata["reason"] = reply["reason"]
        return reply["orders"]

    def acknowledge(self, ack: dict, latency: dict) -> None:
        self.ack, self.latency = ack, latency
        accepted = []
        for result in ack.get("results") or []:
            if not result.get("ok"):
                continue
            index = result.get("index")
            order = (self.sent[index - 1] if index is not None and 0 < index <= len(self.sent)
                     else next((o for o in self.sent if o["unit"] == result["unit"]), None))
            if not order or order["type"] not in ("move", "attack", "halt"):
                continue
            accepted.append(order)
        # A submitted queue is not evidence that its final attack has started.
        queued = {order["unit"] for order in accepted if order.get("queue")}
        for order in accepted:
            if order["unit"] in queued:
                self.ordered.pop(order["unit"], None)
            else:
                self.ordered[order["unit"]] = order

    def metadata(self) -> dict:
        return self._metadata
