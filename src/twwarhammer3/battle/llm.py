"""API language-model commander over battle observations: the prompt, memory and replies.

This file and ``configs/twwarhammer3/`` are the autoresearch loop's editable surface;
transport, prices and spend live in ``gameai.llm``. Memory is bounded: model-written
notes (rewritten through the reply's ``notes`` field), the last few decisions with the
engine's verdict on them, and where enemies were last seen. No transcript accumulates.
"""

import hashlib
import json
import math
import re
from collections import deque

from gameai.ledger import Ledger
from gameai.llm import InvalidReply, Model
from gameai.provenance import REPO_ROOT
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
            _order_schema("ability", ability={"type": "string"}, target=STRING_OR_NULL,
                          x=NUMBER_OR_NULL, z=NUMBER_OR_NULL, facing=NUMBER_OR_NULL,
                          width=NUMBER_OR_NULL),
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


def _distance(unit: dict, other: dict | None) -> str:
    if not other or None in (unit.get("x"), unit.get("z"), other.get("x"), other.get("z")):
        return ""
    return f" {math.hypot(other['x'] - unit['x'], other['z'] - unit['z']):.0f} m"


def _short_of(unit: dict, order: dict) -> float:
    return math.hypot(order["x"] - unit["x"], order["z"] - unit["z"])


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
    return bool(unit.get("dest")) or _short_of(unit, order) > ARRIVED_M


def render_target(unit: dict, enemies: dict, order: dict | None) -> str:
    """The enemy the unit is fighting now, against the order it holds."""
    shown = unit.get("target")
    here = f"target {shown}{_distance(unit, enemies.get(shown))}" if shown else ""
    if unit.get("command_queue"):
        return here
    order = order or {}
    if order.get("type") == "attack":
        if shown == order["target"]:
            return f"{here} (your order, {order['time_s']:.0f} s)"
        return (f"{here}, game's choice; your order at {order['time_s']:.0f} s was"
                f" {order['target']}{_distance(unit, enemies.get(order['target']))}")
    if order.get("type") == "move" and not unit.get("dest"):
        stopped = (f"stopped {_short_of(unit, order):.0f} m short of your move"
                   f" ({order['time_s']:.0f} s)")
        return f"{here}, game's choice; {stopped}" if shown else stopped
    return f"{here}, game's choice" if shown else ""


def render_unit(unit: dict, mine: bool, before: tuple | None = None,
                enemies: dict | None = None, ordered: dict | None = None) -> str:
    """``before`` is (men, hp %) at the previous decision; ``enemies`` and ``ordered`` (the
    attack order the unit holds) annotate a friendly unit's target."""
    if "error" in unit:
        return f"{unit['id']}: unreadable ({unit['error']})"
    if mine and not unit.get("men"):
        return f"{unit['id']} {short_type(unit.get('type'))}: destroyed"
    men0, hp0 = before or (None, None)
    parts = [
        f"{unit['id']} {short_type(unit.get('type'))} ({unit.get('class', '?')}) {_position(unit)}",
        f"{unit.get('men', 0)}/{unit.get('men0', 0)} men{_change(unit.get('men', 0), men0)}",
        f"hp {_hp(unit)}%{_change(_hp(unit), hp0)}",
    ]
    if mine and unit.get("ammo0"):
        parts.append(f"ammo {unit['ammo']}/{unit['ammo0']} range {unit.get('range') or 0:.0f}")
    elif not mine and unit.get("range"):
        parts.append(f"range {unit['range']:.0f}")
    if mine:
        walk, run = unit.get("speed") or (0, 0)
        # The game's Lua numbers are 32-bit floats: 1.9 arrives as 1.8999999761581.
        parts.append(f"walk {walk or 0:.1f} run {run or 0:.1f}")
        parts.append(unit.get("fatigue") or "fresh")
        if unit.get("width"):
            parts.append(f"formation width {unit['width']:.0f} m")
        if unit.get("attack_mode"):
            parts.append(f"last requested attack mode {unit['attack_mode']}")
        if unit.get("behaviours"):
            parts.append("toggles " + " ".join(
                f"{key}={'on' if value else 'off'}" for key, value in unit["behaviours"].items()))
        if unit.get("abilities"):
            parts.append("abilities " + "; ".join(
                f"{a['key']} ({'available' if a.get('can_use') else 'unavailable'})"
                for a in unit["abilities"]))
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
    leaving = {"routing", "shattered"} & set(unit.get("state") or [])
    if mine and not unit.get("target") and not leaving:
        if not (target or unit.get("dest")):
            parts.append("no order")
        if nearest := _nearest(unit, enemies or {}):
            parts.append(f"nearest enemy {nearest['id']}{_distance(unit, nearest)}")
    return ", ".join(parts)


def _nearest(unit: dict, enemies: dict) -> dict | None:
    placed = [enemy for enemy in enemies.values() if enemy.get("x") is not None]
    if unit.get("x") is None or not placed:
        return None
    return min(placed, key=lambda e: math.hypot(e["x"] - unit["x"], e["z"] - unit["z"]))


