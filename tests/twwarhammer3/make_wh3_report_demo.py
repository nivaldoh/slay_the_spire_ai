# TODO: what even is this "synthetic field-report demo"? Do we still need it?

"""Invented WH3 jobs for the synthetic field-report demo; no game is run.

Writes job directories for Demo controllers A, B and C (two launches each, 0/6/10 s added
age), with a timer loss, a repeated rematch, a missing metric, a policy failure and a
setup-only interruption, collects them with report.collect and adds one invented replay.
With PAIR.html it also writes a page of invented launches that pair two models of llm_rules,
rendered as recorded jobs so the page reads their prompt file (for the browser check).

    uv run python tests/twwarhammer3/make_wh3_report_demo.py OUTPUT.html [PAIR.html]
"""

import json
import sys
import tempfile
from pathlib import Path

from twwarhammer3.battle import replay, report, report_html
from twwarhammer3.battle.controllers import policy_parts

SCENARIO = {
    "name": "synthetic-citadel-assault", "family": "Demo: citadel assault", "map": "demo-map",
    "battle_type": "siege",
    "brief": "Invented tactical problem and invented measurements for exercising comparison, "
             "latency and objective layouts. No game was run.",
    "attacker": "player", "split": "development", "status": "synthetic",
    "player": {"faction": "Demo attackers", "units": ["demo-lord", "demo-cavalry", "demo-caster"]},
    "enemy": {"faction": "Demo defenders",
              "units": ["demo-lord", "demo-infantry", "demo-infantry", "demo-ranged"]},
    "protected": ["demo-caster"],
    "expect": {"ai_stats_modifier": "1.0", "difficulty": "demo", "time_limit_s": 1200},
}
# Controller: (margin at +0 s, order age at +0 s, USD, supplies left at episode 0).
CONTROLLERS = {"A": (.58, 2.2, .08, 500), "B": (.42, 3.0, .19, 600), "C": (.26, 3.8, .3, 700)}
# (controller, launch): (added seconds, outcome) per episode; time_limit is an engine loss:
# the player attacks, and the attacker loses when the 20:00 timer runs out.
LAUNCHES = {
    ("A", 1): [(0, "won"), (6, "won"), (10, "won")],
    ("A", 2): [(0, "won"), (6, "won"), (10, "won")],
    ("B", 1): [(0, "won"), (6, "won"), (10, "lost")],
    ("B", 2): [(0, "won"), (6, "won"), (10, "lost")],
    ("C", 1): [(0, "won"), (6, "time_limit"), (10, "lost"), (0, "won")],
    ("C", 2): [(0, "won"), (6, "lost"), (10, "policy_failure")],
}
# A valid trial without final strength, a launch with a flagged start, a rejected condition.
MISSING_FINAL, FLAGGED_START, REJECTED = ("C", 2, 0), ("B", 2), ("B", 10)
# Launches on --model gpt-6-sol rotating PAIR, by --effort and each controller's margin, or
# None where it failed to build and left no card (pair-c's own effort keeps it unpooled).
PAIR = ["llm_rules", "llm_rules@gpt-6-luna/medium"]
PAIR_LAUNCHES = {"pair-a": ("low", .3, .1), "pair-b": ("low", .2, .2),
                 "pair-c": ("high", .25, None)}


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value) if path.suffix == ".json"
                    else "".join(json.dumps(row) + "\n" for row in value))


def job(root: Path, name: str, model: str, *, status="completed", wall=1200, error=None) -> Path:
    path = root / name
    path.mkdir(parents=True)
    write(path / "manifest.json", {
        "status": status, "error": error, "wall_seconds": wall, "created_at": "SYNTHETIC",
        "source_revision": "synthetic-no-game-source", "track": "demo-interface/live-1x",
        "scenario": SCENARIO, "setup_checks": {"demo": True},
        "config": {"policy": model, "model": model, "effort": "demo", "observe_ms": 1000,
                   "tick_ms": 250, "interval_ms": 0}})
    write(path / "environment.json", {"game": {"sha256": "synthetic", "steam_build_id": "DEMO"}})
    return path


