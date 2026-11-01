"""Frozen graph skill adapter over WH3's existing tactics.

Design reference: graph-robots/open-robot-skills, transporting-objects/SKILL.md
at 752dfbd: typed inputs, named exits and separate effect witnesses. No donor code.
An accepted order is never a completion witness. These public witnesses describe
contact, arrival or firing; they do not establish damage or a charge bonus.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from math import hypot, isfinite

from twwarhammer3.battle import skills
from twwarhammer3.protocol import IllegalActionError, validate_orders

VERSION = "wh3-skills-v1"
# JUDGEMENT: G4 Skill limits — Codex, 2026-10-31, delegated baseline: existing arrival
# radius, 60 battle seconds per skill, retry after 2 s; fail without a witness.
# Wider arrival, longer waits or other retry/fallback rules change the executed tactics.
ARRIVAL_M = skills.ARRIVED_M
TIMEOUT_MS = 60000
REPEAT_MS = 2000

# Types belong to the graph format, not Python annotations in generated code.
CONTRACTS = {
    "owned": {"inputs": {}, "outputs": {"units": "units"}, "exits": ["succeeded", "empty"]},
    "select_target": {"inputs": {"units": "units"}, "outputs": {"target": "target"},
                      "exits": ["succeeded", "empty"]},
    "contact": {"inputs": {}, "outputs": {}, "exits": ["yes", "no"]},
    **{name: {"inputs": {"units": "units", **(
        {"point": "point"} if name in ("move", "hold") else {"target": "target"})},
        "outputs": {}, "exits": ["succeeded", "failed", "cancelled"]}
       for name in skills.RULES},
    "end": {"inputs": {}, "outputs": {}, "exits": []},
}


def valid_value(value, kind):
    if kind == "units":
        return (isinstance(value, list) and bool(value)
                and all(isinstance(item, str) for item in value)
                and len(set(value)) == len(value))
    if kind == "target":
        return isinstance(value, str) and bool(value)
    if kind == "point":
        return (isinstance(value, dict) and set(value) == {"x", "z"}
                and all(isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v)
                        for v in value.values()))
    return False


def available(unit):
    return (unit.get("men", 0) > 0 and unit.get("x") is not None
            and unit.get("z") is not None and not skills.OUT.intersection(unit.get("state", [])))


def public_contact(view):
    return any(available(unit) and "melee" in unit.get("state", [])
               for unit in view.get("friendly", []) + view.get("allies", [])
               + view.get("enemy", []))


def preconditions(name, inputs, view):
    owned = {u["id"]: u for u in view.get("friendly", [])}
    units = inputs.get("units", [])
    if not units or any(uid not in owned or not available(owned[uid]) for uid in units):
        return "unit unavailable or not owned"
    if name in ("engage", "shoot", "charge"):
        target = next((u for u in view.get("enemy", []) if u["id"] == inputs["target"]), None)
        if target is None or not available(target):
            return "target unavailable or not visible"
        if name == "charge" and "melee" not in target.get("state", []):
            return "charge target is not in melee"
        if name == "shoot" and any(not owned[uid].get("ammo") for uid in units):
            return "no ammunition"
    return None


@dataclass
class SkillRun:
    name: str
    inputs: dict
    start_ms: int
    timeout_ms: int = TIMEOUT_MS
    sent: dict = field(default_factory=dict)
    status: str = "running"
    reason: str | None = None
    batch: list = field(default_factory=list)
    ammo: dict = field(default_factory=dict)

    def tick(self, view):
        """Return status, orders and a public witness; always bounded local work."""
        if self.status != "running":
            return self.status, [], self.reason
        error = preconditions(self.name, self.inputs, view)
        # A last shot can use the final ammunition; evaluate its witness before the
        # no-ammunition failure, while ownership and target availability remain required.
        if error and error != "no ammunition":
            self.status, self.reason = "failed", error
            return self.status, [], self.reason
        units = {u["id"]: u for u in view["friendly"]}
        selected = [units[uid] for uid in self.inputs["units"]]
        if view["time_ms"] - self.start_ms >= self.timeout_ms:
            self.status, self.reason = "failed", "deadline without effect witness"
            return self.status, [], self.reason
        point, target = self.inputs.get("point"), self.inputs.get("target")
        if self.name in ("move", "hold"):
            witness = all(hypot(u["x"] - point["x"], u["z"] - point["z"]) <= ARRIVAL_M
                          for u in selected)
            if self.name == "hold":
                witness = witness and view["time_ms"] - self.start_ms >= REPEAT_MS
            reason = "inside arrival radius" if self.name == "move" else "at post (may engage)"
        elif self.name == "shoot":
            witness = all(u.get("target") == target
                          and self.ammo.get(u["id"], {}).get("target") == target
                          and u.get("ammo", 0) < self.ammo[u["id"]]["ammo"]
                          for u in selected)
            reason = "ammunition decreased between readings of selected target"
        else:
            witness = all(u.get("target") == target and "melee" in u.get("state", [])
                          for u in selected)
            reason = "melee with selected target"
        if witness:
            self.status, self.reason = "succeeded", reason
            return self.status, [], reason
        if error:
            self.status, self.reason = "failed", error
            return self.status, [], error
        enemies = {u["id"]: u for u in view.get("enemy", [])
                   if target is None or u["id"] == target}
        assignment = {"skill": self.name, "target": target, **(point or {}),
                      "since_s": self.start_ms / 1000}
        orders = []
        for unit in selected:
            self.ammo[unit["id"]] = {"ammo": unit.get("ammo", 0), "target": unit.get("target")}
            previous = self.sent.get(unit["id"])
            order, _ = skills.RULES[self.name](unit, assignment, enemies, previous)
            if order and (not skills.same(order, previous)
                          or view["time_ms"] - previous["time_s"] * 1000 >= REPEAT_MS):
                orders.append(order)
                self.sent[unit["id"]] = {**order, "time_s": view["time_ms"] / 1000}
        validate_orders(orders, view)
        self.batch = deepcopy(orders)
        return "running", orders, None

    def acknowledge(self, ack):
        # Refusal allows graph recovery; acceptance says nothing about effects.
        if ack.get("validation_error") or ack.get("accepted") is False or any(
            not result.get("ok") for result in ack.get("results", [])
        ):
            self.status, self.reason = "failed", "order refused"

    def guard(self, orders, view):
        if self.status != "running":
            raise IllegalActionError("skill run no longer active")
        if error := preconditions(self.name, self.inputs, view):
            raise IllegalActionError(error)
        validate_orders(orders, view)

    def cancel(self):
        self.status, self.reason = "cancelled", "local cancellation; no stop order sent"
