"""Public-state Cannae development witness; no private scenario or outcome reader.

Tactical reference: docs/twwarhammer3/cannae-eval.md and Polybius 3.115–116.
Code reference: SMAC smac/env/starcraft2/starcraft2.py get_agent_action_heuristic
retains a target until unavailable. Here only currently visible, able enemies qualify.
Movement records describe waypoint evidence, never a detector of useful envelopment.
"""

from copy import deepcopy

from twwarhammer3.battle.llm import ARRIVED_M
from twwarhammer3.battle.local_command import able
from twwarhammer3.battle.scripted import distance
from twwarhammer3.protocol import PolicyFailure, friendly_units, visible_enemies

# JUDGEMENT: Cannae witness development rules — Codex, 2026-11-05: centre engages at
# 90 m; infantry flank offset 70 m, rear offset 65 m, route deadline 180 s and idle retry
# 10 s. Other rules change this candidate's wins; no tactical necessity/readiness claim.
CLOSE_M = 90
FLANK_M = 70
REAR_M = 65
ROUTE_MS = 180000
RETRY_MS = 10000
SWORDS = "wh_main_emp_inf_swordsmen"
GREATSWORDS = "wh_main_emp_inf_greatswords"
KNIGHTS = "wh_main_emp_cav_empire_knights"