def render_state(observation: dict, last_seen: dict, before: dict | None = None,
                 ordered: dict | None = None) -> str:
    """``before`` maps unit ids to (men, hp %) at the previous decision, ``ordered`` our
    units to the attack order they hold."""
    visible = visible_enemies(observation)
    before, ordered = before or {}, ordered or {}
    lines = ["Your units:"]
    lines += ["- " + render_unit(unit, True, before.get(unit["id"]), visible,
                                 ordered.get(unit["id"]))
              for unit in observation.get("friendly", [])]
    roster = observation.get("enemy_roster") or []
    lines.append("Enemy roster: " + (", ".join(
        f"{unit['id']} {short_type(unit.get('type'))}{' (destroyed)' if unit.get('dead') else ''}"
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


def render_timing(observation: dict, latency: dict | None) -> str:
    seconds = observation.get("time_ms", 0) / 1000
    remaining = observation.get("remaining_ms", -1)
    limit = f", {remaining / 1000:.0f} s left" if remaining and remaining >= 0 else ""
    text = f"Timing: battle time {seconds:.0f} s{limit}, speed {observation.get('speed', 1)}."
    if observation.get("awaiting_orders"):
        text += " The battle is paused until you reply; your orders apply at once."
    elif latency:
        text += (f" Your last orders took effect {latency['delay_ms'] / 1000:.1f} s after the"
                 f" state you saw (you took {latency['think_s']:.1f} s to reply). Expect a"
                 " similar delay now.")
    else:
        text += " Your orders will take effect a few seconds after this state."
    return text


def render_ack(ack: dict | None) -> str:
    if not ack:
        return "Last orders: none yet."
    results = ack.get("results") or []
    if not results:
        return "Last orders: none (units continued)."
    verdicts = []
    for result in results:
        label = result["unit"] + (f" #{result['index']}" if "index" in result else "")
        verdict = "queued" if result.get("queued") else "applied"
        if not result.get("ok"):
            verdict = "rejected: " + str(result.get("error"))
        verdicts.append(f"{label} {verdict}")
    return "Last orders: " + "; ".join(verdicts) + "."


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
        elif order["type"] == "ability":
            target = order.get("target") or "self"
            if order.get("x") is not None:
                target = f"({order['x']:.0f}, {order['z']:.0f})"
            parts.append(f"{order['unit']} ability {order['ability']} at {target}")
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
        for unit in observation.get("enemy", []):
            if unit.get("x") is not None:
                self.last_seen[unit["id"]] = {
                    "x": unit["x"], "z": unit["z"], "men": unit.get("men", 0),
                    "time_ms": observation.get("time_ms", 0),
                }
        for unit in observation.get("enemy_roster", []):
            if unit.get("dead"):
                self.last_seen.pop(unit["id"], None)
        friendly = friendly_units(observation)
        self.ordered = {unit_id: order for unit_id, order in self.ordered.items()
                        if unit_id in friendly and holds(friendly[unit_id], order)}
        prompt = render_prompt(observation, self.notes, list(self.history), self.last_seen,
                               self.latency, self.ack, self.before, self.ordered)
        self.before = {unit["id"]: (unit.get("men", 0), _hp(unit))
                       for unit in observation.get("friendly", []) + observation.get("enemy", [])}
        self._metadata = metadata = {
            "type": "llm", "model": self.api.name, "effort": self.api.effort,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "prompt": prompt,
        }
        try:
            reply, metadata["attempts"] = self.api.ask(
                prompt, REPLY_SCHEMA, lambda text: parse_reply(text, observation),
                INVALID_RETRIES)
        except InvalidReply as error:
            raise PolicyFailure(str(error), failure={
                "kind": "invalid_reply", "attempts": error.attempts,
            }) from None
        if reply["notes"] is not None:
            self.notes = reply["notes"][:NOTES_LIMIT]
            metadata["notes"] = self.notes
        seconds = observation.get("time_ms", 0) / 1000
        self.sent = [dict(order, time_s=seconds) for order in reply["orders"]]
        summary = describe_orders(reply["orders"])
        self.history.append(f"{seconds:.0f} s: {summary} ({reply['reason']})")
        metadata["reason"] = reply["reason"]
        return reply["orders"]

    def acknowledge(self, ack: dict, latency: dict) -> None:
        self.ack, self.latency = ack, latency
        for result in ack.get("results") or []:
            if not result.get("ok"):
                continue
            index = result.get("index")
            order = (self.sent[index - 1] if index is not None and 0 < index <= len(self.sent)
                     else next((o for o in self.sent if o["unit"] == result["unit"]), None))
            if not order or order["type"] not in ("move", "attack", "halt"):
                continue
            unit = order["unit"]
            # A submitted queue is not evidence that its final attack has started.
            sequence = [o for o in self.sent if o["unit"] == unit and o.get("queue")]
            if sequence:
                self.ordered.pop(unit, None)
            else:
                self.ordered[unit] = order

    def metadata(self) -> dict:
        return self._metadata
