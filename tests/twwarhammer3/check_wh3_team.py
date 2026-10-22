# TODO: what is the purpose of this? Is it just for multi-agent testing? If so, it should be in
# a separate multi-agent test suite, not here.

"""Check that a scripted team member can move while its teammate is delayed.

Four game launches, no paid model calls, at most 30 minutes total.

uv run --locked python tests/twwarhammer3/check_wh3_team.py --output runs/twwarhammer3/...

Each launch uses the normal battle setup and ends after checking movement, timing and
cleanup. It does not measure wins or use rematches.
Recount saved evidence without launching or writing: --recount EXISTING_OUTPUT.
To save that recount separately, add --recount-output NEW_CHECKS.json (must not exist).
"""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path

from gameai.provenance import committed_revision, git, sha256, source_fingerprints, write_json
from gameai.windows_game import conflicting_games
from spire.engine import runtime as spire_runtime
from twwarhammer3.battle import play, setup, team
from twwarhammer3.engine.doctor import collect_diagnostics
from twwarhammer3.engine.mailbox import Mailbox
from twwarhammer3.engine.runtime import (
    BRIDGE_DIR,
    OwnedGame,
    RuntimeLock,
    prepare_runtime,
    running_pids,
)

VARIANTS = (team.DelayInfantry, team.DelayCavalry, team.DelayInfantry, team.DelayCavalry)
CONFIG = {"speed": 1, "pause": False, "observe_ms": 1000, "tick_ms": 250,
          "record_replay": True, "stills": False, "interval_ms": 0, "delay_ms": 0,
          "start_timeout": 240, "observation_timeout": 10, "episode_timeout": 90,
          "run_timeout": 360}


def assess(events, samples, slow):
    """Independent live witness: engine movement after ack, before slow completion."""
    ownership = next(e["ownership"] for e in events if e.get("event") == "partition")
    roster = next(s["observation"]["friendly"] for s in samples
                  if len(s["observation"].get("friendly", [])) == 2)
    expected = {name: [u["id"] for u in roster if u["type"] == kind]
                for name, kind in (("infantry", team.SWORD), ("cavalry", team.KNIGHT))}
    assert all(len(ids) == 1 for ids in expected.values())
    assert ownership == {name: ids[0] for name, ids in expected.items()}
    fast = "cavalry" if slow == "infantry" else "infantry"
    completed = next(e for e in events if e.get("event") == "completed"
                     and e["decision"] == f"{slow}-1")
    assert 3 <= completed["completed"] - completed["started"] <= 4.5
    dispatches = [e for e in events if e["kind"] == "decision" and e["orders"]]
    assert {e["behavior"]["decision"] for e in dispatches} == {"infantry-1", "cavalry-1"}
    for dispatch in dispatches:
        member = dispatch["behavior"]["member"]
        assert all(order["unit"] == ownership[member] for order in dispatch["orders"])
        feedback = next(e for e in events if e.get("event") == "feedback"
                        and e["decision"] == dispatch["behavior"]["decision"])
        assert feedback["source"] == "engine" and feedback["ack"]["results"]
        assert feedback["ack"]["request"] == dispatch["request"]
        assert all(row["ok"] for row in feedback["ack"]["results"])
        raw = next(s["observation"]["orders"] for s in samples
                   if (s["observation"].get("orders") or {}).get("request") == dispatch["request"])
        assert raw == feedback["ack"]
        # The member's age from raw evidence: the engine ack and the observation it was given.
        source = next(s["observation"] for s in samples
                      if s["observation"].get("seq") == dispatch["behavior"]["source_seq"])
        assert feedback["latency"]["delay_ms"] == raw["applied_ms"] - source["time_ms"]
        result, = raw["results"]
        assert result["index"] == 1 and result["unit"] == ownership[member] and result["ok"] is True
    dispatch = next(e for e in dispatches if e["behavior"]["decision"] == f"{fast}-1")
    order, = dispatch["orders"]
    feedback = next(e for e in events if e.get("event") == "feedback"
                    and e["decision"] == f"{fast}-1")
    assert not any(e.get("event") == "feedback" and e["source"] != "engine" for e in events)
    assert all(sample["observation"].get("speed", 1) == 1
               and not sample["observation"].get("awaiting_orders") for sample in samples)
    acknowledged = next(i for i, sample in enumerate(samples)
                        if (sample["observation"].get("orders") or {}).get("request")
                        == dispatch["request"])

    def unit(sample):
        return next(u for u in sample["observation"]["friendly"] if u["id"] == order["unit"])

    def distance(row):
        return math.hypot(row["x"] - order["x"], row["z"] - order["z"])

    baseline = samples[acknowledged]
    initial_distance = distance(unit(baseline))
    # JUDGEMENT: Movement witness — assistant, 2026-10-21: existing motion can qualify.
    # Requiring idle samples before acknowledgement would change the live pass rule;
    # agreement is pending in multi-agent-implementation.md. Keep that rule unchanged here.
    witnesses = [sample for sample in samples[acknowledged + 1:]
                 if completed["started"] <= sample["received"] < completed["completed"]
                 and {"moving", "running"} & set(unit(sample).get("state", []))
                 and initial_distance - distance(unit(sample)) >= .25]
    deployed = [s for s in samples if s["observation"].get("phase") == "Deployed"]
    wall_s = deployed[-1]["received"] - deployed[0]["received"]
    battle_s = (deployed[-1]["observation"]["time_ms"]
                - deployed[0]["observation"]["time_ms"]) / 1000
    clock_ratio = battle_s / wall_s if wall_s else 0
    clock_ok = wall_s >= 10 and .85 <= clock_ratio <= 1.15
    return {"passed": bool(witnesses) and clock_ok, "fast": fast, "unit": order["unit"],
            "request": dispatch["request"], "order": order,
            "ack_ms": feedback["ack"]["applied_ms"],
            "member_age_ms": feedback["latency"]["delay_ms"],
            "baseline": baseline, "slow_completed": completed["completed"],
            "clock_ratio": clock_ratio, "clock_window_s": wall_s,
            "witness": witnesses[0] if witnesses else None,
            "reason": "clock progress inconsistent with 1x" if not clock_ok else
                      "moving toward waypoint before peer completed" if witnesses
                      else "no qualifying movement observed; capability unverified"}


