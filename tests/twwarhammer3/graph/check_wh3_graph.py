"""Initial graph effect check: no-order control, move, then contact/charge; $0, fresh 1x.

Launch pattern: team/check_wh3_team.py; graph reference: graph-as-policy
tests/runtime/test_executor.py at 71549e1. Recount never launches a game.
"""

import argparse
import json
import math
import time
from pathlib import Path

from gameai.provenance import REPO_ROOT, committed_revision, sha256, source_fingerprints, write_json
from gameai.windows_game import conflicting_games
from spire.engine import runtime as spire_runtime
from twwarhammer3.battle import configured, graph, play, setup, team
from twwarhammer3.battle.digest import ONE_X
from twwarhammer3.battle.skill_contracts import ARRIVAL_M
from twwarhammer3.engine.doctor import collect_diagnostics
from twwarhammer3.engine.mailbox import Mailbox
from twwarhammer3.engine.runtime import (
    BRIDGE_DIR,
    OwnedGame,
    RuntimeLock,
    prepare_runtime,
    running_pids,
)

# JUDGEMENT: Probe bounds — Codex, 2026-11-01: 5 s settling, 60 m forward, 165 s move/control.
# Owner approved 540 s contact on 2026-11-01 after the first cutoff. Other geometry/bounds
# change which effects this feasibility check can see; no benchmark family is selected.
SETTLE_MS = 5000
MOVE_M = 60
WALL_LIMITS = {"control": 165, "move": 165, "contact": 540}
COMPOSITION = REPO_ROOT / "configs/twwarhammer3/graphs/contact-team.json"
CONFIG = {"speed": 1, "pause": False, "observe_ms": 1000, "tick_ms": 250,
          "record_replay": True, "stills": False, "interval_ms": 0, "delay_ms": 0,
          "start_timeout": 240, "observation_timeout": 10,
          "run_timeout": 900}  # frontend/loading plus the contact window and cleanup


def waypoint(observation):
    unit, = [u for u in observation["friendly"] if u["type"] == team.KNIGHT]
    angle = math.radians(unit["bearing"])
    return unit["id"], {"x": unit["x"] + MOVE_M * math.sin(angle),
                        "z": unit["z"] + MOVE_M * math.cos(angle)}


class MoveProbe:
    """Freeze one graph from the initial public waypoint; optionally issue no orders."""

    def __init__(self, control=False):
        self.control, self.policy = control, None
        self.start_ms = None
        self.events = []

    def decide(self, observation):
        if self.start_ms is None:
            self.start_ms = observation["time_ms"]
        if self.policy is None:
            if observation["time_ms"] - self.start_ms < SETTLE_MS:
                return []
            uid, point = waypoint(observation)
            spec = {"version": graph.VERSION, "entry": "move", "nodes": {
                "move": {"op": "move", "inputs": {"units": [uid], "point": point},
                         "next": {"succeeded": "end", "failed": "end", "cancelled": "end"}},
                "end": {"op": "end", "inputs": {}, "next": {}}}}
            self.policy = graph.GraphPolicy(spec)
            self.events.append({"event": "probe_graph", "source_seq": observation["seq"],
                                "unit": uid, "point": point, "card": self.policy.card})
        return [] if self.control else self.policy.decide(observation)

    def acknowledge(self, ack, latency):
        if self.policy is not None and not self.control:
            self.policy.acknowledge(ack, latency)

    def dispatch_guard(self, orders, observation):
        if self.policy is not None:
            self.policy.dispatch_guard(orders, observation)

    def metadata(self):
        return self.policy.metadata() if self.policy is not None else {"type": "settling"}

    def drain_events(self):
        events, self.events = self.events, []
        return events + (self.policy.drain_events() if self.policy is not None else [])

    def close(self):
        if self.policy is not None:
            self.policy.close()


def unit(observation, uid, side="friendly"):
    return next(u for u in observation[side] if u["id"] == uid)


def distance(a, b):
    return math.hypot(a["x"] - b["x"], a["z"] - b["z"])


def acknowledged(decision, samples):
    ack = next(s["observation"]["orders"] for s in samples
               if (s["observation"].get("orders") or {}).get("request") == decision["request"])
    assert ack.get("accepted") is not False
    assert len(ack["results"]) == len(decision["orders"]) > 0
    for index, (result, order) in enumerate(zip(ack["results"], decision["orders"]), 1):
        assert result["ok"] is True and result["index"] == index
        assert result["unit"] == order["unit"]
    return ack


def completions(events, op, member=None):
    """Match runtime transitions to their declared inputs, then check them against raw state."""
    starts = {}
    for event in events:
        if event.get("event") == "member_event":
            owner, record = event["member"], event["record"]
        else:
            owner, record = None, event
        if owner != member or "node" not in record:
            continue
        key = record["node"], record["node_run"]
        if record.get("event") == "started" and record["op"] == op:
            starts[key] = record["inputs"]
        if (record.get("event") == "transition" and record.get("status") == "succeeded"
                and key in starts):
            yield starts[key], record["source"]


