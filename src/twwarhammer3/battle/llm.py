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
from twwarhammer3.protocol import (
    IllegalActionError,
    PolicyFailure,
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
REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "orders": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "unit": {"type": "string"},
                    "type": {"type": "string", "enum": ["move", "attack", "halt"]},
                    "x": {"type": ["number", "null"]},
                    "z": {"type": ["number", "null"]},
                    "facing": {"type": ["number", "null"]},
                    "target": {"type": ["string", "null"]},
                    "run": {"type": "boolean"},
                },
                "required": ["unit", "type", "x", "z", "facing", "target", "run"],
                "additionalProperties": False,
            },
        },
        "reason": {"type": "string"},
        "notes": {"type": ["string", "null"]},
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


def render_unit(unit: dict, mine: bool) -> str:
    if "error" in unit:
        return f"{unit['id']}: unreadable ({unit['error']})"
    parts = [
        f"{unit['id']} {short_type(unit.get('type'))} ({unit.get('class', '?')}) {_position(unit)}",
        f"{unit.get('men', 0)}/{unit.get('men0', 0)} men",
        f"hp {round(100 * (unit.get('hp') or 0))}%",
    ]
    if mine:
        if unit.get("ammo0"):
            parts.append(f"ammo {unit['ammo']}/{unit['ammo0']} range {unit.get('range', 0)}")
        walk, run = unit.get("speed") or (0, 0)
        parts.append(f"walk {walk} run {run}")
        parts.append(unit.get("fatigue") or "fresh")
    if unit.get("state"):
        parts.append(" ".join(unit["state"]))
    if unit.get("target"):
        parts.append(f"target {unit['target']}")
    if unit.get("dest"):
        parts.append(f"heading to ({unit['dest'][0]:.0f}, {unit['dest'][1]:.0f})")
    return ", ".join(parts)


def render_state(observation: dict, last_seen: dict) -> str:
    visible = visible_enemies(observation)
    lines = ["Your units:"]
    lines += ["- " + render_unit(unit, True) for unit in observation.get("friendly", [])]
    roster = observation.get("enemy_roster") or []
    lines.append("Enemy roster: " + (", ".join(
        f"{unit['id']} {short_type(unit.get('type'))}{' (destroyed)' if unit.get('dead') else ''}"
        for unit in roster) or "unknown"))
    lines.append("Visible enemies:")
    lines += ["- " + render_unit(unit, False) for unit in visible.values()] or ["- none"]
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
    verdicts = [f"{r['unit']} {'applied' if r.get('ok') else 'rejected: ' + str(r.get('error'))}"
                for r in results]
    return "Last orders: " + "; ".join(verdicts) + "."


def render_prompt(observation: dict, notes: str, history: list[str], last_seen: dict,
                  latency: dict | None, ack: dict | None) -> str:
    return "\n\n".join([
        "Battle notes:\n" + (notes or "(none)"),
        "Recent decisions, oldest first:\n" + ("\n".join(history) or "(none)"),
        render_timing(observation, latency),
        render_ack(ack),
        render_state(observation, last_seen),
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
                         + (f" facing {facing:.0f}" if facing is not None else "") + run)
        elif order["type"] == "attack":
            parts.append(f"{order['unit']} attack {order['target']}{run}")
        else:
            parts.append(f"{order['unit']} halt")
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
        prompt = render_prompt(observation, self.notes, list(self.history), self.last_seen,
                               self.latency, self.ack)
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
        summary = describe_orders(reply["orders"])
        self.history.append(f"{seconds:.0f} s: {summary} ({reply['reason']})")
        metadata["reason"] = reply["reason"]
        return reply["orders"]

    def acknowledge(self, ack: dict, latency: dict) -> None:
        self.ack, self.latency = ack, latency

    def metadata(self) -> dict:
        return self._metadata
