"""Persistent unit skills: the executor under the LLM commander, and the ``skills`` policy.

Each unit holds an assignment ``{skill, target, x, z, since_s}`` until it is replaced. On
every observation its skill turns the fresh state into the order the unit should have,
and an order goes out only when it differs from the last one sent or that one lapsed.
Without a commander, units keep the default skill of their class.

- engage: fight in melee; free units go for the enemy lord when he is in melee nearby.
- shoot: fire at a live enemy in range that is not in melee (unless the commander named it);
  walk to a firing spot first.
- hold: keep a post and fight enemies that come near it.
- charge: wait (at a post) until the target, or any enemy, is in melee, then charge it
  (mounted units run all the way, others for the last stretch).
- move: go to a point, also out of melee, and stay there.
"""

import math

from twwarhammer3.battle.llm import ARRIVED_M
from twwarhammer3.battle.scripted import _distance
from twwarhammer3.protocol import friendly_units, visible_enemies

SKILLS = ("engage", "shoot", "hold", "charge", "move")
RUN_M = 30  # run only for the last stretch of a charge
ENGAGE_M = 40  # how near an enemy must come to a hold post, or the enemy lord to a free unit
REPEAT_S = 2.0  # a lapsed or rejected order is sent again after this many battle seconds
SHOOTERS = ("missile", "missile_chariot", "artillery")
CHARGERS = ("lord", "hero", "cavalry", "chariot", "missile_cavalry")
MOUNTED = ("cavalry", "chariot", "missile_cavalry", "missile_chariot")
OUT = {"routing", "shattered"}


def default_skill(unit: dict) -> str:
    if unit.get("class") in SHOOTERS:
        return "shoot"
    return "charge" if unit.get("class") in CHARGERS else "engage"


def _states(unit: dict) -> set:
    return set(unit.get("state") or [])


def _live(enemy: dict) -> bool:
    return enemy.get("x") is not None and not OUT & _states(enemy)


def _nearest(unit: dict, enemies) -> dict | None:
    return min(enemies, key=lambda enemy: _distance(unit, enemy), default=None)


def _point(assignment: dict) -> dict | None:
    if assignment.get("x") is None or assignment.get("z") is None:
        return None
    return {"x": assignment["x"], "z": assignment["z"]}


def _facing(unit: dict, enemy: dict | None) -> float | None:
    """The bearing from a unit to an enemy: 0 north (+z), 90 east (+x)."""
    if not enemy or _distance(unit, enemy) == math.inf:
        return None
    return round(math.degrees(math.atan2(enemy["x"] - unit["x"], enemy["z"] - unit["z"])) % 360)


def _move(unit: dict, point: dict, *, run: bool = False, face: dict | None = None) -> dict:
    return {"unit": unit["id"], "type": "move", "x": point["x"], "z": point["z"],
            "facing": _facing(point, face), "width": None, "run": run, "queue": False}


def _attack(unit: dict, enemy: dict, mode: str, sent: dict | None, *,
            run: bool | None = None) -> dict:
    if run is None:  # walk until the last stretch, and keep running once started
        before = sent or {}
        run = _distance(unit, enemy) <= RUN_M or (
            before.get("type") == "attack" and before.get("target") == enemy["id"]
            and before.get("run", False))
    return {"unit": unit["id"], "type": "attack", "target": enemy["id"], "mode": mode,
            "run": run, "queue": False}


def _last(sent: dict | None) -> str | None:
    """The target of our last attack: the observed target lags an order by one tick."""
    return sent["target"] if sent and sent["type"] == "attack" else None


def _first(enemies: dict, *ids) -> dict | None:
    """The first of ``ids`` naming a live visible enemy."""
    for enemy_id in ids:
        if enemy_id in enemies and _live(enemies[enemy_id]):
            return enemies[enemy_id]
    return None


