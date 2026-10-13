"""What the policy sees and may order in a battle, and the failure taxonomy.

Observations are the dicts the Lua side publishes (``engine/mailbox.py`` has the
shape); orders are dicts ``{"unit", "type", "x", "z", "facing", "run", "target"}``. Only an
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


ORDER_TYPES = ("move", "attack", "halt", "behaviour", "ability")
ATTACK_MODES = ("auto", "melee", "ranged")
BEHAVIOURS = ("fire_at_will", "skirmish", "defend", "change_formation_spacing", "formed_attack")


def friendly_units(observation: dict) -> dict[str, dict]:
    return {unit["id"]: unit for unit in observation.get("friendly", [])}


def visible_enemies(observation: dict) -> dict[str, dict]:
    return {unit["id"]: unit for unit in observation.get("enemy", [])}


def validate_orders(orders: list, observation: dict) -> None:
    """Reject orders the observation does not allow; the engine re-checks the rest."""
    friendly = friendly_units(observation)
    enemies = visible_enemies(observation)
    if not isinstance(orders, list):
        raise IllegalActionError("orders must be a list")
    movement = {}
    settings = set()
    for order in orders:
        if not isinstance(order, dict):
            raise IllegalActionError(f"order is not an object: {order!r}")
        unit, kind = order.get("unit"), order.get("type")
        if unit not in friendly:
            raise IllegalActionError(f"unknown friendly unit {unit!r}")
        if kind not in ORDER_TYPES:
            raise IllegalActionError(f"{unit}: unknown order type {kind!r}")
        queued = order.get("queue", False)
        if not isinstance(queued, bool) or not isinstance(order.get("run", False), bool):
            raise IllegalActionError(f"{unit}: queue and run must be booleans")
        if queued and (kind not in ("move", "attack") or movement.get(unit) != "move"):
            raise IllegalActionError(f"{unit}: queued move/attack must follow a move in this batch")
        if kind in ("move", "attack", "halt"):
            if unit in movement and not queued:
                raise IllegalActionError(f"{unit} is ordered twice without queue")
            movement[unit] = kind
        else:
            key = (unit, kind, order.get(kind))
            if key in settings:
                raise IllegalActionError(f"{unit}: repeated {kind} {order.get(kind)!r}")
            settings.add(key)
        if kind == "move" and not all(_finite(order.get(axis)) for axis in ("x", "z")):
            raise IllegalActionError(f"{unit}: move needs finite x and z")
        if order.get("facing") is not None and not _finite(order["facing"]):
            raise IllegalActionError(f"{unit}: facing must be a number of degrees or null")
        if order.get("width") is not None and (
            not _finite(order["width"]) or order["width"] <= 0
        ):
            raise IllegalActionError(f"{unit}: width must be a positive number or null")
        if kind == "attack" and order.get("target") not in enemies:
            raise IllegalActionError(f"{unit}: target {order.get('target')!r} is not visible")
        if kind == "attack":
            mode = order.get("mode", "auto")
            if mode not in ATTACK_MODES:
                raise IllegalActionError(f"{unit}: unknown attack mode {mode!r}")
            if mode == "ranged" and not friendly[unit].get("ammo", 0):
                raise IllegalActionError(f"{unit}: ranged attack needs ammunition")
        if kind == "behaviour":
            behaviour = order.get("behaviour")
            if behaviour not in BEHAVIOURS or behaviour not in friendly[unit].get("behaviours", {}):
                raise IllegalActionError(f"{unit}: unavailable behaviour {behaviour!r}")
            if not isinstance(order.get("enabled"), bool):
                raise IllegalActionError(f"{unit}: enabled must be a boolean")
        if kind == "ability":
            ability = order.get("ability")
            available = {a["key"]: a for a in friendly[unit].get("abilities", [])}
            if ability not in available or available[ability].get("can_use") is not True:
                raise IllegalActionError(f"{unit}: unavailable ability {ability!r}")
            target = order.get("target")
            ground = order.get("x") is not None or order.get("z") is not None
            if target is not None and target not in friendly and target not in enemies:
                raise IllegalActionError(f"{unit}: ability target {target!r} not visible/friendly")
            positioned = all(_finite(order.get(axis)) for axis in ("x", "z"))
            if ground and (target is not None or not positioned):
                raise IllegalActionError(f"{unit}: ground ability needs x/z and no unit target")


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def scenario_key(observation: dict) -> str:
    """Factions and unit counts of the first observation, to check a job's episodes match."""
    armies = observation.get("armies", {})
    player = armies.get("player", {}).get("faction", "?")
    enemy = armies.get("enemy", {}).get("faction", "?")
    roster = observation.get("enemy_roster") or observation.get("enemy", [])
    return f"{player}({len(observation.get('friendly', []))}) vs {enemy}({len(roster)})"
