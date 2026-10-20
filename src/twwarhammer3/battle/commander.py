"""Asynchronous API-model commander over the skills executor (``--policy commander``).

The model gives units standing assignments (a skill from ``skills.py`` with an optional
target and point); the executor carries them out on every observation. One plan request
is in flight at a time on a worker thread, so ``decide`` never waits: it adopts a finished
plan against the current state, runs the executor, and asks again from the latest state.
Memory is bounded: the model's notes, the last few plans, assignments dropped or orders
rejected since the last request, and where enemies were last seen.
"""

import hashlib
import json
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor

from gameai.ledger import Ledger
from gameai.llm import InvalidReply, Model, check_fields
from gameai.provenance import REPO_ROOT
from twwarhammer3.battle.llm import (
    ABILITY_SCHEMA,
    BUILD_SCHEMA,
    FLIGHT_SCHEMA,
    MAX_OUTPUT_TOKENS,
    NOTES_LIMIT,
    NUMBER_OR_NULL,
    REASON_LIMIT,
    REINFORCE_SCHEMA,
    STRING_OR_NULL,
    describe_dropped,
    describe_orders,
    holds,
    invalid_reply,
    remember,
    render_clock,
    render_state,
    split_valid,
    strengths,
)
from twwarhammer3.battle.skills import SKILLS, Skills
from twwarhammer3.protocol import friendly_units

PROMPT_PATH = REPO_ROOT / "configs/twwarhammer3/commander_prompt.md"
INVALID_RETRIES = 1  # only a reply off the schema is invalid; the plan is checked on arrival
PLAN_HISTORY = 6
REPORT_LENGTH = 8
REPORT_HEADER = "Dropped or rejected since your last plan:\n"
ABILITY_TYPES = ("ability", "build", "reinforce", "flight")  # the skills give the rest
ASSIGNMENT_SCHEMA = {
    "type": "object",
    "properties": {"unit": {"type": "string"}, "skill": {"type": "string", "enum": list(SKILLS)},
                   "target": STRING_OR_NULL, "x": NUMBER_OR_NULL, "z": NUMBER_OR_NULL},
    "required": ["unit", "skill", "target", "x", "z"],
    "additionalProperties": False,
}
REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "assignments": {"type": "array", "items": ASSIGNMENT_SCHEMA},
        "abilities": {"type": "array",
                      "items": {"anyOf": [ABILITY_SCHEMA, BUILD_SCHEMA, REINFORCE_SCHEMA,
                                          FLIGHT_SCHEMA]}},
        "reason": {"type": "string"},
        "notes": STRING_OR_NULL,
    },
    "required": ["assignments", "abilities", "reason", "notes"],
    "additionalProperties": False,
}


def parse_plan(text: str) -> dict:
    reply = check_fields(json.loads(text), REPLY_SCHEMA)
    # A plan's readers take a missing target, x or z as null.
    fields = dict(ASSIGNMENT_SCHEMA, required=["unit", "skill"])
    for index, item in enumerate(reply["assignments"], 1):
        check_fields(item, fields, f"assignment {index}")
    return reply


def describe_assignment(item: dict) -> str:
    text = f"{item['unit']} {item['skill']}"
    if item.get("target"):
        text += f" {item['target']}"
    if item.get("x") is not None and item.get("z") is not None:
        text += f" ({item['x']:.0f}, {item['z']:.0f})"
    return text


def describe_plan(assignments: list[dict]) -> str:
    return "; ".join(describe_assignment(item) for item in assignments) or "no changes"


def render_assignments(skills: Skills, observation: dict) -> str:
    lines = ["Assignments (skill, target, point; since; what the executor is doing):"]
    for unit in observation.get("friendly", []):
        item = skills.assignments.get(unit["id"])
        if item:
            lines.append(f"- {describe_assignment({'unit': unit['id'], **item})}"
                         f" (since {item['since_s']:.0f} s): {skills.phase.get(unit['id'], '')}")
    return "\n".join(lines)


def render_timing(observation: dict, age_ms: int | None) -> str:
    text = render_clock(observation) + "."
    if age_ms is None:
        return text + " Units follow their default skills until your first plan arrives."
    return (text + f" Your last plan reached the units {age_ms / 1000:.1f} s after the state"
            " it was based on; expect a similar delay now.")


