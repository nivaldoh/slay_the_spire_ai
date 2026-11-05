"""One executor for the six development diagnostics; ordinary public orders only.

The supplied owner plan is the reference. This is an adaptation of pin/flank tasks,
not evidence of a new coordination mechanism. All numerical choices rest on JUDGEMENT
in docs/twwarhammer3/support-timing.md. No engine effect is inferred from an ack.
"""

import argparse
import copy
import json
import math
from pathlib import Path

from gameai.provenance import committed_revision, source_fingerprints
from twwarhammer3.battle.play import SOURCES
from twwarhammer3.battle.setup import scenarios
from twwarhammer3.protocol import ProtocolError

# Owner selected the translated revision after the v1 deployment failure (2026-11-04).
SCENARIO = "emp-support-timing-v2"
TYPES = {"infantry": "wh_main_emp_inf_swordsmen", "cavalry": "wh_main_emp_cav_empire_knights",
         "enemy": "wh_main_emp_inf_greatswords"}
ARMS = ("direct", "opening", "scheduled", "contact", "delayed", "none")
# Rests on JUDGEMENT docs/twwarhammer3/support-timing.md Diagnostic design.
SCHEDULE_MS, DELAY_MS, LEFT_M, BEHIND_M, REPEATS = 30000, 12000, 80, 60, 3
OUT = {"routing", "shattered", "leaving", "not_deployed", "deploying"}


def identities(observation):
    """Bind by type, never recruitment order. Missing/duplicate identity is a defect."""
    result = {}
    for role, kind in TYPES.items():
        side = "enemy_roster" if role == "enemy" else "friendly"
        matches = [u for u in observation.get(side, []) if u.get("type") == kind]
        if len(matches) != 1 or not matches[0].get("id"):
            raise ProtocolError(f"support timing: ambiguous {role} identity")
        result[role] = matches[0]["id"]
    if len(set(result.values())) != 3:
        raise ProtocolError("support timing: duplicate unit IDs")
    return result


def able(unit):
    return (unit.get("men", 0) > 0 and not unit.get("error")
            and not OUT.intersection(unit.get("state", [])))


def attack(unit, target, queued=False):
    return {"type": "attack", "unit": unit, "target": target, "mode": "melee",
            "run": True, "queue": queued}


def flank(unit, enemy):
    # WH3 bearing: 0 faces +z; increasing clockwise. Left is -x at bearing 0.
    theta = math.radians(enemy["bearing"])
    x = enemy["x"] - LEFT_M * math.cos(theta)
    z = enemy["z"] + LEFT_M * math.sin(theta)
    return [{"type": "move", "unit": unit, "x": x, "z": z, "run": True,
             "facing": None, "width": None, "queue": False},
            {"type": "move", "unit": unit, "x": x - BEHIND_M * math.sin(theta),
             "z": z - BEHIND_M * math.cos(theta), "run": True,
             "facing": None, "width": None, "queue": True},
            attack(unit, enemy["id"], True)]