def recount(output, *, destination=None):
    """Assess saved inputs; only an explicit, new destination receives a verdict.

    Hash the bytes actually parsed, so a later recount identifies its evidence and checker
    independently of the original launch's plan and verdict.
    """
    checker = {"revision": git("rev-parse", "HEAD").strip(),
               "path": str(Path(__file__).resolve()), "sha256": sha256(Path(__file__)),
               "dependencies": {str(Path(team.__file__).resolve()): sha256(Path(team.__file__))}}
    evidence = {}

    def read(relative):
        evidence[relative] = None  # A missing file is evidence of a failed check too.
        payload = (output / relative).read_bytes()
        evidence[relative] = hashlib.sha256(payload).hexdigest()
        return payload

    try:
        read("plan.json")  # Preserve identity of the launch settings; old runs may lack it.
    except OSError:
        pass
    results = []
    for index, variant in enumerate(VARIANTS):
        prefix = f"probe-{index + 1}"
        slow = "infantry" if variant is team.DelayInfantry else "cavalry"
        try:
            events = [json.loads(line)
                      for line in read(f"{prefix}/episode/trace.jsonl").splitlines()]
            samples = [json.loads(line)
                       for line in read(f"{prefix}/observations.jsonl").splitlines()]
            result = assess(events, samples, slow)
            manifest = json.loads(read(f"{prefix}/manifest.json"))
            assert manifest["closed"] and not manifest["remaining_pids"]
            assert manifest["result"]["status"] in ("truncated", "won", "lost", "draw")
        except (OSError, KeyError, AssertionError, StopIteration, ValueError) as exc:
            result = {"passed": False,
                      "reason": f"missing or failed evidence: {type(exc).__name__} {exc}"}
        results.append({"probe": index + 1, "delayed": slow, **result})
    if destination is not None:
        report = {"passed": all(r["passed"] for r in results), "probes": results,
                  "checker": checker, "evidence": {"directory": str(output.resolve()),
                                                      "files": evidence}}
        with destination.open("x") as stream:
            stream.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return results