class Envelop:
    """Hold the centre, turn in the Greatswords and redirect the successful cavalry wing."""

    def __init__(self):
        self.groups = None
        self.types = None
        self.mid_z = None
        self.contact_ms = None
        self.targets, self.sent, self.last_sent = {}, {}, {}
        self.routes = {}
        self.cavalry_stage = "own_wing"
        self.seen_north = False
        self.enemy_wings = {}
        self.now = 0

    def _bind(self, units):
        expected = ((SWORDS, 4), (GREATSWORDS, 2), (KNIGHTS, 3))
        if any(u.get("x") is None or u.get("z") is None for u in units.values()):
            raise PolicyFailure("Cannae witness needs placed starting regiments")
        by_type = {kind: sorted((u for u in units.values() if u.get("type") == kind),
                                key=lambda u: (-u["z"], u["x"], u["id"]))
                   for kind, _ in expected}
        if len(units) != 9 or any(len(by_type[kind]) != n for kind, n in expected):
            raise PolicyFailure("Cannae witness needs four Swordsmen, two Greatswords, "
                                "three Knights")
        self.groups = {"centre": [u["id"] for u in by_type[SWORDS]],
                       "left": [by_type[GREATSWORDS][0]["id"]],
                       "right": [by_type[GREATSWORDS][1]["id"]],
                       "decisive": [u["id"] for u in by_type[KNIGHTS][:2]],
                       "containing": [by_type[KNIGHTS][2]["id"]]}
        self.mid_z = sum(u["z"] for u in by_type[SWORDS]) / 4
        self.types = {identity: u["type"] for identity, u in units.items()}

    def _send(self, unit, order):
        identity = unit["id"]
        lapsed = (order["type"] == "attack" and
                  (not unit.get("target") or "idle" in (unit.get("state") or []))
                  or order["type"] == "move" and "idle" in (unit.get("state") or []))
        if self.sent.get(identity) == order and not (
                lapsed and self.now - self.last_sent[identity] >= RETRY_MS):
            return []
        self.sent[identity], self.last_sent[identity] = order, self.now
        return [order]

    def _attack(self, unit, enemies):
        identity = unit["id"]
        target = next((e for e in enemies if e["id"] == self.targets.get(identity)), None)
        target = target or min(enemies, key=lambda e: distance(unit, e), default=None)
        if target is None:
            return []
        self.targets[identity] = target["id"]
        return self._send(unit, {"unit": identity, "type": "attack", "target": target["id"],
                                 "mode": "auto", "run": True, "queue": False})

    def _begin(self, unit, points, purpose):
        self.routes[unit["id"]] = {"purpose": purpose, "points": points, "next": 0,
                                    "started_ms": self.now, "arrivals": [], "status": "pending"}
        self.sent.pop(unit["id"], None)

    def _route(self, unit):
        route = self.routes[unit["id"]]
        if route["status"] != "pending":
            return None
        if not able(unit):
            route.update(status="unavailable", ended_ms=self.now)
            return []
        # An acknowledgement never advances the route. Only a fresh own position can.
        while route["next"] < len(route["points"]):
            point = route["points"][route["next"]]
            if distance(unit, point) > ARRIVED_M:
                break
            route["arrivals"].append({"point": route["next"], "time_ms": self.now,
                                       "x": unit["x"], "z": unit["z"]})
            route["next"] += 1
        if route["next"] == len(route["points"]):
            route.update(status="arrived", ended_ms=self.now)
            self.sent.pop(unit["id"], None)
            return None
        if self.now - route["started_ms"] >= ROUTE_MS:
            route.update(status="deadline", ended_ms=self.now)
            self.sent.pop(unit["id"], None)
            return None
        return self._send(unit, {"unit": unit["id"], "type": "move",
                                 **route["points"][route["next"]], "facing": None,
                                 "width": None, "run": True, "queue": False})

    def _points(self, observation, infantry, side, *, cross_z=None):
        # Geometry is derived from currently visible infantry and then frozen for this
        # route. The public terrain bounds limit waypoints, not hidden enemy positions.
        bounds = (observation.get("terrain") or {}).get("bounds")
        if not bounds:
            raise PolicyFailure("Cannae route needs public terrain bounds")

        def point(x, z):
            return {"x": round(min(bounds["max_x"] - ARRIVED_M,
                                    max(bounds["min_x"] + ARRIVED_M, x)), 1),
                    "z": round(min(bounds["max_z"] - ARRIVED_M,
                                    max(bounds["min_z"] + ARRIVED_M, z)), 1)}

        front, rear = min(e["x"] for e in infantry), max(e["x"] for e in infantry) + REAR_M
        z = (max(e["z"] for e in infantry) + FLANK_M if side == "left"
             else min(e["z"] for e in infantry) - FLANK_M)
        return [point(front - REAR_M, z), point(rear, z),
                point(rear, cross_z if cross_z is not None else
                      (max(e["z"] for e in infantry) if side == "left"
                       else min(e["z"] for e in infantry)))]

    def decide(self, observation):
        self.now = observation["time_ms"]
        roster = observation.get("friendly")
        if (not isinstance(roster, list) or any(not isinstance(u, dict)
                or not isinstance(u.get("id"), str) or not u["id"] for u in roster)
                or len({u["id"] for u in roster}) != len(roster)):
            raise PolicyFailure("Cannae witness received a malformed own roster")
        units = friendly_units(observation)
        if self.groups is None:
            self._bind(units)
        elif {identity: u.get("type") for identity, u in units.items()} != self.types:
            raise PolicyFailure("Cannae witness regiment identity or type changed")
        visible = list(visible_enemies(observation).values())
        enemies = [e for e in visible if able(e)]
        infantry = [e for e in enemies if e.get("class") == "infantry"]
        cavalry = [e for e in enemies if e.get("class") == "cavalry"]
        centre = [units[i] for i in self.groups["centre"] if i in units and able(units[i])]
        if self.contact_ms is None and any("melee" in (u.get("state") or []) for u in centre):
            self.contact_ms = self.now
        # JUDGEMENT: Enemy wing labels — Codex, 2026-11-05: first visible position assigns
        # each horse to a wing, retained by identity. Reclassifying after a crossing changes
        # this candidate's redirection cue; absence from view still never means dead.
        for enemy in (e for e in visible if e.get("class") == "cavalry"):
            self.enemy_wings.setdefault(enemy["id"], "north" if enemy["z"] >= self.mid_z
                                         else "south")
        north = [e for e in cavalry if self.enemy_wings[e["id"]] == "north"]
        south = [e for e in cavalry if self.enemy_wings[e["id"]] == "south"]
        self.seen_north = "north" in self.enemy_wings.values()
        if self.cavalry_stage == "own_wing" and self.seen_north and not north:
            self.cavalry_stage = "other_wing" if south else "rear"
        if self.cavalry_stage == "other_wing" and not south:
            self.cavalry_stage = "rear"
        orders = []
        for role, identities in self.groups.items():
            for identity in identities:
                unit = units[identity]
                route = self.routes.get(identity)
                if route and route["status"] == "pending":
                    moves = self._route(unit)
                    if moves is not None:
                        orders += moves
                        continue
                if not able(unit):
                    continue
                if role == "centre":
                    if enemies and min(distance(unit, e) for e in enemies) <= CLOSE_M:
                        orders += self._attack(unit, enemies)
                elif role in {"left", "right"}:
                    if self.contact_ms is None:
                        continue
                    if route is None and infantry:
                        self._begin(unit, self._points(observation, infantry, role),
                                    "infantry_flank")
                        orders += self._route(unit) or []
                    else:
                        orders += self._attack(unit, infantry or enemies)
                elif role == "decisive":
                    if self.cavalry_stage == "own_wing":
                        orders += self._attack(unit, north)
                    elif route is None and infantry:
                        z = sum(e["z"] for e in south) / len(south) if south else None
                        self._begin(unit, self._points(observation, infantry, "left", cross_z=z),
                                    "cavalry_redeployment")
                        orders += self._route(unit) or []
                    else:
                        orders += self._attack(unit, south if self.cavalry_stage == "other_wing"
                                               else infantry or enemies)
                else:
                    orders += self._attack(unit, south or infantry or enemies)
        return orders

    def acknowledge(self, ack, latency):
        for result in ack.get("results", []):
            if not result.get("ok"):
                self.sent.pop(result.get("unit"), None)

    def metadata(self):
        return deepcopy({"type": "cannae_envelop", "groups": self.groups,
                         "contact_ms": self.contact_ms, "cavalry_stage": self.cavalry_stage,
                         "seen_north": self.seen_north,
                         "enemy_wings": self.enemy_wings,
                         "routes": self.routes, "targets": self.targets})