def assess(kind, events, samples):
    """Raw state establishes effects; a node's completion must agree with its raw witness."""
    views = [s["observation"] for s in samples if s["observation"].get("phase") == "Deployed"]
    assert views and all(v.get("speed") == 1 and not v.get("awaiting_orders") for v in views)
    battle = views[0]["battle"]
    assert isinstance(battle, str) and battle
    assert all(s["observation"]["battle"] == battle for s in samples)
    timed = [s for s in samples if s["observation"].get("phase") == "Deployed"]
    elapsed_ns = timed[-1]["written_ns"] - timed[0]["written_ns"]
    assert elapsed_ns > 0
    ratio = (views[-1]["time_ms"] - views[0]["time_ms"]) * 10**6 / elapsed_ns
    assert ONE_X[0] <= ratio <= ONE_X[1]  # owner's whole-interval Windows-clock band
    common = {"battle": battle, "clock_ratio": ratio}
    decisions = [e for e in events if e.get("kind") == "decision" and e["orders"]]
    by_seq = {v["seq"]: v for v in views}
    if kind in ("control", "move"):
        init, = [e for e in events if e.get("event") == "probe_graph"]
        source = by_seq[init["source_seq"]]
        cavalry, = [u for u in source["friendly"] if u["type"] == team.KNIGHT]
        expected_uid, expected_point = cavalry["id"], init["point"]
        dx, dz = expected_point["x"] - cavalry["x"], expected_point["z"] - cavalry["z"]
        assert init["unit"] == expected_uid
        assert math.isclose(math.hypot(dx, dz), MOVE_M, abs_tol=1e-6)
        heading = math.degrees(math.atan2(dx, dz))
        assert abs((heading - cavalry["bearing"] + 180) % 360 - 180) < 1e-6
        after = [v for v in views if v["seq"] >= source["seq"]]
        arrivals = [v for v in after
                    if distance(unit(v, expected_uid), expected_point) <= ARRIVAL_M]
        assert after[-1]["time_ms"] - source["time_ms"] >= SETTLE_MS
        if kind == "control":
            assert not decisions and not arrivals
            return {**common, "passed": True, "unit": expected_uid, "arrivals": 0,
                    "duration_ms": after[-1]["time_ms"] - source["time_ms"]}
        assert decisions and arrivals
        for decision in decisions:
            for order in decision["orders"]:
                assert order["unit"] == expected_uid and order["type"] == "move"
                assert {axis: order[axis] for axis in ("x", "z")} == expected_point
            acknowledged(decision, samples)
        ack = acknowledged(decisions[0], samples)
        # Arrival before delivery cannot be credited to this order, even if later
        # frames remain at the waypoint. Bind both effect and completion to delivery.
        assert arrivals[0]["time_ms"] > ack["applied_ms"]
        assert any(inputs == {"units": [expected_uid], "point": expected_point}
                   and source["battle"] == battle
                   and source["time_ms"] > ack["applied_ms"]
                   and any(v["seq"] == source["seq"] and v["time_ms"] == source["time_ms"]
                           for v in arrivals)
                   for inputs, source in completions(events, "move"))
        return {**common, "passed": True, "unit": expected_uid,
                "arrival_ms": arrivals[0]["time_ms"], "ack_ms": ack["applied_ms"],
                "arrival_offset_ms": arrivals[0]["time_ms"] - source["time_ms"]}
    assert kind == "contact"
    first = views[0]
    knight, = [u for u in first["friendly"] if u["type"] == team.KNIGHT]
    line, = [u for u in first["friendly"] if u["type"] == team.SWORD]
    attacks = []
    line_orders = []
    for decision in decisions:
        behavior = decision["behavior"]
        basis = by_seq[behavior["source_seq"]]
        assert behavior["source_ms"] == basis["time_ms"]
        ack = acknowledged(decision, samples)
        assert ack["applied_ms"] >= basis["time_ms"]
        for order in decision["orders"]:
            assert order["type"] == "attack"
            target = unit(basis, order["target"], "enemy")  # must be visible on its source
            if behavior["member"] == "cavalry":
                assert order["unit"] == knight["id"] and "melee" in target.get("state", [])
                attacks.append((order, ack))
            else:
                assert behavior["member"] == "line" and order["unit"] == line["id"]
                line_orders.append(order)
    assert line_orders and attacks
    witnesses = [(order, v) for order, ack in attacks for v in views
                 if v["time_ms"] > ack["applied_ms"]
                 and "melee" in unit(v, knight["id"]).get("state", [])
                 and unit(v, knight["id"]).get("target") == order["target"]]
    assert witnesses
    assert any(inputs["units"] == [knight["id"]]
               and source["battle"] == battle
               and any(inputs["target"] == order["target"] and source["seq"] == v["seq"]
                       and source["time_ms"] == v["time_ms"]
                       for order, v in witnesses)
               for inputs, source in completions(events, "charge", "cavalry"))
    order, view = witnesses[0]
    return {**common, "passed": True, "unit": knight["id"], "target": order["target"],
            "contact_ms": view["time_ms"], "cavalry_batches": len(attacks)}


