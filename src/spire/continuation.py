"""Collect and audit one fixed two-combat segment, independently of v1 rollouts."""

import hashlib
import json
import math
import signal
import subprocess
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from spire.bridge import BridgeError, BridgeServer
from spire.continuation_protocol import (
    GAME_SEED,
    INITIAL_START_SHA256,
    TRANSIT_VERSION,
    choose_transit,
    persistent_state,
    require,
    transit_decision,
    validate_combat,
    validate_transit_action,
)
from spire.doctor import collect_diagnostics, collect_profile
from spire.evidence import normalized_observation_fingerprint
from spire.policies import EndTurnPolicy, StarterHeuristicPolicy
from spire.protocol import ProtocolError, combat_outcome, decision_from_message, validate_action
from spire.rollout import BRIDGE_PORT, prefix_command, source_fingerprints, write_json
from spire.runtime import (
    GAME_DIR,
    PINS,
    OwnedGame,
    RuntimeLock,
    prepare_runtime,
    sha256,
    wsl_bridge_host,
)

SCOPE = "ironclad-two-combat-continuation-v1"
SOURCE_ROOT = Path(__file__).resolve().parents[2]
ENGINE_SHA256 = "cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673"
CONTRACT = {
    "scope": SCOPE,
    "game_seed": GAME_SEED,
    "initial_start_sha256": INITIAL_START_SHA256,
    "transit_version": TRANSIT_VERSION,
    "route": [[0, 0], [1, 1]],
    "combats": 2,
    "rewards": "claim_gold_then_leave_others",
    "purpose": "development",
}


