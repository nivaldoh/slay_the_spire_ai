"""Fixed-schedule foil: replay a won battle's accepted orders by battle time on a fresh launch.

Evaluation guideline 2.4 proposes it for a card that claims reacting to the enemy matters: a
foil that replays a witness win's orders without reacting tests that claim. ``build`` turns
one recorded episode (manifest, trace and result as ``play`` writes them) into a schedule, and
``ReplaySchedule`` plays it, reading only the public observation. local_scripts.FixedSchedule
is another foil (each group runs east at a set time) and replays nothing.

A batch is due once the observation the foil decides on reaches the battle time at which the
engine applied the witness's batch. Under play's added age D (``delay_ms``) the foil decides on
observations D old, so the engine applies each replayed batch at least D plus the foil's own
latency after it applied the witness's. The schedule's ``source`` keeps the witness's
``delay_ms`` and ``interval_ms`` so that a report can compare the two timings.

Reference: robomimic robomimic/scripts/playback_dataset.py, playback_trajectory_with_env, plays
a demonstration's actions open-loop after a reset. It steps by index because its simulator's
step is fixed; here a batch goes by battle time, because decision gaps change with latency.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from gameai.provenance import sha256
from twwarhammer3.battle.scripted import distance
from twwarhammer3.protocol import PolicyFailure, friendly_units, visible_enemies

VERSION = 1
PLACE = ("type", "x", "z")
MOVEMENT = ("move", "attack", "halt")


def digest(value) -> str:
    """SHA-256 of canonical JSON, as checkpoint.digest hashes a scenario."""
    text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def build(episode) -> dict:
    """The engine-accepted orders of one recorded won episode, in batches at their applied
    battle time, with each own unit's first position and each enemy target's last public one."""
    episode = Path(episode)
    manifest_path, trace_path = episode.parent / "manifest.json", episode / "trace.jsonl"
    manifest = json.loads(manifest_path.read_text())
    result = json.loads((episode / "result.json").read_text())
    if result["status"] != "won":
        raise ValueError(f"{episode}: a schedule replays a won battle, not {result['status']!r}")
    start, seen, sent, batches = None, {}, {}, []
    with trace_path.open() as rows:
        for line in rows:
            row = json.loads(line)
            if row["kind"] == "observation":  # a controller's input: the public view
                view = row["observation"]
                if start is None and view.get("friendly"):
                    start = {unit["id"]: {key: unit.get(key) for key in PLACE}
                             for unit in view["friendly"]}
                seen.update({enemy["id"]: {key: enemy.get(key) for key in PLACE}
                             for enemy in view.get("enemy", [])})
            elif row["kind"] == "decision" and row["orders"]:
                sent[row["request"]] = [
                    {"order": order, **({"target": seen[order["target"]]}
                                        if order.get("target") in seen else {})}
                    for order in row["orders"]]
            elif row["kind"] == "ack" and row["request"] in sent:
                entries, results = sent.pop(row["request"]), row["ack"].get("results", [])
                if any("index" not in item for item in results):  # older traces
                    raise ValueError(f"{episode}: acknowledgements without order indices")
                kept = [entries[item["index"] - 1] for item in results if item.get("ok")]
                if kept:
                    batches.append({"time_ms": row["ack"]["applied_ms"],
                                    "request": row["request"], "orders": kept})
    if start is None:
        raise ValueError(f"{episode}: no observation with own units")
    return {"version": VERSION, "scenario": manifest.get("config", {}).get("scenario"),
            "scenario_sha256": digest(manifest["scenario"]),
            "source": {"job": episode.parent.name, "episode": episode.name,
                       "policy": result.get("policy"), "delay_ms": result["delay_ms"],
                       "interval_ms": manifest["config"]["interval_ms"],
                       "source_revision": manifest.get("source_revision"),
                       "manifest_sha256": sha256(manifest_path),
                       "trace_sha256": sha256(trace_path)},
            "start": start, "batches": batches}


# JUDGEMENT: Replay carried out — Claude, 2026-11-08: the engine accepted at least 90% of the orders
# due by the last decision, less any it never answered as the battle ended (none due: not carried
# out). Another share, or all scheduled orders as the base, changes which foil launches count.
def carried_out(accepted: int, due: int) -> bool:
    return due > 0 and 10 * accepted >= 9 * due


def bind(start: dict, units: dict) -> tuple[dict, float]:
    """Recorded own id -> this launch's id, and the largest distance between paired starts.
    Each recorded unit in turn takes the nearest unpaired unit of its type, as
    setup.match_deployment pairs placements."""
    if any(unit.get(key) is None for unit in units.values() for key in PLACE):
        raise PolicyFailure("replay needs every own unit typed and placed") from ValueError(
            "unplaced unit at the first observation")
    if Counter(place["type"] for place in start.values()) != Counter(
            unit["type"] for unit in units.values()):
        raise PolicyFailure("replay: this launch's own units differ from the recorded ones") \
            from ValueError("roster differs")
    left, bound, farthest = dict(units), {}, 0.0
    for recorded, place in start.items():
        nearest = min((unit for unit in left.values() if unit["type"] == place["type"]),
                      key=lambda unit: (distance(unit, place), unit["id"]))
        bound[recorded] = nearest["id"]
        farthest = max(farthest, distance(nearest, place))
        del left[nearest["id"]]
    return bound, farthest


class ReplaySchedule:
    """Replays a won battle's accepted orders on a fresh launch, each batch once the observation
    it decides on reaches the battle time the witness's batch was applied (later under added age).

    Own units are paired once, at the first observation; each attack picks its target when it
    is sent. Nothing else reacts to the battle. On close it records whether it carried out its
    play (``carried_out``): play writes the trace row ``{"kind": "team", "event":
    "replay_schedule"}`` through drain_events, as it writes GraphPolicy's rows. Its counts:
    ``due``, orders whose time came by the last decision; ``unanswered``, those of the last
    decision that the engine never answered because the battle ended; ``sent``, orders the
    engine answered; ``accepted``, those it applied; ``unmatched``, orders dropped for want of
    a unit or target.
    """

    def __init__(self, schedule: dict, *, scenario: dict):
        if schedule.get("version") != VERSION:
            raise ValueError(f"replay schedule version {schedule.get('version')!r}, not {VERSION}")
        # JUDGEMENT?: Replay identity — Claude, 2026-11-08: the whole resolved scenario declaration
        # must hash alike; cards compare map, armies, expect, attacker, battle type. Another key
        # admits other schedules; which launches may run this foil rests on it.
        if schedule["scenario_sha256"] != digest(scenario):
            raise ValueError("the schedule was recorded under another scenario declaration")
        self.schedule = schedule
        self.card = {"schedule_sha256": digest(schedule), "source": schedule["source"],
                     "scenario_sha256": schedule["scenario_sha256"]}
        self.units, self.now, self.next, self.bind_max_m = None, None, 0, None
        self.sent = self.accepted = self.unmatched = self.unanswered = 0
        self.events = []

    def decide(self, observation: dict) -> list[dict]:
        self.now = observation["time_ms"]
        friendly = friendly_units(observation)
        if self.units is None:
            self.units, self.bind_max_m = bind(self.schedule["start"], friendly)
        enemies = list(visible_enemies(observation).values())
        batches, orders, ordered = self.schedule["batches"], [], set()
        # JUDGEMENT: Replay time — Claude, 2026-11-08: due when the basis reaches applied_ms, so
        # at added age D a batch lands D plus latency after the witness's; due at the recorded basis
        # time roughly matches the witness at the same cell. Foil losses at 5 s / 5 s rest on it.
        # JUDGEMENT?: Replay merge — Claude, 2026-11-08: due batches join one decision unless one
        # orders a unit already ordered there; one batch a decision would delay later ones.
        while self.next < len(batches) and batches[self.next]["time_ms"] <= self.now:
            entries = batches[self.next]["orders"]
            if ordered & {self.units.get(entry["order"]["unit"], entry["order"]["unit"])
                          for entry in entries}:
                break
            self.next += 1
            for entry in entries:
                order = self._remap(entry, friendly, enemies)
                if order is None:
                    self.unmatched += 1
                    continue
                orders.append(order)
                ordered.add(order["unit"])
        self.unanswered = len(orders)  # until acknowledged; play may also discard them
        return orders

    def _remap(self, entry: dict, friendly: dict, enemies: list[dict]) -> dict | None:
        """The order for this launch's units, or None when its unit or target has no match."""
        order = dict(entry["order"])
        if order["unit"] != "army":
            order["unit"] = self.units.get(order["unit"])
            if order["unit"] not in friendly:
                return None
        # JUDGEMENT: Replay remap — Claude, 2026-11-08: an enemy target becomes the visible enemy of
        # its type nearest its last public position, else the order is dropped. Haengju's draft
        # falls back to any type; which unit each foil attack hits, and its wins, rest on it.
        last = entry.get("target")
        if last is not None:
            same = [enemy for enemy in enemies if enemy.get("type") == last["type"]]
            if not same:
                return None
            nearest = min(same, key=lambda enemy: (distance(enemy, last), enemy["id"]))
            order["target"] = nearest["id"]
        elif order.get("target") is not None:  # an ability on an own unit
            order["target"] = self.units.get(order["target"])
            if order["target"] not in friendly:
                return None
        return order

    def acknowledge(self, ack: dict, latency: dict) -> None:
        results = ack.get("results", [])
        if "validation_error" not in ack:  # play voided that batch before the engine saw it
            self.sent += len(results)
        self.accepted += sum(1 for item in results if item.get("ok"))
        self.unanswered = 0

    def due(self) -> int:
        """Orders whose recorded time has come by the last decision, sent or not."""
        if self.now is None:
            return 0
        return sum(len(batch["orders"]) for batch in self.schedule["batches"]
                   if batch["time_ms"] <= self.now)

    def metadata(self) -> dict:
        return {"type": "replay_schedule", "version": VERSION,
                "schedule_sha256": self.card["schedule_sha256"]}

    def close(self) -> None:
        due = self.due()
        self.events.append({"event": "replay_schedule", "due": due, "unanswered": self.unanswered,
                            "sent": self.sent, "accepted": self.accepted,
                            "unmatched": self.unmatched, "bind_max_m": self.bind_max_m,
                            "carried_out": carried_out(self.accepted, due - self.unanswered)})

    def drain_events(self) -> list[dict]:
        events, self.events = self.events, []
        return events