class Diagnostic:
    """Single persistent attack/route per regiment; no retries or hidden-state adaptation."""

    arm = "contact"

    def __init__(self):
        self.ids = None
        self.infantry_sent = False
        self.cue = None
        self.route = None
        self.submitted = None
        self.pending = []

    def decide(self, observation):
        if observation.get("phase") != "Deployed" or observation.get("result"):
            return []
        ids = identities(observation)
        if self.ids and self.ids != ids:
            raise ProtocolError("support timing: unit identities changed")
        self.ids = ids
        units = {u["id"]: u for u in observation["friendly"]}
        infantry, cavalry = units[ids["infantry"]], units[ids["cavalry"]]
        enemy = next((u for u in observation.get("enemy", []) if u["id"] == ids["enemy"]), None)
        if not enemy or not able(enemy):
            return []
        if enemy.get("type") != TYPES["enemy"]:
            raise ProtocolError("support timing: visible enemy identity changed")
        now = observation["time_ms"]
        orders = []
        if not self.infantry_sent and able(infantry):
            orders.append(attack(ids["infantry"], ids["enemy"]))
            self.infantry_sent = True
        contact = ("melee" in infantry.get("state", []) and "melee" in enemy.get("state", [])
                   and able(infantry))
        trigger = (self.arm in ("direct", "opening")
                   or self.arm == "scheduled" and now >= SCHEDULE_MS
                   or self.arm in ("contact", "delayed") and contact)
        if self.cue is None and trigger:
            self.cue = {"time_ms": now, "seq": observation["seq"], "ids": dict(ids),
                        "enemy": {k: enemy.get(k) for k in ("x", "z", "bearing", "state")},
                        "infantry_state": list(infantry.get("state", []))}
            self.route = ([attack(ids["cavalry"], ids["enemy"])] if self.arm == "direct"
                          else flank(ids["cavalry"], enemy))
        delay = DELAY_MS if self.arm == "delayed" else 0
        if (self.cue is not None and self.submitted is None and able(cavalry)
                and now >= self.cue["time_ms"] + delay):
            orders.extend(copy.deepcopy(self.route))
            self.submitted = {"time_ms": now, "seq": observation["seq"]}
        self.pending = copy.deepcopy(orders)
        return orders

    def acknowledge(self, ack, latency):
        # No silent repair or retry: a fresh version/comparison is needed after a defect.
        expected = {(i + 1, o["unit"]) for i, o in enumerate(self.pending)}
        received = {(r.get("index"), r.get("unit")) for r in ack.get("results", [])}
        if (received != expected or len(ack.get("results", [])) != len(expected)
                or any(r.get("ok") is not True for r in ack.get("results", []))):
            raise ProtocolError("support timing: missing or failed order acknowledgement")
        self.pending = []

    def metadata(self):
        return copy.deepcopy({"type": "support_timing", "version": 1, "arm": self.arm,
                              "ids": self.ids, "cue": self.cue, "route": self.route,
                              "submitted": self.submitted})


class Direct(Diagnostic):
    arm = "direct"


class Opening(Diagnostic):
    arm = "opening"


class Scheduled(Diagnostic):
    arm = "scheduled"


class Contact(Diagnostic):
    arm = "contact"


class Delayed(Diagnostic):
    arm = "delayed"


class NoneIntervention(Diagnostic):
    arm = "none"


CLASSES = dict(zip(ARMS, (Direct, Opening, Scheduled, Contact, Delayed, NoneIntervention),
                   strict=True))


def make_plan(output: Path):
    """SWE-bench swebench/harness/reporting.py pattern: enumerate every planned attempt.

    The ordinary queue runs these fresh-launch jobs once and stops on the first failure.
    This writes only a plan; it is not live-check approval.
    """
    revision = committed_revision("freezing support timing diagnostics", SOURCES)
    # JUDGEMENT: Diagnostic launch caps — Codex, 2026-11-04: reuse 1000/250 ms observation/
    # tick and 900/1320 s setup/episode caps, with a 2280 s watchdog covering both. Different
    # cadence or truncation limits alter the comparison; this is still a proposed live check.
    jobs = []
    for block in range(REPEATS):
        for arm in ARMS[block:] + ARMS[:block]:
            name = f"block-{block + 1}-{arm}"
            jobs.append({"block": block + 1, "arm": arm, "output": str(output.parent / name),
                         "args": ["--scenario", SCENARIO, "--policy",
                                  f"{__name__}:{CLASSES[arm].__name__}", "--episodes", "1",
                                  "--observe-ms", "1000", "--tick-ms", "250", "--interval-ms", "0",
                                  "--start-timeout", "900", "--episode-timeout", "1320",
                                  "--run-timeout", "2280", "--record-replay"],
                         # Rests on JUDGEMENT Diagnostic launch caps above and Diagnostic
                         # design in docs/twwarhammer3/support-timing.md. Pin CLI defaults too.
                         "config": {"policy": f"{__name__}:{CLASSES[arm].__name__}",
                                    "episodes": 1, "observe_ms": 1000, "tick_ms": 250,
                                    "interval_ms": 0, "start_timeout": 900,
                                    "episode_timeout": 1320, "run_timeout": 2280,
                                    "speed": 1, "pause": False, "delay_seconds": "0",
                                    "record_replay": True, "stills": False, "attach": False}})
    plan = {"kind": SCENARIO, "source_revision": revision,
            "source_files": source_fingerprints(SOURCES), "scenario": scenarios()[SCENARIO],
            "status": "owner_agreed_exploratory_check", "keep_going": False, "jobs": jobs}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as file:
        json.dump(plan, file, indent=2)
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new queue plan JSON; never launches")
    args = parser.parse_args()
    # Importable policy names must survive python -m execution.
    from twwarhammer3.battle.support_timing import make_plan
    make_plan(args.output.resolve())


if __name__ == "__main__":
    main()