def engage(unit, assignment, enemies, sent):
    if "melee" in _states(unit):
        return None, f"in melee with {unit.get('target') or '?'}"
    live = [enemy for enemy in enemies.values() if _live(enemy)]
    lords = [enemy for enemy in live if (enemy.get("commander") or enemy.get("class") == "lord")
             and "melee" in _states(enemy) and _distance(unit, enemy) <= ENGAGE_M]
    target = (_nearest(unit, lords)
              or _first(enemies, assignment.get("target"), _last(sent), unit.get("target"))
              or _nearest(unit, live)
              or _nearest(unit, [e for e in enemies.values() if e.get("x") is not None]))
    if not target:
        return None, "no enemy in sight"
    return _attack(unit, target, "melee", sent), f"attacking {target['id']}"


def shoot(unit, assignment, enemies, sent):
    if not unit.get("ammo"):
        if unit.get("class") == "artillery":
            return None, "out of ammunition"
        order, phase = charge(unit, {"skill": "charge"}, enemies, sent)
        return order, "out of ammunition, " + phase
    if "melee" in _states(unit):
        return None, f"in melee with {unit.get('target') or '?'}"
    spot = _point(assignment)
    if spot and _distance(unit, spot) > ARRIVED_M:
        return _move(unit, spot, face=_nearest(spot, enemies.values())), "walking to firing spot"
    # Only a target the commander named is shot at in melee (from a spot beside the fight).
    named = assignment.get("target")
    clear = [enemy for enemy in enemies.values()
             if _live(enemy) and ("melee" not in _states(enemy) or enemy["id"] == named)]
    in_range = [enemy for enemy in clear if _distance(unit, enemy) <= (unit.get("range") or 0)]
    ids = [enemy["id"] for enemy in in_range]
    target = _first({e["id"]: e for e in in_range}, named, _last(sent), unit.get("target"))
    if not target and in_range:
        # Blocks of infantry and cavalry before shooters and guns, the largest first.
        target = min(in_range, key=lambda e: (e.get("class") in SHOOTERS + ("missile_cavalry",),
                                              -e.get("men", 0)))
    if target:
        return (_attack(unit, target, "ranged", sent, run=False),
                f"shooting {target['id']} ({len(ids)} in range)")
    if clear and not spot and unit.get("class") != "artillery":
        # Out of range everywhere: the engine walks a shooter into range of its target.
        target = _first(enemies, named) or _nearest(unit, clear)
        return _attack(unit, target, "ranged", sent, run=False), f"closing on {target['id']}"
    if (sent or {}).get("type") == "attack":
        return {"unit": unit["id"], "type": "halt"}, "holding fire"
    return None, "nothing to shoot"


def hold(unit, assignment, enemies, sent):
    if "melee" in _states(unit):
        return None, f"in melee with {unit.get('target') or '?'}"
    post = _point(assignment) or unit
    near = [enemy for enemy in enemies.values()
            if _live(enemy) and _distance(post, enemy) <= ENGAGE_M]
    if near:
        target = (_first({e["id"]: e for e in near}, _last(sent), unit.get("target"))
                  or _nearest(post, near))
        return _attack(unit, target, "auto", sent), f"fighting {target['id']} at the post"
    if _distance(unit, post) > ARRIVED_M:
        return _move(unit, post, face=_nearest(post, enemies.values())), "returning to post"
    return None, "holding"


def charge(unit, assignment, enemies, sent):
    if "melee" in _states(unit):
        return None, f"in melee with {unit.get('target') or '?'}"
    fighting = {enemy["id"]: enemy for enemy in enemies.values()
                if _live(enemy) and "melee" in _states(enemy)}
    # A named target out of sight, dead or routing counts as no target.
    wanted = assignment.get("target") if _first(enemies, assignment.get("target")) else None
    target = (_first(fighting, wanted) if wanted
              else _first(fighting, _last(sent), unit.get("target"))
              or _nearest(unit, fighting.values()))
    if target:
        run = True if unit.get("class") in MOUNTED else None  # foot walks most of the way
        return _attack(unit, target, "melee", sent, run=run), f"charging {target['id']}"
    named = assignment.get("target")
    waiting = (f"waiting: {wanted} not in melee" if wanted else "waiting for melee"
               + (f" ({named} out of sight)" if named else ""))
    post = _point(assignment)
    if post and _distance(unit, post) > ARRIVED_M:
        order = _move(unit, post, face=_nearest(post, enemies.values()))
        return order, waiting + ", moving to post"
    if not post and sent and sent["type"] != "halt" and sent["time_s"] < assignment.get(
            "since_s", 0):
        return {"unit": unit["id"], "type": "halt"}, waiting  # stop the previous skill's order
    return None, waiting