class CommanderPolicy:
    """One instance per episode; ``close`` waits for the request still in flight."""

    def __init__(self, model: str, effort: str, ledger: Ledger, *, send=None,
                 system_prompt: str | None = None, provider: str = "openai"):
        self.api = Model(model, effort, ledger, send=send, provider=provider,
                         instructions=system_prompt or PROMPT_PATH.read_text(),
                         max_output_tokens=MAX_OUTPUT_TOKENS, record_exchanges=True)
        self.skills = Skills()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.pending = None
        self.plans = Counter()
        self.notes = ""
        self.history: deque[str] = deque(maxlen=PLAN_HISTORY)
        self.report: deque[str] = deque(maxlen=REPORT_LENGTH)
        self.last_seen: dict[str, dict] = {}
        self.before: dict[str, tuple] = {}
        self.age_ms = None
        self.batch: list[dict] = []
        self._metadata = {}

    @property
    def totals(self) -> dict:
        return {**self.api.totals, **self.plans}

    def decide(self, observation: dict) -> list[dict]:
        remember(self.last_seen, observation)
        self._metadata = {"type": "commander", "model": self.api.name, "effort": self.api.effort}
        abilities = []
        if self.pending and self.pending.done():
            done, self.pending = self.pending, None  # after a failure the next tick asks again
            reply, attempts, seen_ms = done.result()  # a worker's error surfaces here
            abilities = self._adopt(reply, observation, seen_ms)
            self._metadata["attempts"] = attempts
        self.batch = self.skills.decide(observation) + abilities
        if self.pending is None:
            prompt = self._prompt(observation)
            self.pending = self.pool.submit(self._ask, prompt, observation.get("time_ms", 0))
            self._metadata.update(prompt=prompt,
                                  prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest())
        return self.batch

    def _ask(self, prompt: str, seen_ms: int) -> tuple[dict, list[dict], int]:
        """On the worker thread: only the call, so all state changes stay on the caller's."""
        try:
            reply, attempts = self.api.ask(prompt, REPLY_SCHEMA, parse_plan, INVALID_RETRIES)
        except InvalidReply as error:
            raise invalid_reply(error) from None
        return reply, attempts, seen_ms

    def _adopt(self, reply: dict, observation: dict, seen_ms: int) -> list[dict]:
        """Apply the plan's assignments that still fit the state; return its abilities."""
        friendly = friendly_units(observation)
        roster = {unit["id"]: unit for unit in observation.get("enemy_roster", [])}
        now_ms = observation.get("time_ms", 0)
        dropped = []
        for item in reply["assignments"]:
            unit, target = friendly.get(item["unit"]), item.get("target")
            if not unit or not unit.get("men"):
                dropped.append(f"{describe_assignment(item)}: no such unit alive")
                continue
            if item["skill"] == "move" and (item.get("x") is None or item.get("z") is None):
                dropped.append(f"{describe_assignment(item)}: a move needs x and z")
                continue
            if item["skill"] == "shoot" and not unit.get("ammo0"):
                dropped.append(f"{describe_assignment(item)}: the unit has no missiles")
                continue
            if target and (target not in roster or roster[target].get("dead")):
                dropped.append(f"{describe_assignment(item)}: target {target} is not a live"
                               " enemy, so it was cleared")
                item = dict(item, target=None)
            self.skills.assign(unit, item, now_ms / 1000)
        orders = []
        for order in reply["abilities"]:
            if isinstance(order, dict) and order.get("type") not in ABILITY_TYPES:
                dropped.append(f"{describe_dropped(order)}: not an ability, build, reinforce"
                               " or flight order")
            else:
                orders.append(order)
        abilities, rejected = split_valid(orders, observation)
        dropped += rejected
        if reply["notes"] is not None:
            self.notes = reply["notes"][:NOTES_LIMIT]
        self.age_ms = now_ms - seen_ms
        self.plans.update(plans=1, plan_age_ms=self.age_ms)
        self.report.extend(f"dropped {item}" for item in dropped)
        plan = describe_plan(reply["assignments"])
        if abilities:
            plan += "; " + describe_orders(abilities)
        self.history.append(f"state {seen_ms / 1000:.0f} s, adopted {now_ms / 1000:.0f} s:"
                            f" {plan} ({reply['reason'][:REASON_LIMIT]})")
        self._metadata.update(plan=reply["assignments"], abilities=abilities,
                              reason=reply["reason"], notes=self.notes, dropped=dropped,
                              plan_age_s=round(self.age_ms / 1000, 2))
        return abilities

    def _prompt(self, observation: dict) -> str:
        friendly = friendly_units(observation)
        # Orders sent this tick have not reached the engine, so the state cannot show them.
        ordered = {unit_id: order for unit_id, order in self.skills.sent.items()
                   if unit_id in friendly and order["time_s"] < self.skills.time_s
                   and holds(friendly[unit_id], order)}
        report = "\n".join(self.report) or "(none)"
        self.report.clear()
        submitting = [order for order in self.batch if order["type"] in ABILITY_TYPES]
        prompt = "\n\n".join([
            "Battle notes:\n" + (self.notes or "(none)"),
            "Recent plans, oldest first:\n" + ("\n".join(self.history) or "(none)"),
            render_timing(observation, self.age_ms),
            REPORT_HEADER + report,
            *(["Orders being submitted now (not yet acknowledged or reflected in this "
               "snapshot):\n" + describe_orders(submitting)] if submitting else []),
            render_state(observation, self.last_seen, self.before, ordered),
            render_assignments(self.skills, observation),
        ])
        self.before = strengths(observation)
        return prompt

    def acknowledge(self, ack: dict, latency: dict) -> None:
        self.skills.acknowledge(ack, latency)
        for result in ack.get("results") or []:
            index = result.get("index")
            if not result.get("ok") and index and index <= len(self.batch):
                order = self.batch[index - 1]
                self.report.append(f"engine rejected {describe_orders([order])}:"
                                   f" {result.get('error')}")

    def metadata(self) -> dict:
        return self._metadata

    def close(self) -> None:
        self.pool.shutdown(wait=True)
