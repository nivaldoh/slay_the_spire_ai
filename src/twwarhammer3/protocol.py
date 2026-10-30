"""What the policy sees and may order in a battle, and the failure taxonomy.

Observations are the dicts the Lua side publishes (``engine/mailbox.py`` has the
shape). Orders have a unit, type and command-specific fields for movement, attacks,
toggles or abilities; move/attack sequences use ``queue``. The unit ``"army"`` gives the
army's own orders: an ``ability`` (a faction's point unlocks), and, paid with supplies, a
``build`` (a tower or barricade on a slot) or a ``reinforce`` (a unit from the
reinforcement pool, entering at a spawn zone). Only an engine-reported battle result is a
gameplay outcome; everything below is an infrastructure, protocol or policy failure.
"""

import math


class ProtocolError(RuntimeError):
    """The game's messages or setup (against the scenario), or the policy, broke the contract."""


class IllegalActionError(ProtocolError):
    """An order the observation does not allow (unknown unit, invisible target, ...)."""


class PolicyFailure(RuntimeError):
    """The policy could not produce orders; ``failure`` records why."""

    def __init__(self, message: str, *, failure: dict | None = None):
        super().__init__(message)
        self.failure = failure or {}


class MailboxTimeout(RuntimeError):
    """The game did not publish what was awaited in time, or never consumed a request."""


class BattleRestarted(RuntimeError):
    """A new battle replaced the one being played; ``observation`` is its first message."""

    def __init__(self, observation: dict):
        super().__init__(f"battle {observation.get('battle')} replaced the current one")
        self.observation = observation


# Observation keys a policy never reads: evaluator and private setup state, and the
# multiplayer modes' native identities (engine/mailbox.py).
HIDDEN_KEYS = ("evaluation", "final", "setup", "native")
ORDER_TYPES = ("move", "attack", "halt", "behaviour", "ability", "flight")
ATTACK_MODES = ("auto", "melee", "ranged")
BEHAVIOURS = ("fire_at_will", "skirmish", "defend", "change_formation_spacing", "formed_attack")


def friendly_units(observation: dict) -> dict[str, dict]:
    return {unit["id"]: unit for unit in observation.get("friendly", [])}


def visible_enemies(observation: dict) -> dict[str, dict]:
    return {unit["id"]: unit for unit in observation.get("enemy", [])}


def refused(orders, error: str) -> dict:
    """The acknowledgement of a batch refused before the engine: every order failed."""
    return {"validation_error": error,
            "results": [{"index": index + 1, "unit": order.get("unit"), "ok": False,
                         "error": error} for index, order in enumerate(orders)
                        if isinstance(order, dict)] if isinstance(orders, list) else []}


def validate_orders(orders: list, observation: dict) -> None:
    """Reject orders the observation does not allow; the engine re-checks the rest."""
    friendly = friendly_units(observation)
    enemies = visible_enemies(observation)
    # A team member may aim abilities at its teammate's units (``allies``), not order them.
    targets = friendly.keys() | enemies.keys() | {u["id"] for u in observation.get("allies", [])}
    if not isinstance(orders, list):
        raise IllegalActionError("orders must be a list")
    movement = {}
    settings = set()
    purchases = {"spent": 0, "slots": set(), "units": []}
    for order in orders:
        if not isinstance(order, dict):
            raise IllegalActionError(f"order is not an object: {order!r}")
        field = next((key for key, value in order.items()
                      if value is not None and not isinstance(value, (str, int, float))), None)
        if field is not None:
            raise IllegalActionError(f"order field {field!r} must be a string, number, boolean"
                                     " or null")
        unit, kind = order.get("unit"), order.get("type")
        if unit == "army" and kind == "ability":
            _validate_army_ability(order, observation, targets, settings)
            continue
        if unit == "army" and kind in ("build", "reinforce"):
            _validate_purchase(order, observation, purchases)
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
        if kind == "flight":
            if not isinstance(order.get("flying"), bool):
                raise IllegalActionError(f"{unit}: flying must be a boolean")
            current = friendly[unit]
            if not current.get("can_fly"):
                raise IllegalActionError(f"{unit}: cannot fly")
            if (current.get("flying") != order["flying"]
                    and (current.get("flight") or {}).get("can_toggle") is not True):
                raise IllegalActionError(f"{unit}: flight change is unavailable now")
        if kind == "ability":
            ability = order.get("ability")
            available = {a["key"]: a for a in friendly[unit].get("abilities", [])}
            if ability not in available or available[ability].get("can_use") is not True:
                raise IllegalActionError(f"{unit}: unavailable ability {ability!r}")
            if available[ability].get("ready") is False:
                raise IllegalActionError(f"{unit}: ability {ability!r} is not ready")
            _validate_ability_target(unit, order, targets)

    # Keep command-specific diagnostics above, then check unused fields too: every
    # field crosses the Lua JSON boundary, even when its command ignores it.
    for order in orders:
        for field, value in order.items():
            if (isinstance(value, (int, float)) and not isinstance(value, bool)
                    and not _finite(value)):
                raise IllegalActionError(f"order field {field!r} must be a finite number")