def result(model: str, launch: int, episode: int, delay: int, outcome: str) -> dict:
    margin, _, usd, supplies = CONTROLLERS[model[-1]]
    margin += .04 * (launch - 1) - .05 * delay
    timer = outcome == "time_limit"
    survived = outcome in {"won", "time_limit"}  # the protected caster
    value = {
        "status": "lost" if timer else outcome, "policy": model,
        "ended_by": "time_limit" if timer else "engine_result",
        "delay_ms": delay * 1000, "battle_ms": 1_200_000 if timer else 300_000,
        "start_time_ms": 0, "battle_s": 1200 if timer else 300,
        "elapsed_seconds": 300, "decisions": 20, "setup_checks": {"demo": True},
        "start_comparison": {"flagged": (model[-1], launch) == FLAGGED_START},
        "card": {"kind": "demo", "name": model, "source_sha256": "synthetic", "timing": "blocking",
                 "description": "Invented controller; no model or engine execution."},
        "llm": {"usd": usd + .01 * (launch - 1), "input_tokens": 1000, "output_tokens": 300},
        "final": {"version": 2, "friendly": {"men0": 100, "men": 95,
                               "active_men": round(100 * (margin + .3)),
                               "units": {"registered": 3, "alive": 2, "destroyed": 1,
                                         "active": 1, "routed": 1, "leaving": 0,
                                         "absent": 0, "unknown": 0},
                               "by_type": {"demo-caster": {"men0": 10,
                                                           "active_men": 10 if survived else 0}}},
                  "enemy": {"men0": 100, "men": 40, "active_men": 30}},
        "objectives": {"method": "engine_tick_time_weighted", "victory_held": .6 - .02 * delay,
                       "points": {"c1": {"key": "demo_gate", "held_ms": 180000,
                                         "observed_ms": 300000}},
                       "key_held": .5 - .02 * delay, "supplies_left": supplies + 50 * episode,
                       "reinforcements_by_type": {"demo-infantry": 4}},
    }
    if outcome == "policy_failure":
        value["error"] = "Synthetic policy failure"
    if (model[-1], launch, delay) == MISSING_FINAL:
        del value["final"]
    return value


def short_trace(model: str, launch: int, delay: int) -> list[dict]:
    age = CONTROLLERS[model[-1]][1] + .3 * (launch - 1) + delay
    ok = (model[-1], delay) != REJECTED
    return [{"kind": "decision", "request": "r0", "seq": 0, "time_ms": 0,
             "decision_time_ms": delay * 1000 + 200, "orders": [{"unit": "f1", "type": "halt"}]},
            {"kind": "ack", "request": "r0", "latency": {"delay_ms": round(age * 1000)},
             "ack": {"results": [{"index": 1, "ok": ok,
                                  "error": None if ok else "synthetic_rejection"}]}}]


