"""What the policy sees and may order in a battle, and the failure taxonomy.

Observations are the dicts the Lua side publishes (``engine/mailbox.py`` has the
shape); orders are dicts ``{"unit", "type", "x", "z", "run", "target"}``. Only an
engine-reported battle result is a gameplay outcome; everything below is an
infrastructure, protocol or policy failure.
"""

import math


class ProtocolError(RuntimeError):
    """The in-game side or the policy broke the message contract."""


class IllegalActionError(ProtocolError):
    """An order the observation does not allow (unknown unit, invisible target, ...)."""


class PolicyFailure(RuntimeError):
    """The policy could not produce orders; ``failure`` records why."""

    def __init__(self, message: str, *, failure: dict | None = None):
        super().__init__(message)
        self.failure = failure or {}


class MailboxTimeout(RuntimeError):
    """The game stopped publishing, or never consumed a request."""


class BattleRestarted(RuntimeError):
    """A new battle replaced the one being played; ``observation`` is its first message."""

    def __init__(self, observation: dict):
        super().__init__(f"battle {observation.get('battle')} replaced the current one")
        self.observation = observation


ORDER_TYPES = ("move", "attack", "halt")


def friendly_units(observation: dict) -> dict[str, dict]:
    return {unit["id"]: unit for unit in observation.get("friendly", [])}


def visible_enemies(observation: dict) -> dict[str, dict]:
    return {unit["id"]: unit for unit in observation.get("enemy", [])}


def validate_orders(orders: list, observation: dict) -> None:
    """Reject orders the observation does not allow; the engine re-checks the rest."""
    friendly = friendly_units(observation)
    enemies = visible_enemies(observation)
    seen = set()
    for order in orders:
        if not isinstance(order, dict):
            raise IllegalActionError(f"order is not an object: {order!r}")
        unit, kind = order.get("unit"), order.get("type")
        if unit not in friendly:
            raise IllegalActionError(f"unknown friendly unit {unit!r}")
        if unit in seen:
            raise IllegalActionError(f"{unit} is ordered twice")
        seen.add(unit)
        if kind not in ORDER_TYPES:
            raise IllegalActionError(f"{unit}: unknown order type {kind!r}")
        if kind == "move" and not all(_finite(order.get(axis)) for axis in ("x", "z")):
            raise IllegalActionError(f"{unit}: move needs finite x and z")
        if kind == "attack" and order.get("target") not in enemies:
            raise IllegalActionError(f"{unit}: target {order.get('target')!r} is not visible")


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def scenario_key(observation: dict) -> str:
    """Factions and unit counts of the first observation, to check a job's episodes match."""
    armies = observation.get("armies", {})
    player = armies.get("player", {}).get("faction", "?")
    enemy = armies.get("enemy", {}).get("faction", "?")
    roster = observation.get("enemy_roster") or observation.get("enemy", [])
    return f"{player}({len(observation.get('friendly', []))}) vs {enemy}({len(roster)})"