def _validate_army_ability(order, observation, targets, settings) -> None:
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
    _validate_ability_target("army", order, targets)


def _validate_purchase(order, observation, purchases) -> None:
    """A build (a tower or barricade on an empty slot the army can build on now) or a
    reinforcement (a unit type from the army's pool, entering at one of its spawn zones),
    paid with supplies. ``purchases`` holds what the batch has already spent and taken."""
    mode = observation.get("mode") or {}
    if order["type"] == "build":
        slot = {slot["id"]: slot for slot in mode.get("slots") or []}.get(order.get("slot"))
        if slot is None:
            raise IllegalActionError(f"army: unknown building slot {order.get('slot')!r}")
        if slot.get("built") or slot.get("building_s") is not None:
            raise IllegalActionError(f"army: slot {slot['id']} already has a building")
        if not slot.get("usable"):
            raise IllegalActionError(f"army: slot {slot['id']} cannot be built on now")
        if slot["id"] in purchases["slots"]:
            raise IllegalActionError(f"army: slot {slot['id']} ordered twice")
        options = {option["name"]: option for option in slot.get("options") or []}
        if order.get("option") not in options:
            raise IllegalActionError(f"army: slot {slot['id']} has no option"
                                     f" {order.get('option')!r}")
        purchases["slots"].add(slot["id"])
        name, cost = order["option"], options[order["option"]].get("cost") or 0
    else:
        name = order.get("reinforcement")
        pool = [unit for unit in mode.get("reinforcements") or [] if unit.get("type") == name]
        taken = purchases["units"].count(name)
        if len(pool) <= taken:
            raise IllegalActionError(f"army: no {name!r} left in the reinforcement pool")
        zones = {zone["id"]: zone for zone in mode.get("spawn_zones") or []}
        if order.get("zone") not in zones:
            raise IllegalActionError(f"army: zone {order.get('zone')!r} is not one of yours")
        if zones[order["zone"]].get("usable") is False:
            raise IllegalActionError(f"army: zone {order['zone']} refuses purchases now")
        purchases["units"].append(name)
        # The engine side buys the cheapest unit of the type, then the next cheapest.
        cost = sorted(unit.get("cost") or 0 for unit in pool)[taken]
    if mode.get("supplies") is not None and purchases["spent"] + cost > mode["supplies"]:
        raise IllegalActionError(f"army: {name} costs {cost}, supplies {mode['supplies']}"
                                 f" ({purchases['spent']} already ordered)")
    purchases["spent"] += cost


def _validate_ability_target(unit, order, targets) -> None:
    target = order.get("target")
    ground = order.get("x") is not None or order.get("z") is not None
    if target is not None and target not in targets:
        raise IllegalActionError(f"{unit}: ability target {target!r} not visible/friendly")
    positioned = all(_finite(order.get(axis)) for axis in ("x", "z"))
    if ground and (target is not None or not positioned):
        raise IllegalActionError(f"{unit}: ground ability needs x/z and no unit target")


def _finite(value) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:  # an integer beyond float range
        return False


def scenario_key(observation: dict) -> str:
    """Factions and unit counts of the first observation with units: an episode's ``scenario``."""
    armies = observation.get("armies", {})
    player = armies.get("player", {}).get("faction", "?")
    enemy = armies.get("enemy", {}).get("faction", "?")
    roster = observation.get("enemy_roster") or observation.get("enemy", [])
    return f"{player}({len(observation.get('friendly', []))}) vs {enemy}({len(roster)})"