def recount(output):
    results, hashes = {}, {}
    for kind in WALL_LIMITS:
        try:
            def read(name):
                path = output / kind / name
                hashes[f"{kind}/{name}"] = sha256(path)
                return path.read_text()

            events = [json.loads(line) for line in read("episode/trace.jsonl").splitlines()]
            samples = [json.loads(line) for line in read("observations.jsonl").splitlines()]
            manifest = json.loads(read("manifest.json"))
            assert manifest["closed"] and not manifest["remaining_pids"]
            assert manifest["result"]["status"] in ("truncated", "won", "lost", "draw")
            results[kind] = assess(kind, events, samples)
            assert manifest["result"]["battle"] == results[kind]["battle"]
        except (OSError, KeyError, AssertionError, StopIteration, ValueError) as exc:
            results[kind] = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
    complete = all(r["passed"] for r in results.values())
    matched = complete and results["control"]["duration_ms"] >= results["move"]["arrival_offset_ms"]
    fresh = complete and len({r["battle"] for r in results.values()}) == len(WALL_LIMITS)
    return {"passed": bool(complete and matched and fresh), "probes": results,
            "control_covers_arrival": bool(matched), "fresh_battles": bool(fresh),
            "checker_sha256": sha256(Path(__file__)), "evidence": hashes}


def run(output):
    revision = committed_revision("graph live check", play.SOURCES)
    fingerprints = source_fingerprints(play.SOURCES)
    output.mkdir(parents=True)
    environment = collect_diagnostics()
    write_json(output / "environment.json", environment)
    if environment["blockers"]:
        raise RuntimeError(environment["blockers"])
    for warning in environment["warnings"]:
        print("WARNING: " + warning, flush=True)
    scenario = setup.scenarios()["emp-knights-emp-swordsmen"]
    steps = setup.scenario_steps(scenario, build_id=environment["game"]["steam_build_id"])
    write_json(output / "plan.json", {"source_revision": revision, "source_files": fingerprints,
               "scenario": scenario, "config": CONFIG, "wall_limits_s": WALL_LIMITS,
               "checker_sha256": sha256(Path(__file__)), "budget_usd": 0, "total_cap_s": 1800})
    deadline = time.monotonic() + 1800
    for kind, duration in WALL_LIMITS.items():
        if time.monotonic() + CONFIG["run_timeout"] + 30 > deadline:
            break
        if source_fingerprints(play.SOURCES) != fingerprints:
            raise RuntimeError("sources changed during verification")
        if conflicting_games(Path(spire_runtime.WINDOWS_GAME_DIR), spire_runtime.CONFLICTS):
            raise RuntimeError("Spire running; no concurrent game controllers")
        directory = output / kind
        directory.mkdir()
        manifest = {"kind": kind, "source_revision": revision, "closed": False}
        write_json(directory / "manifest.json", manifest)
        print(f"probe {kind}", flush=True)
        with RuntimeLock(), (directory / "observations.jsonl").open("x", buffering=1) as stream:
            class RecordingMailbox(Mailbox):
                def wait_observation(self, **kwargs):
                    value = super().wait_observation(**kwargs)
                    stream.write(json.dumps({"written_ns": self.written_ns,
                                             "observation": value}) + "\n")
                    return value

            manifest["deployment"] = prepare_runtime()
            mailbox = RecordingMailbox(BRIDGE_DIR, job=f"{output.name}-{kind}")
            mailbox.reset()
            config = {**CONFIG, "policy": "configured", "episode_timeout": duration}
            make = (configured.factory(COMPOSITION, {}) if kind == "contact"
                    else lambda: MoveProbe(control=kind == "control"))
            try:
                with (mailbox.owned_session(play.session(config)),
                      OwnedGame(directory / "game.log", timeout=CONFIG["run_timeout"]) as game):
                    manifest["game"] = game.info
                    play.start_frontend(mailbox, config, directory, steps)
                    manifest["setup_checks"] = setup.check_menu(scenario, directory)
                    manifest["result"] = play.play_episode(directory / "episode", config, make,
                                                           mailbox, not_battle=None,
                                                           scenario=scenario)
            finally:
                manifest["remaining_pids"] = running_pids()
                manifest["closed"] = True
                write_json(directory / "manifest.json", manifest)
        if manifest["result"]["status"] not in ("truncated", "won", "lost", "draw"):
            break  # preserve a failed launch; never silently replace it
    report = recount(output)
    write_json(output / "checks.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--recount", type=Path)
    args = parser.parse_args()
    result = recount(args.recount) if args.recount else run(args.output)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
