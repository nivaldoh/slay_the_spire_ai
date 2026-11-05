"""Free challenge control: the whole army runs from visible enemies and never attacks.

Reference: docs/twwarhammer3/cannae-comparison.md item 4 "timer defence". Each Cannae and
air candidate plays as defender with timeout_winner us, so a surviving army can win at the
timer. Unplayed: no tactical claim rests on it, and it may lose.
"""

from twwarhammer3.battle.local_command import able
from twwarhammer3.battle.scripted import distance
from twwarhammer3.protocol import PolicyFailure, friendly_units, visible_enemies

# JUDGEMENT: Evade parameters — Claude Code, 2026-11-05: eight points 30 m inside the bounds,
# 10 s retry, stopped = no "moving" flag. Other values change how long the army lasts; the
# timer challenge rests on them.
INSET_M = 30
RETRY_MS = 10000


class Evade:
    """Every able unit runs to the open map point farthest from the visible enemies."""

    def __init__(self):
        self.points, self.sent_ms, self.refused = {}, {}, []

    def decide(self, observation: dict) -> list[dict]:
        enemies = visible_enemies(observation).values()
        if not enemies:
            return []
        bounds = (observation.get("terrain") or {}).get("bounds")
        if not bounds:
            raise PolicyFailure("Evade needs public terrain bounds") from ValueError("no bounds")
        xs = (bounds["min_x"] + INSET_M, (bounds["min_x"] + bounds["max_x"]) / 2,
              bounds["max_x"] - INSET_M)
        zs = (bounds["min_z"] + INSET_M, (bounds["min_z"] + bounds["max_z"]) / 2,
              bounds["max_z"] - INSET_M)
        points = [{"x": x, "z": z} for x in xs for z in zs if (x, z) != (xs[1], zs[1])]
        points = [point for point in points if point not in self.refused]
        if not points:
            # The cause ends the episode: a bare PolicyFailure is a forfeit, which would leave
            # the army on its last orders and credit any timer win to Evade.
            raise PolicyFailure("Evade: the engine refused all eight points") \
                from RuntimeError("no open point left")
        clearance = [min(distance(point, enemy) for enemy in enemies) for point in points]
        farthest = [point for point, value in zip(points, clearance) if value == max(clearance)]
        now = observation["time_ms"]
        orders = []
        for unit_id, unit in friendly_units(observation).items():
            if not able(unit):
                continue
            point = min(farthest, key=lambda candidate: distance(unit, candidate))
            changed = point != self.points.get(unit_id)
            stopped = "moving" not in unit.get("state", [])
            waited = now - self.sent_ms.get(unit_id, -RETRY_MS) >= RETRY_MS
            if (changed or stopped) and waited:
                self.points[unit_id], self.sent_ms[unit_id] = point, now
                orders.append({"unit": unit_id, "type": "move", **point, "run": True})
        return orders

    def acknowledge(self, ack: dict, latency: dict) -> None:
        # JUDGEMENT: Evade refused points — Claude Code, 2026-11-05: a point refused as unreachable
        # leaves the eight for the army and battle (calibration.py open_point), costing up to 10 s;
        # with none left the job fails. A "#" filter, per-unit lists or holding alter the challenge.
        self.refused += [self.points[result["unit"]] for result in ack.get("results", [])
                         if result.get("error") == "unreachable"]

    def metadata(self) -> dict:
        return {"type": "evade"}