def run(output):
    revision = committed_revision("team live verification", play.SOURCES)
    fingerprints = source_fingerprints(play.SOURCES)
    output.mkdir(parents=True)
    environment = collect_diagnostics()
    write_json(output / "environment.json", environment)
    if environment["blockers"]:
        raise RuntimeError(environment["blockers"])
    for warning in environment["warnings"]:
        print("WARNING: " + warning, flush=True)
    spec = setup.scenarios()["emp-knights-emp-swordsmen"]
    steps = setup.scenario_steps(spec, build_id=environment["game"]["steam_build_id"])
    plan = {"revision": revision, "source_files": fingerprints, "scenario": spec,
            "check_sha256": sha256(Path(__file__)), "input_version": team.INPUT_VERSION,
            "variants": [v.__name__ for v in VARIANTS], "config": CONFIG,
            "total_cap_s": 1800, "model_spend_usd": 0,
            "movement": "after ack: >=0.25m closer AND moving/running before slow completion"}
    write_json(output / "plan.json", plan)
    deadline = time.monotonic() + 1800
    for index, variant in enumerate(VARIANTS):
        if time.monotonic() + CONFIG["run_timeout"] + 30 > deadline:
            break
        if source_fingerprints(play.SOURCES) != fingerprints:
            raise RuntimeError("sources changed during verification")
        if conflicting_games(Path(spire_runtime.WINDOWS_GAME_DIR), spire_runtime.CONFLICTS):
            raise RuntimeError("Slay the Spire is running; no concurrent game controllers")
        directory = output / f"probe-{index + 1}"
        directory.mkdir()
        manifest = {"variant": variant.__name__, "source_revision": revision, "closed": False}
        write_json(directory / "manifest.json", manifest)
        print(f"probe {index + 1}/4: {variant.__name__}", flush=True)
        with (RuntimeLock(), (directory / "observations.jsonl").open("x", buffering=1) as samples):
            class RecordingMailbox(Mailbox):
                def wait_observation(self, **kwargs):
                    observation = super().wait_observation(**kwargs)
                    samples.write(json.dumps({"received": time.time(),  # the team's clock
                                              "observation": observation}) + "\n")
                    return observation

            manifest["deployment"] = prepare_runtime()
            mailbox = RecordingMailbox(BRIDGE_DIR, job=f"{output.name}-{index + 1}")
            mailbox.reset()
            if time.monotonic() + CONFIG["run_timeout"] + 30 > deadline:
                break
            try:
                with (mailbox.owned_session(play.session(CONFIG)),
                      OwnedGame(directory / "game.log", timeout=CONFIG["run_timeout"]) as game):
                    manifest["game"] = game.info
                    play.start_frontend(mailbox, CONFIG, directory, steps)
                    manifest["setup_checks"] = setup.check_menu(spec, directory)
                    config = {**CONFIG, "start_timeout": CONFIG["episode_timeout"],
                              "policy": f"twwarhammer3.battle.team:{variant.__name__}"}
                    manifest["result"] = play.play_episode(
                        directory / "episode", config, variant, mailbox,
                        not_battle=None, scenario=spec)
            finally:
                manifest["remaining_pids"] = running_pids()
                manifest["closed"] = True
                write_json(directory / "manifest.json", manifest)
        print(f"probe {index + 1}: {manifest['result']['status']}", flush=True)
    return recount(output, destination=output / "checks.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--recount", type=Path)
    parser.add_argument("--recount-output", type=Path,
                        help="save a recount to this new file; never replace the original verdict")
    args = parser.parse_args()
    if args.recount_output and not args.recount:
        parser.error("--recount-output requires --recount")
    results = (recount(args.recount, destination=args.recount_output)
               if args.recount else run(args.output))
    print(json.dumps([{k: row[k] for k in ("probe", "delayed", "passed", "reason")}
                      for row in results], indent=2))
    raise SystemExit(0 if all(row["passed"] for row in results) else 1)