def move(unit, assignment, enemies, sent):
    point = _point(assignment)
    if not point or _distance(unit, point) <= ARRIVED_M:
        return None, "arrived"
    threatened = any(_live(e) and _distance(unit, e) <= ENGAGE_M for e in enemies.values())
    run = threatened or ((sent or {}).get("type") == "move" and sent.get("run", False))
    return _move(unit, point, run=run), "moving"


RULES = {"engage": engage, "shoot": shoot, "hold": hold, "charge": charge, "move": move}


def same(order: dict, sent: dict | None) -> bool:
    if not sent or order["type"] != sent["type"]:
        return False
    if order["type"] == "move":
        return _distance(order, sent) <= ARRIVED_M and order["run"] == sent["run"]
    if order["type"] == "attack":
        return all(order[key] == sent[key] for key in ("target", "mode", "run"))
    return True


def lapsed(unit: dict, sent: dict) -> bool:
    """Whether the engine dropped an order we sent, never started it or changed it."""
    if sent["type"] == "attack":
        return unit.get("target") != sent["target"] or "idle" in _states(unit)
    if sent["type"] == "move":
        return not unit.get("dest") and "moving" not in _states(unit)
    return False  # a halt is one-shot


class Skills:
    """Assignments, the last order sent per unit and each unit's phase; one per episode."""

    def __init__(self):
        self.assignments: dict[str, dict] = {}
        self.sent: dict[str, dict] = {}
        self.phase: dict[str, str] = {}
        self.batch: list[dict] = []
        self.time_s = 0.0

    def assign(self, unit: dict, item: dict, time_s: float) -> None:
        self.assignments[unit["id"]] = {"skill": item["skill"], "target": item.get("target"),
                                        "x": item.get("x"), "z": item.get("z"),
                                        "since_s": time_s}

    def decide(self, observation: dict) -> list[dict]:
        self.time_s = observation.get("time_ms", 0) / 1000
        enemies = visible_enemies(observation)
        orders = []
        for unit_id, unit in friendly_units(observation).items():
            if not unit.get("men") or OUT & _states(unit) or unit.get("x") is None:
                self.phase[unit_id] = "routing" if unit.get("men") else "destroyed"
                continue
            if unit_id not in self.assignments:
                self.assign(unit, {"skill": default_skill(unit)}, self.time_s)
            assignment = self.assignments[unit_id]
            if assignment["skill"] == "hold" and _point(assignment) is None:
                assignment.update(x=unit["x"], z=unit["z"])  # the post is where it stands
            sent = self.sent.get(unit_id)
            order, self.phase[unit_id] = RULES[assignment["skill"]](unit, assignment, enemies,
                                                                    sent)
            if order is None:
                continue
            if same(order, sent) and not (
                lapsed(unit, sent) and self.time_s - sent["time_s"] >= REPEAT_S
            ):
                continue
            self.sent[unit_id] = dict(order, time_s=self.time_s)
            orders.append(order)
        self.batch = orders
        return orders

    def acknowledge(self, ack: dict, latency: dict) -> None:
        for result in ack.get("results") or []:
            index = result.get("index")
            if result.get("ok") or not index or index > len(self.batch):
                continue
            order = self.batch[index - 1]
            assignment = self.assignments.get(order["unit"])
            # Other rejections (a routing unit) are retried once the order lapses.
            if order["type"] == "move" and assignment and result.get("error") == "unreachable":
                if assignment["skill"] == "move":  # stay where the unit is instead
                    assignment["skill"] = "hold"
                assignment.update(x=None, z=None)

    def metadata(self) -> dict:
        return {"type": "skills"}