def battle_trace() -> list[dict]:
    """Five invented minutes of one demo battle, a decision every 15 s."""
    def unit(uid, x, state, men=20, men0=20):
        return {"id": uid, "type": "demo-infantry", "name": "Demo Infantry", "class": "infantry",
                "men": men, "men0": men0, "x": x, "z": 0, "bearing": 90, "state": state,
                "hp": men / men0, "abilities": [{"key": "demo_ability", "ready": True}],
                "morale": {"fraction": .8, "effect": "Attacked in the rear" if "routing" in state
                           else "Flanks secure"}}

    rows = []
    for second in sorted(set(range(10)) | set(range(0, 301, 15)) | set(range(3, 300, 15))):
        if second == 5:
            continue  # an unrecorded interval
        state = ["idle"] if second < 2 or second >= 6 else ["melee"] if second < 4 else ["routing"]
        observation = {
            "battle": "synthetic", "job": "demo", "seq": second, "time_ms": second * 1000,
            "friendly": [unit("f1", min(second * 4, 30), state)],
            "enemy": [] if second in (3, 4) else [unit("e1", 40, ["idle"], max(42, 100 - second),
                                                       100)],
            "enemy_roster": [{"id": "e1", "type": "demo-infantry"}],
            "magic": {"current": max(0, 10 - second), "reserve": 20},
            "mode": {"type": "synthetic_demo", "role": "attacker", "supplies": 800 - second,
                     "objectives": "Synthetic: hold the demo point.",
                     "capture_points": [{"id": "c1", "x": 30, "z": 30,
                                         "holder": "enemy" if second < 6 else "us"}]},
            "remaining_ms": 365_000 - second * 1000,
            "terrain": {"bounds": {"min_x": -64, "max_x": 64, "min_z": -64, "max_z": 64},
                        "cell_m": 32, "x0": -48, "z0": -48,
                        "rows": ["....", ".#..", "....", "...."]}}
        if second == 0:
            observation["armies"] = {"player": {"faction": "Demo friendly"},
                                     "enemy": {"faction": "Demo enemy"}}
        rows.append({"kind": "observation", "observation": observation})
        if second % 15 == 0 and second < 300:
            order = [{"unit": "f1", "type": "attack", "target": "e1"},
                     {"unit": "f1", "type": "move", "x": 40, "z": 40},
                     {"unit": "f1", "type": "ability", "ability": "demo_ability"}][second // 15 % 3]
            attempt = {"text": '{"synthetic":true}', "usd": .004, "seconds": 1.8,
                       "provider_processing_ms": 1500,
                       "usage": {"input_tokens": 50, "output_tokens": 15}}
            refused = second == 45  # recorded as play.py records a batch validation refuses
            if refused:
                rows.append({"kind": "invalid", "error": "Synthetic validation refusal: unknown "
                                                         "unit f9",
                             "orders": [{"unit": "f9", "type": "halt"}]})
            rows.append({"kind": "decision", "request": f"r{second}", "seq": second,
                         "time_ms": second * 1000, "decision_time_ms": second * 1000 + 200,
                         "orders": [] if refused else [order], "behavior": {
                             "reason": "Synthetic stated rationale.",
                             "notes": f"Synthetic notes {second}.",
                             "prompt": f"Synthetic exact prompt {second}.", "attempts": [attempt]}})
            rejected = second == 15
            rows.append({"kind": "ack", "request": f"r{second}",
                         "latency": {"think_s": 1.8, "roundtrip_s": 2, "delay_ms": 2200},
                         "ack": {"applied_ms": second * 1000 + 2200, "results": [] if refused
                                 else [{"index": 1, "ok": not rejected,
                                        "error": "unreachable" if rejected else None}]}})
    return rows


def demo_report(root: Path) -> dict:
    """Write the invented jobs under root and collect them as one synthetic report."""
    jobs = []
    for (name, launch), trials in LAUNCHES.items():
        model = f"Demo controller {name}"
        jobs.append(job(root, f"demo-{name}-launch-{launch}", model))
        for episode, (delay, outcome) in enumerate(trials):
            directory = jobs[-1] / f"episode-{episode:04d}"
            directory.mkdir()
            write(directory / "result.json", result(model, launch, episode, delay, outcome))
            featured = (name, launch, episode) == ("A", 1, 0)
            write(directory / "trace.jsonl",
                  battle_trace() if featured else short_trace(model, launch, delay))
    jobs.append(job(root, "demo-interrupted-setup", "Demo controller C", status="interrupted",
                    wall=40, error="Synthetic owner interruption"))
    data = report.collect(jobs)
    data["evidence_kind"] = "synthetic"
    for item in [*data["groups"], *data["jobs"]]:
        item["evidence_kind"] = "synthetic"
    payload = replay.build(jobs[0] / "episode-0000")
    payload.update(evidence_kind="synthetic",
                   frame_source="SYNTHETIC DEMO: invented tactical frames, not benchmark evidence")
    data["replays"] = {"g0-t0": payload}
    return data


def pair_jobs(root: Path) -> list[Path]:
    """Write the PAIR_LAUNCHES jobs under root, with the rules-only prompt they snapshot."""
    jobs = []
    for name, (effort, *margins) in PAIR_LAUNCHES.items():
        jobs.append(job(root, name, "gpt-6-sol"))
        manifest = json.loads((jobs[-1] / "manifest.json").read_text())
        manifest["config"].update(policy=",".join(PAIR), effort=effort)
        write(jobs[-1] / "manifest.json", manifest)
        (jobs[-1] / "llm_rules_prompt.md").write_text("Invented rules-only prompt.")
        for index, (policy, margin) in enumerate(zip(PAIR, margins)):
            _, model, level = policy_parts(policy, manifest["config"])
            directory = jobs[-1] / f"episode-{index:04d}"
            directory.mkdir()
            value = {"status": "policy_failure", "policy": policy,
                     "error": "controller construction: invented"}
            if margin is not None:
                value = {"status": "won", "policy": policy, "battle_s": 300,
                         "final": {"friendly": {"men0": 100, "active_men": 50 + margin * 100},
                                   "enemy": {"men0": 100, "active_men": 50}},
                         "card": {"kind": "model", "model": model, "effort": level,
                                  "source_sha256": "synthetic", "timing": "blocking"}}
                write(directory / "trace.jsonl", battle_trace())
            write(directory / "result.json", value)
    return jobs


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp:
        report_html.write(Path(sys.argv[1]), demo_report(Path(temp)))
        if len(sys.argv) > 2:
            report_html.write(Path(sys.argv[2]), report.collect(pair_jobs(Path(temp, "pair"))))
    print(*sys.argv[1:])