class Segment:
    """Monotone state and command acknowledgements reconstructed from observations."""

    def __init__(self, session_id, second_policy="heuristic"):
        require(second_policy in {"heuristic", "end_turn"}, "Unsupported second-combat policy")
        self.session_id, self.second_policy = session_id, second_policy
        self.phase = "prefix"
        self.pending = self.plan = self.terminal = None
        self.sequence = self.actions = self.combat_actions = self.transit_actions = 0
        self.combats = []
        self.carried = None
        self.settle_count = 0

    def _plan(self, role, action, decision=None):
        self.plan = {"role": role, "action": action}
        if decision is not None:
            self.plan["decision"] = decision
        return self.plan

    def _plain_action(self, role, command):
        return self._plan(
            role, {"id": f"{self.session_id}:{self.sequence}:{role}", "command": command}
        )

    def sent(self, plan):
        require(
            self.plan is not None and plan == self.plan and self.pending is None,
            "Action differs from the current state-bound controller decision",
        )
        self.pending, self.plan = self.plan, None
        self.actions += 1
        self.combat_actions += plan["role"] == "combat"
        self.transit_actions += plan["role"] == "transit"

    def _acknowledge(self, raw):
        if self.pending is None:
            return
        plan = self.pending
        if plan["role"] == "transit":
            action, game = plan["action"], raw["game_state"]
            carried = persistent_state(raw)
            expected = dict(self.carried)
            if action["kind"] == "gold":
                expected["gold"] += action["choice"]["gold"]
                next_decision = transit_decision(
                    raw, session_id=self.session_id, sequence=self.sequence
                )
                require(game.get("screen_type") == "COMBAT_REWARD", "GOLD left its reward screen")
                rewards = list(plan["decision"]["observation"]["rewards"])
                del rewards[action["index"]]
                require(
                    next_decision["observation"]["rewards"] == rewards,
                    "GOLD acknowledgement changed or failed to remove the chosen reward",
                )
            elif action["kind"] == "proceed":
                require(
                    game.get("screen_type") == "MAP" and game.get("floor") == 1,
                    "PROCEED did not reach the first-floor map",
                )
                self.phase = "map"
            elif action["kind"] == "map":
                require(
                    game.get("room_phase") == "COMBAT" and game.get("floor") == 2,
                    "MAP choice did not enter the declared second floor",
                )
                self.phase = "entry2"
            require(carried == expected, "HP/gold/deck/relic/potion continuity failed in transit")
            self.carried = carried
        self.pending = None

    def observe(self, raw, sequence, previous_action_id):
        require(self.terminal is None, "Observation after segment terminal")
        require(type(sequence) is int and sequence == self.sequence + 1, "Observation sequence gap")
        require(self.plan is None, "A stable decision was skipped without its recorded action")
        pending_id = self.pending["action"]["id"] if self.pending else None
        require(previous_action_id == pending_id, "Observation/action acknowledgement link differs")
        self.sequence = sequence
        if "error" in raw:
            raise ProtocolError(f"Engine rejected command: {raw['error']}")
        if raw.get("ready_for_command") is not True:
            return None
        self._acknowledge(raw)
        game = raw.get("game_state", {})
        if self.phase == "prefix" and game.get("room_phase") != "COMBAT":
            if not raw.get("in_game") and "start" in raw.get("available_commands", []):
                return self._plain_action("prefix", f"START IRONCLAD 0 {GAME_SEED}")
            require(game.get("screen_type") in {"EVENT", "MAP"}, "Unexpected initial prefix screen")
            if game.get("screen_type") == "MAP":
                require(
                    game.get("screen_state", {}).get("first_node_chosen") is False,
                    "Initial prefix map is not the initial map",
                )
                nodes = game.get("screen_state", {}).get("next_nodes", [])
                require(
                    nodes
                    and all(
                        nodes[0].get(key) == value
                        for key, value in {"x": 0, "y": 0, "symbol": "M"}.items()
                    ),
                    "Initial leftmost node differs from the declared route",
                )
            return self._plain_action("prefix", prefix_command(raw))
        carried = persistent_state(raw)
        if self.phase in {"combat1", "combat2"}:
            combat = self.combats[-1]
            require(
                game.get("floor") == combat["floor"] and carried["gold"] == combat["gold"],
                "Combat changed floor or gold unexpectedly",
            )
            outcome = combat_outcome(raw, combat_floor=combat["floor"])
            if outcome:
                if outcome == "won":
                    require(
                        game.get("screen_type") == "COMBAT_REWARD"
                        and game.get("room_type") == "MonsterRoom",
                        "Combat completion is not the supported reward boundary",
                    )
                else:
                    require(
                        game.get("screen_name") == "DEATH" and carried["current_hp"] == 0,
                        "Loss lacks an actual zero-HP DEATH screen",
                    )
                combat.update(
                    outcome=outcome, ending_hp=carried["current_hp"], terminal_sequence=sequence
                )
                if outcome == "lost" or len(self.combats) == 2:
                    self.terminal = "lost" if outcome == "lost" else "completed_segment"
                    return None
                self.phase, self.carried, self.settle_count = "reward", carried, 0
        if self.phase in {"reward", "map"}:
            require(carried == self.carried, "Uncommanded persistent-state change in transit")
            expected_screen = "COMBAT_REWARD" if self.phase == "reward" else "MAP"
            require(game.get("screen_type") == expected_screen, "Unexpected transit screen")
            decision = transit_decision(raw, session_id=self.session_id, sequence=sequence)
            action = validate_transit_action(decision, choose_transit(decision))
            return self._plan("transit", action, decision)
        validate_combat(raw)
        entering = self.phase in {"prefix", "entry2"}
        floor = (
            1
            if self.phase == "prefix"
            else 2
            if self.phase == "entry2"
            else self.combats[-1]["floor"]
        )
        require(game.get("floor") == floor, "Wrong combat floor")
        if self.phase == "entry2":
            require(carried == self.carried, "Second-combat entry changed carried state")
        monsters = game["combat_state"]["monsters"]
        if entering and any(
            m.get("intent") == "DEBUG" and m.get("current_hp", 0) > 0 for m in monsters
        ):
            require(
                self.settle_count < 3 and "wait" in raw.get("available_commands", []),
                "Combat intent did not settle within three waits",
            )
            self.settle_count += 1
            return self._plain_action("settle", "WAIT 60")
        decision = decision_from_message(raw, session_id=self.session_id, sequence=sequence)
        public = decision.to_dict()["observation"]
        fingerprint = normalized_observation_fingerprint(public)
        if entering:
            if floor == 1:
                require(
                    fingerprint == CONTRACT["initial_start_sha256"], "Initial combat pin differs"
                )
            self.combats.append(
                {
                    "floor": floor,
                    "starting_hp": carried["current_hp"],
                    "gold": carried["gold"],
                    "start_sha256": fingerprint,
                    "start_sequence": sequence,
                    "monsters": [m["id"] for m in monsters],
                }
            )
            self.phase = f"combat{floor}"
        require(
            [m["id"] for m in monsters] == self.combats[-1]["monsters"],
            "Combat monster identity/order changed",
        )
        policy = (
            EndTurnPolicy()
            if floor == 2 and self.second_policy == "end_turn"
            else StarterHeuristicPolicy()
        )
        action = validate_action(decision, policy.choose(decision))
        return self._plan("combat", action.to_dict(), decision.to_dict())

    def summary(self):
        return {
            "actions": self.actions,
            "combat_actions": self.combat_actions,
            "transit_actions": self.transit_actions,
            "combats": self.combats,
            "completed_combats": sum(c.get("outcome") == "won" for c in self.combats),
            "pending_action_id": self.pending["action"]["id"] if self.pending else None,
        }


