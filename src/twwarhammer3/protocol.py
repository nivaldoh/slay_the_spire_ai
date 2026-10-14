"""What the policy sees and may order in a battle, and the failure taxonomy.

Observations are the dicts the Lua side publishes (``engine/mailbox.py`` has the
shape). Orders have a unit, type and command-specific fields for movement, attacks,
toggles or abilities; move/attack sequences use ``queue``. An army ability (Khorne's kill
unlocks) is an ``ability`` order whose unit is ``"army"``, and so is a ``build`` order (a
tower or barricade on a slot, paid with supplies). Only an engine-reported
battle result is a gameplay outcome; everything below is an
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
ARMY_ORDER_TYPES = ("ability", "build", "reinforce")
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
        if unit == "army" and kind == "ability":
            _validate_army_ability(order, observation, friendly, enemies, settings)
            continue
        if unit == "army" and kind == "build":
            _validate_build(order, observation, settings)
            continue
        if unit == "army" and kind == "reinforce":
            _validate_reinforce(order, observation, settings)
            continue
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
            if available[ability].get("ready") is False:
                raise IllegalActionError(f"{unit}: ability {ability!r} is not ready")
            _validate_ability_target(unit, order, friendly, enemies)


def _validate_army_ability(order, observation, friendly, enemies, settings) -> None:
    """An army ability is cast by the army ("unit": "army"), not by one of its units."""
    ability = order.get("ability")
    army = {a["key"]: a for a in (observation.get("army") or {}).get("abilities", [])}
    if ability not in army or army[ability].get("unlocked") is False:
        raise IllegalActionError(f"army: unavailable army ability {ability!r}")
    if army[ability].get("ready") is False:
        raise IllegalActionError(f"army: army ability {ability!r} is not ready")
    if ("army", ability) in settings:
        raise IllegalActionError(f"army: repeated ability {ability!r}")
    settings.add(("army", ability))
    if order.get("target") is None and order.get("x") is None:
        raise IllegalActionError(f"army: {ability!r} needs a unit target or x/z")
    _validate_ability_target("army", order, friendly, enemies)


def _validate_build(order, observation, settings) -> None:
    """A tower or barricade on an empty slot, paid with the army's supplies."""
    mode = observation.get("mode") or {}
    slots = {slot["id"]: slot for slot in mode.get("slots") or []}
    slot = slots.get(order.get("slot"))
    if slot is None:
        raise IllegalActionError(f"army: unknown building slot {order.get('slot')!r}")
    if slot.get("built") or slot.get("building_s") is not None:
        raise IllegalActionError(f"army: slot {slot['id']} already has a building")
    options = {option["name"]: option for option in slot.get("options") or []}
    if order.get("option") not in options:
        raise IllegalActionError(f"army: slot {slot['id']} has no option {order.get('option')!r}")
    cost = options[order["option"]].get("cost") or 0
    if mode.get("supplies") is not None and cost > mode["supplies"]:
        raise IllegalActionError(f"army: {order['option']} costs {cost}, supplies"
                                 f" {mode['supplies']}")
    if ("build", slot["id"]) in settings:
        raise IllegalActionError(f"army: slot {slot['id']} ordered twice")
    settings.add(("build", slot["id"]))


def _validate_reinforce(order, observation, settings) -> None:
    """A unit from the army's reinforcement pool, paid with supplies, at one of its zones."""
    mode = observation.get("mode") or {}
    pool = {unit["id"]: unit for unit in mode.get("reinforcements") or []}
    unit = pool.get(order.get("reinforcement"))
    if unit is None:
        raise IllegalActionError(f"army: unknown reinforcement {order.get('reinforcement')!r}")
    if order.get("zone") not in {zone["id"] for zone in mode.get("spawn_zones") or []}:
        raise IllegalActionError(f"army: zone {order.get('zone')!r} is not one of yours")
    spent = sum(pool[key].get("cost") or 0 for kind, key in settings if kind == "reinforce")
    if mode.get("supplies") is not None and spent + (unit.get("cost") or 0) > mode["supplies"]:
        raise IllegalActionError(f"army: {unit['id']} costs {unit.get('cost')}, supplies"
                                 f" {mode['supplies']} ({spent} already ordered)")
    if ("reinforce", unit["id"]) in settings:
        raise IllegalActionError(f"army: reinforcement {unit['id']} ordered twice")
    settings.add(("reinforce", unit["id"]))


def _validate_ability_target(unit, order, friendly, enemies) -> None:
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