class SegmentDeadline(TimeoutError):
    pass


@contextmanager
def _deadline(seconds):
    def expire(*_):
        raise SegmentDeadline("Absolute continuation deadline reached")

    require(
        signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
        "An outer alarm already owns this process",
    )
    previous = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, max(seconds, 0.001))
    try:
        yield lambda: signal.setitimer(signal.ITIMER_REAL, 0)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def run_continuation(
    output, *, second_policy="heuristic", time_budget=240, max_actions=500, bridge_timeout=45
):
    """One fresh, bounded attempt. No retry, resume, training or model loading."""
    require(second_policy in {"heuristic", "end_turn"}, "Unsupported second policy")
    require(type(max_actions) is int and 1 <= max_actions <= 500, "Action budget must be 1..500")
    require(
        all(
            type(value) in (int, float) and math.isfinite(value) and value > 0
            for value in (time_budget, bridge_timeout)
        )
        and time_budget <= 240
        and bridge_timeout <= 45,
        "Time budgets exceed the declared bounds",
    )
    source_status = subprocess.check_output(
        [
            "git",
            "status",
            "--porcelain",
            "--",
            "src",
            "scripts",
            "configs",
            "pyproject.toml",
            "uv.lock",
            ".python-version",
        ],
        text=True,
    )
    require(not source_status, "Commit implementation changes before attributable collection")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started, started_unix = time.monotonic(), time.time()
    machine = Segment(uuid.uuid4().hex, second_policy)
    manifest = {
        "schema_version": 1,
        "scope": SCOPE,
        "contract": CONTRACT,
        "contract_sha256": hashlib.sha256(
            json.dumps(CONTRACT, sort_keys=True).encode()
        ).hexdigest(),
        "contract_document_sha256": sha256(SOURCE_ROOT / "docs/continuation.md"),
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_files": source_fingerprints(),
        "session_id": machine.session_id,
        "config": {
            "second_policy": second_policy,
            "time_budget": time_budget,
            "max_actions": max_actions,
            "bridge_timeout": bridge_timeout,
        },
        "started_unix": started_unix,
        "deadline_unix": started_unix + time_budget,
        "status": "running",
    }
    result = {"status": "interrupted"}
    write_json(output / "manifest.json", manifest)
    write_json(output / "result.json", result)
    with (output / "trace.jsonl").open("x", buffering=1) as trace:

        def event(kind, **fields):
            trace.write(
                json.dumps(
                    {"kind": kind, "elapsed": time.monotonic() - started, **fields}, sort_keys=True
                )
                + "\n"
            )
            trace.flush()

        try:
            with _deadline(time_budget - (time.monotonic() - started)) as stop_collection:
                environment = collect_diagnostics()
                write_json(output / "environment.json", environment)
                write_json(output / "profile-before.json", collect_profile(GAME_DIR))
                if environment["game"]["sha256"] != ENGINE_SHA256:
                    raise RuntimeError("Engine pin differs")
                with (
                    RuntimeLock(),
                    BridgeServer(
                        host=wsl_bridge_host(), port=BRIDGE_PORT, timeout=bridge_timeout
                    ) as bridge,
                ):
                    deployment = prepare_runtime(*bridge.address, timeout=bridge_timeout)
                    write_json(output / "deployment.json", deployment)
                    if source_fingerprints() != manifest["source_files"]:
                        raise RuntimeError("Source changed before launch")
                    remaining = time_budget - (time.monotonic() - started)
                    require(remaining > 0, "No remaining launch budget")
                    with OwnedGame(output / "game.log", timeout=remaining) as game:
                        event("launch", **game.info)
                        try:
                            while True:
                                raw = bridge.receive()
                                received_elapsed = time.monotonic() - started
                                if received_elapsed >= time_budget:
                                    raise SegmentDeadline("Observation arrived after deadline")
                                sequence = machine.sequence + 1
                                previous = (
                                    machine.pending["action"]["id"] if machine.pending else None
                                )
                                event(
                                    "observation",
                                    raw=raw,
                                    elapsed=received_elapsed,
                                    sequence=sequence,
                                    previous_action_id=previous,
                                )
                                plan = machine.observe(raw, sequence, previous)
                                if machine.terminal:
                                    result["status"] = machine.terminal
                                    break
                                if raw.get("ready_for_command") is not True:
                                    continue
                                if machine.actions >= max_actions:
                                    result.update(status="truncated", reason="action_limit")
                                    break
                                if plan:
                                    if source_fingerprints() != manifest["source_files"]:
                                        raise RuntimeError("Source changed during collection")
                                    event("action", sequence=sequence, plan=plan)
                                    machine.sent(plan)
                                    bridge.send(plan["action"]["command"])
                        finally:
                            # Collection is over; owned-process cleanup may exceed its deadline.
                            stop_collection()
        except KeyboardInterrupt:
            result.update(status="interrupted", reason="keyboard_interrupt")
        except SegmentDeadline as exc:
            result.update(status="truncated", reason="time_limit", error=str(exc))
        except BridgeError as exc:
            if time.monotonic() - started >= time_budget:
                result.update(status="truncated", reason="time_limit", error=str(exc))
            else:
                result.update(
                    status="infrastructure_failure", error=str(exc), error_type=type(exc).__name__
                )
        except ProtocolError as exc:
            result.update(
                status="unsupported_or_invalid", error=str(exc), error_type=type(exc).__name__
            )
        except Exception as exc:
            result.update(
                status="infrastructure_failure", error=str(exc), error_type=type(exc).__name__
            )
        finally:
            if machine.terminal and result["status"] != machine.terminal:
                # Once verified, an engine endpoint survives a later cleanup failure.
                cleanup_error = dict(result)
                result = {"status": machine.terminal, "cleanup_error": cleanup_error}
            result.update(machine.summary(), elapsed_seconds=time.monotonic() - started)
            event("result", result=result)
            write_json(output / "result.json", result)
            try:
                write_json(output / "profile-after.json", collect_profile(GAME_DIR))
            except Exception as exc:
                write_json(output / "profile-after.json", {"error": str(exc)})
            manifest["status"] = "closed"
            manifest["finished_unix"] = time.time()
            manifest["cleanup_overrun_seconds"] = max(
                0, manifest["finished_unix"] - manifest["deadline_unix"]
            )
            manifest["files"] = {
                path.name: sha256(path)
                for path in sorted(output.iterdir())
                if path.is_file() and path.name != "manifest.json"
            }
            write_json(output / "manifest.json", manifest)
    return {"result": result, "audit": audit_continuation(output)}


def audit_continuation(directory):
    """Replay public decisions and continuity; never launch game/model or read hidden futures."""
    directory = Path(directory)
    checks, errors = [], []
    result = {}
    try:

        def read(name):
            return json.loads((directory / name).read_text())

        manifest, result = read("manifest.json"), read("result.json")
        require(
            manifest["schema_version"] == 1
            and manifest["scope"] == SCOPE
            and manifest["contract"] == CONTRACT
            and manifest["status"] == "closed"
            and manifest["contract_sha256"]
            == hashlib.sha256(json.dumps(CONTRACT, sort_keys=True).encode()).hexdigest()
            and manifest["contract_document_sha256"]
            == sha256(SOURCE_ROOT / "docs/continuation.md"),
            "Unsupported continuation manifest/contract",
        )
        config = manifest["config"]
        require(
            manifest["source_files"] == source_fingerprints()
            and manifest["source_revision"]
            == subprocess.check_output(
                ["git", "-C", str(SOURCE_ROOT), "rev-parse", "HEAD"], text=True
            ).strip(),
            "Audit requires the recorded source checkout; source fingerprints differ",
        )
        require(
            type(config["max_actions"]) is int
            and 1 <= config["max_actions"] <= 500
            and 0 < config["time_budget"] <= 240
            and 0 < config["bridge_timeout"] <= 45,
            "Manifest exceeds the declared collection budgets",
        )
        require(
            manifest["deadline_unix"] == manifest["started_unix"] + config["time_budget"],
            "Original deadline changed",
        )
        for name in ("trace.jsonl", "result.json"):
            require(name in manifest["files"], f"Missing required evidence hash: {name}")
        for name, expected in manifest["files"].items():
            require(
                Path(name).name == name and sha256(directory / name) == expected,
                f"Evidence hash differs: {name}",
            )
        checks.append("contract, deadline and saved file hashes")
        machine = Segment(manifest["session_id"], config["second_policy"])
        launched = finished = False
        expected_error = None
        elapsed = 0
        for line in (directory / "trace.jsonl").read_text().splitlines():
            event = json.loads(line)
            require(
                not finished and math.isfinite(event["elapsed"]) and event["elapsed"] >= elapsed,
                "Trace continues after result or elapsed time decreases",
            )
            elapsed = event["elapsed"]
            kind = event["kind"]
            if kind == "launch":
                require(not launched and machine.sequence == 0, "Duplicate/late launch")
                launched = True
            elif kind == "observation":
                require(
                    launched and expected_error is None and elapsed < config["time_budget"],
                    "Observation outside valid runtime or after collection deadline",
                )
                try:
                    machine.observe(event["raw"], event["sequence"], event["previous_action_id"])
                except ProtocolError as exc:
                    expected_error = exc
            elif kind == "action":
                require(
                    expected_error is None and event["sequence"] == machine.sequence,
                    "Action after invalid observation or at another sequence",
                )
                require(
                    machine.actions < config["max_actions"] and elapsed < config["time_budget"],
                    "Action exceeds frozen budget",
                )
                machine.sent(event["plan"])
            elif kind == "result":
                require(event["result"] == result, "Trace/result file disagree")
                finished = True
            else:
                raise ProtocolError(f"Unknown trace event: {kind}")
        require(finished, "Missing final result event")
        require(
            all(result.get(key) == value for key, value in machine.summary().items()),
            "Result differs from replayed progress/action accounting",
        )
        if expected_error is not None:
            require(
                result["status"] == "unsupported_or_invalid"
                and result.get("error") == str(expected_error),
                "Invalid observation was scored",
            )
        elif machine.terminal:
            require(result["status"] == machine.terminal, "Verified endpoint was mislabeled")
        else:
            require(
                result["status"]
                in {"interrupted", "truncated", "infrastructure_failure", "unsupported_or_invalid"},
                "Missing verified segment endpoint",
            )
        if result["status"] == "truncated":
            require(
                (
                    result.get("reason") == "action_limit"
                    and machine.actions == config["max_actions"]
                )
                or (
                    result.get("reason") == "time_limit"
                    and result["elapsed_seconds"] >= config["time_budget"]
                ),
                "Truncation does not match frozen limits",
            )
        require(
            math.isfinite(result["elapsed_seconds"]) and result["elapsed_seconds"] >= 0,
            "Invalid elapsed measurement",
        )
        require(
            result["elapsed_seconds"] <= elapsed <= result["elapsed_seconds"] + 1,
            "Trace/result elapsed measurement mismatch",
        )
        if launched:
            environment, deployment = read("environment.json"), read("deployment.json")
            require(environment["game"]["sha256"] == ENGINE_SHA256, "Engine provenance differs")
            require(
                deployment["mods"] == {name: pin[1] for name, pin in PINS.items()},
                "Mod deployment pins differ",
            )
            require(
                all(
                    name in manifest["files"]
                    for name in ("environment.json", "deployment.json", "profile-before.json")
                ),
                "Launch provenance was not hashed",
            )
        checks += [
            "state-bound commands and acknowledgements",
            "persistent transit continuity",
            "per-combat identity and single completion",
            "outcome and budget accounting",
        ]
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    return {
        "schema_version": 1,
        "scope": SCOPE,
        "valid": not errors,
        "errors": errors,
        "checks": checks,
        "result": result,
        "claim": "One fixed development segment; not an Act 1 clear or generalization result",
    }
