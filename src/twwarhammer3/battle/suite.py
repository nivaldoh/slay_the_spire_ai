"""The coordination suite: frozen control methods over many battles, read along dimensions.

A plan fixes every scenario/arm battle before any runs and each gets one row, played or not
(SWE-bench's swebench/harness/reporting.py, as in benchmark.py). No dimension is folded into
another: outcome, what was kept and taken, cost, speed, reliability and coordination stay
apart, so a method can lead on one and trail on another.

Across scenarios the unit of uncertainty is the scenario: each arm is compared with the
reference by how many scenarios it did better or worse on, with an exact sign test (McNemar's
test on the scenarios that differ), and by a paired t interval of what it took. These are the
small-sample methods evaluation-guidelines.md section 7.2 names; it rules out a bootstrap here.
"""

import json
import math
import random
import statistics
import subprocess
from pathlib import Path

from gameai.provenance import REPO_ROOT, write_json
from twwarhammer3.battle.benchmark import EFFORT, MODEL, SUITE, collect
from twwarhammer3.battle.report import mean_interval, trial_metrics, wilson
from twwarhammer3.battle.skills import SHOOTERS

# JUDGEMENT: Suite arms — Claude, 2026-11-04, overnight goal: the methods the code has today,
# frozen, at Haiku low: no orders; run at the nearest enemy; the scripted class skills; one model;
# one model per unit class; one model over the skills; generic graphs per class with model target
# hints; graphs a model writes before each scenario, with the same hints (GaP's own idea).
# Another model, effort or split is another arm; what the comparison answers rests on these.
# JUDGEMENT: Class team — Claude, 2026-11-04, overnight goal: team.CLASS_PARTITION gives one
# member each to shooters, to fast or monstrous units and to the rest, on every scenario, so one
# frozen team plays them all. A split by unit, by type, by position or by a planner is another arm.
PAID = ["--provider", "anthropic"]
GRAPH_TEMPLATE = Path("configs/twwarhammer3/graphs/suite-gap.json")
ARMS = {
    "hold": ["--policy", "hold"],
    "rush": ["--policy", "rush_nearest"],
    "skills": ["--policy", "skills"],
    "single": ["--policy", f"llm_rules@{MODEL}/{EFFORT}", *PAID],
    "team": ["--policy", f"team_llm_rules@{MODEL}/{EFFORT}", *PAID],  # ClassTeam in a suite
    "commander": ["--policy", f"commander@{MODEL}/{EFFORT}", *PAID],
    "graphs": ["--policy", "configured", "--controller-config", str(GRAPH_TEMPLATE), *PAID],
    "gap": ["--policy", "configured", *PAID],  # plus each scenario's authored artifact
}
REFERENCE = "single"
# JUDGEMENT: Local odds radius — Claude, 2026-11-04: men within 80 m (about two unit widths) of a
# fighting unit count as that fight. A wider radius blends fights and moves the number toward the
# whole-army ratio; a narrower one misses supporting units.
LOCAL_M = 80


def author_task(scenario):
    """The public task a graph author reads: goal, roles, rosters and our own starting places.

    The enemy's start is private setup, and no tactic is named: what to do is the author's.
    """
    expect = scenario["expect"]
    role = "defender" if expect["player_defends"] else "attacker"
    own = scenario.get("deployment", {}).get("friendly") or []
    places = {place["id"]: f" at x={place['x']}, z={place['z']}" for place in own}
    units = [f"f{i}: {kind}{places.get(f'f{i}', '')}"
             for i, kind in enumerate(scenario["player"]["units"], 1)]
    return (f"Win this {scenario.get('battle_type', 'classic')} battle as the {role}: any engine"
            f" win counts, and the {expect['time_limit_s']} s timer ends it. Within an outcome,"
            " keep your own army and destroy or rout the enemy's. Coordinates are metres: x east,"
            " z north, on a map from -512 to 512. Your units: " + "; ".join(units) + ". The enemy"
            " roster: " + ", ".join(scenario["enemy"]["units"]) + ". Enemy positions are unknown"
            " until seen. Each member's graph must get its units into the fight: a graph that"
            " waits for contact needs another member that starts it.")


def author(directory, scenario_names, ledger, *, send=None):
    """One graph artifact per scenario, written before any battle; a failure stops the batch."""
    from twwarhammer3.battle import graph_author
    from twwarhammer3.battle.setup import scenarios

    known, directory = scenarios(), Path(directory)
    return {name: graph_author.generate(
        REPO_ROOT / GRAPH_TEMPLATE, author_task(known[name]), directory / name, ledger,
        model=MODEL, effort=EFFORT, provider="anthropic", send=send)["totals"]
        for name in scenario_names}


def make_plan(output, scenario_names, arm_names, repeats, budget_usd, *, seed, start_before=None,
              graphs=None):
    """A frozen plan: each repeat plays every scenario/arm pair once, in its own random order.

    Shuffling pairs, not arms inside a scenario, spreads a scenario's battles over the night
    and keeps one broken scenario from failing twice in a row and stopping the queue."""
    from twwarhammer3.battle.setup import scenarios

    output = Path(output)
    if output.exists():
        raise ValueError(f"plan already exists: {output}")
    if not math.isfinite(budget_usd) or not 0 < budget_usd <= 200:
        raise ValueError("budget must be a positive cumulative ledger cap, at most $200")
    if repeats < 1:
        raise ValueError("a plan needs at least one repeat")
    known = scenarios()
    if "gap" in arm_names and not graphs:
        raise ValueError("the gap arm needs --graphs, a directory of authored scenarios")
    for name in scenario_names:
        if known.get(name, {}).get("benchmark") != SUITE:
            raise ValueError(f"{name} is not a {SUITE} scenario")
    for arm in arm_names:
        if arm not in ARMS:
            raise ValueError(f"unknown arm {arm}")
    rng = random.Random(seed)
    jobs = []
    pairs = [(scenario, arm) for scenario in scenario_names for arm in arm_names]
    for repeat in range(1, repeats + 1):
        for scenario, arm in rng.sample(pairs, len(pairs)):
            directory = output.parent / output.stem / f"{scenario}--{arm}--{repeat}"
            args = ["--scenario", scenario, *ARMS[arm], "--episodes", "1",
                    "--start-timeout", "900", "--episode-timeout", "1320",
                    "--run-timeout", "2280"]
            if arm == "gap":
                args += ["--controller-config", str(Path(graphs).resolve() / scenario)]
            if PAID[0] in args:
                args += ["--budget-usd", str(budget_usd)]
            jobs.append({"output": str(directory.resolve()), "args": args, "arm": arm,
                         "scenario": scenario, "controller": ARMS[arm][1]})
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                                       text=True).strip()
    plan = {"benchmark": SUITE, "source_revision": revision, "stage": "suite",
            "scenarios": {name: known[name] for name in scenario_names}, "seed": seed,
            "purpose": "exploratory comparison of control methods; every battle reported",
            "cumulative_ledger_cap_usd": budget_usd, "keep_going": True, "jobs": jobs}
    if start_before:
        plan["start_before"] = start_before
    write_json(output, plan)
    return plan


def taken(result):
    """Percent of the enemy army dead, routed or gone at the end; None if unread.

    The engine's own totals. It counts what a loss still achieved: the first screen's best
    condition (28.4) belonged to an army that routed having cost the enemy 2% of its men.
    """
    enemy = (result.get("final") or {}).get("enemy") or {}
    men0, active = enemy.get("men0"), enemy.get("active_men")
    if not men0 or active is None:
        return None
    return round(100 * (1 - active / men0), 1)


def read_frames(episode):
    """The 1 Hz recorder's frames, sampled the same way for every controller."""
    path = Path(episode) / "replay.jsonl"
    if not path.exists():
        return []
    frames = []
    for line in path.read_text().splitlines():
        try:
            frame = json.loads(line)
        except ValueError:
            continue
        if isinstance(frame.get("time_ms"), (int, float)):
            frames.append(frame)
    return sorted(frames, key=lambda frame: frame["time_ms"])


def able(unit):
    states = set(unit.get("state") or [])
    return (unit.get("men") or 0) > 0 and not states & {"routing", "shattered"}


def within(unit, other):
    return math.hypot(other["x"] - unit["x"], other["z"] - unit["z"]) <= LOCAL_M


def coordination(frames):
    """How the army came together, from unit states and positions alone. Read as diagnostics.

    - first_contact_s: when any friendly unit first shows melee.
    - spread_s: from then until the median unit that ever fights has joined; large when the
      army arrives piecemeal.
    - idle_share: of able non-shooter unit-seconds after first contact, the share idle and
      not fighting. A shooter firing also reads idle, so shooters are left out.
    - local_share: at each fight, friendly men over all men within LOCAL_M of a friendly unit
      in melee, pooled over the battle. Above 0.5 the army outnumbers the enemy where it
      fights. Only enemies the recorder can see count.
    """
    joined, friendly_men, enemy_men, idle, seconds = {}, 0, 0, 0, 0
    first = None
    for frame in frames:
        units = frame.get("friendly") or []
        fighting = [u for u in units if able(u) and "melee" in (u.get("state") or [])]
        for unit in fighting:
            joined.setdefault(unit["id"], frame["time_ms"])
        if fighting and first is None:
            first = frame["time_ms"]
        if first is None:
            continue
        for unit in units:
            if able(unit) and unit.get("class") not in SHOOTERS:
                seconds += 1
                states = set(unit.get("state") or [])
                idle += "idle" in states and "melee" not in states
        enemies = [u for u in frame.get("enemy") or [] if able(u) and u.get("x") is not None]
        allies = [u for u in units if able(u) and u.get("x") is not None]
        for unit in fighting:
            if unit.get("x") is None:
                continue
            friendly_men += sum(other["men"] for other in allies if within(unit, other))
            enemy_men += sum(other["men"] for other in enemies if within(unit, other))
    if first is None:
        return {"first_contact_s": None, "spread_s": None, "idle_share": None, "local_share": None}
    return {"first_contact_s": round(first / 1000, 1),
            "spread_s": round((statistics.median(joined.values()) - first) / 1000, 1),
            "idle_share": round(idle / seconds, 3) if seconds else None,
            "local_share": (round(friendly_men / (friendly_men + enemy_men), 3)
                            if friendly_men + enemy_men else None)}


def measure(row):
    """One planned battle along every dimension; a battle not played keeps Nones."""
    directory = Path(row["output"])
    path = directory / "episode-0000" / "result.json"
    result = json.loads(path.read_text()) if path.exists() else None
    empty = {"own": None, "taken": None, "battle_s": None, "usd": None, "authoring_usd": None,
             "calls": None, "tokens": None, "age_s": None, "age_p90_s": None, "orders": None,
             "refused": None, "forfeits": None, "first_contact_s": None, "spread_s": None,
             "idle_share": None, "local_share": None}
    if result is None or not row["evidence_matches_plan"]:
        return empty
    metrics = trial_metrics(path.parent, result)
    llm = result.get("llm") or {}
    trace = metrics["trace"]
    return {"own": row["condition"], "taken": taken(result), "battle_s": result.get("battle_s"),
            "usd": llm.get("usd", 0), "authoring_usd": authoring_usd(result),
            "calls": llm.get("calls", 0),
            "tokens": (llm.get("input_tokens") or 0) + (llm.get("output_tokens") or 0),
            "age_s": metrics["order_age_s"]["p50"], "age_p90_s": metrics["order_age_s"]["p90"],
            "orders": trace.get("orders", 0), "refused": sum(metrics["rejections"].values()),
            "forfeits": metrics["reply_validation"]["failed"] + metrics["transport_failures"],
            **coordination(read_frames(path.parent))}


def authoring_usd(result):
    """What writing this battle's graphs cost, kept apart from what playing them cost."""
    artifact = ((result.get("card") or {}).get("disclosure") or {}).get("artifact")
    if not artifact:
        return 0
    manifest = Path(artifact["directory"]) / "manifest.json"
    return json.loads(manifest.read_text())["totals"].get("usd", 0)


def mean(values):
    kept = [value for value in values if value is not None]
    return round(statistics.mean(kept), 3) if kept else None


def median(values):
    kept = [value for value in values if value is not None]
    return round(statistics.median(kept), 3) if kept else None


def win_bound(wins, battles):
    """Wilson 95%, or for no wins the exact one-sided 95% upper bound (guidelines 7.2)."""
    if not battles:
        return None
    if not wins:
        return {"method": "exact one-sided 95%", "upper": round(1 - .05 ** (1 / battles), 3)}
    low, high = wilson(wins, battles)
    return {"method": "Wilson 95%", "lower": round(low, 3), "upper": round(high, 3)}


def sign_test(better, worse):
    """Two-sided exact sign test over scenarios that differ."""
    total = better + worse
    if not total:
        return None
    tail = sum(math.comb(total, k) for k in range(min(better, worse) + 1)) / 2 ** total
    return round(min(1, 2 * tail), 4)


def scenario_value(rows):
    """One arm on one scenario: wins, then own plus taken; None with nothing completed."""
    done = [row for row in rows if row["outcome"]]
    if not done:
        return None
    return (mean([row["outcome"] == "won" for row in done]),
            mean([(row["own"] or 0) + (row["taken"] or 0) for row in done]))


def paired(rows, arm, reference, scenarios):
    """How an arm compares with the reference, scenario by scenario, on completed battles."""
    better = worse = tied = 0
    for scenario in scenarios:
        a = scenario_value([r for r in rows if r["arm"] == arm and r["scenario"] == scenario])
        b = scenario_value([r for r in rows if r["arm"] == reference and r["scenario"] == scenario])
        if a is None or b is None:
            continue
        better += a > b
        worse += a < b
        tied += a == b
    return {"against": reference, "better": better, "worse": worse, "tied": tied,
            "sign_test_p": sign_test(better, worse)}


def taken_difference(rows, arm, reference, scenarios):
    """The arm's mean taken minus the reference's: a t interval over shared scenarios."""
    gaps = []
    for scenario in scenarios:
        a = mean([r["taken"] for r in rows if r["arm"] == arm and r["scenario"] == scenario])
        b = mean([r["taken"] for r in rows if r["arm"] == reference and r["scenario"] == scenario])
        if a is not None and b is not None:
            gaps.append(a - b)
    interval = mean_interval(gaps)
    return {"scenarios": len(gaps), "mean": interval["mean"],
            "t_95": [round(value, 1) for value in interval["ci95"]] if interval["ci95"] else None}


def summarize(rows):
    scenarios = sorted({row["scenario"] for row in rows})
    arms = [arm for arm in ARMS if any(row["arm"] == arm for row in rows)]
    table = {}
    for arm in arms:
        mine = [row for row in rows if row["arm"] == arm]
        done = [row for row in mine if row["outcome"]]
        wins = sum(row["outcome"] == "won" for row in done)
        draws = sum(row["outcome"] == "draw" for row in done)
        decided = [row for row in done if row["orders"]]
        table[arm] = {
            "planned": len(mine), "completed": len(done), "wins": wins, "draws": draws,
            "losses": len(done) - wins - draws, "win_bound": win_bound(wins, len(done)),
            "scenarios_won": len({r["scenario"] for r in done if r["outcome"] == "won"}),
            "scenarios_played": len({r["scenario"] for r in done}),
            "own": mean([r["own"] for r in done]),
            "taken": mean([r["taken"] for r in done]),
            "battle_s": median([r["battle_s"] for r in done]),
            "usd": mean([r["usd"] for r in done]),
            "authoring_usd": mean([r["authoring_usd"] for r in done]),
            "usd_total": round(sum(r["usd"] or 0 for r in mine), 4),
            "usd_per_win": round(sum(r["usd"] or 0 for r in done) / wins, 4) if wins else None,
            "calls": mean([r["calls"] for r in done]),
            "age_s": median([r["age_s"] for r in done]),
            "age_p90_s": median([r["age_p90_s"] for r in done]),
            "orders": mean([r["orders"] for r in done]),
            "refused_share": (round(sum(r["refused"] for r in decided)
                                    / sum(r["orders"] for r in decided), 3) if decided else None),
            "forfeits": sum(r["forfeits"] or 0 for r in done),
            "spread_s": median([r["spread_s"] for r in done]),
            "idle_share": mean([r["idle_share"] for r in done]),
            "local_share": mean([r["local_share"] for r in done]),
            **({"paired": {**paired(rows, arm, REFERENCE, scenarios),
                           "taken": taken_difference(rows, arm, REFERENCE, scenarios)}}
               if arm != REFERENCE and REFERENCE in arms else {})}
    matrix = {scenario: {arm: [{"outcome": r["outcome"] or r["status"], "own": r["own"],
                                "taken": r["taken"]}
                               for r in rows if r["scenario"] == scenario and r["arm"] == arm]
                         for arm in arms} for scenario in scenarios}
    witnessed = {scenario: sorted({r["arm"] for r in rows if r["scenario"] == scenario
                                   and r["outcome"] == "won"}) for scenario in scenarios}
    return {"arms": table, "matrix": matrix, "witnessed_by": witnessed}


COLUMNS = (("won", lambda a: f"{a['wins']}/{a['completed']}"), ("own", lambda a: a["own"]),
           ("taken", lambda a: a["taken"]), ("$/battle", lambda a: a["usd"]),
           ("$ author", lambda a: a["authoring_usd"]),
           ("calls", lambda a: a["calls"]), ("age s", lambda a: a["age_s"]),
           ("p90 s", lambda a: a["age_p90_s"]), ("refused", lambda a: a["refused_share"]),
           ("forfeits", lambda a: a["forfeits"]), ("spread s", lambda a: a["spread_s"]),
           ("idle", lambda a: a["idle_share"]), ("local", lambda a: a["local_share"]))


def render(data):
    lines = [f"{SUITE}: {data['completed']}/{data['planned']} planned battles completed."
             " Exploratory: no ranking is claimed from these counts.", "",
             " | ".join(["arm", *[name for name, _ in COLUMNS]])]
    for arm, row in data["summary"]["arms"].items():
        lines.append(" | ".join([arm, *[str(read(row)) for _, read in COLUMNS]]))
    lines.append("")
    for arm, row in data["summary"]["arms"].items():
        if row.get("paired"):
            pair = row["paired"]
            gap = pair["taken"]
            lines.append(f"{arm} against {pair['against']}: better on {pair['better']} scenarios,"
                         f" worse on {pair['worse']}, tied on {pair['tied']};"
                         f" sign test p={pair['sign_test_p']}; taken {gap['mean']} points,"
                         f" t 95% {gap['t_95']}, {gap['scenarios']} scenarios.")
    lines.append("")
    for scenario, cells in data["summary"]["matrix"].items():
        text = "; ".join(f"{arm} " + ",".join(
            f"{cell['outcome']}({cell['own']}/{cell['taken']})" for cell in cell_rows)
            for arm, cell_rows in cells.items())
        lines.append(f"{scenario}: {text}")
    return "\n".join(lines) + "\n"


def gather(plans):
    rows, planned = [], 0
    for plan in plans:
        data = collect(Path(plan))
        planned += data["planned"]
        for row in data["rows"]:
            rows.append({**row, **measure(row)})
    return {"version": SUITE, "plans": [str(plan) for plan in plans], "planned": planned,
            "completed": sum(bool(row["outcome"]) for row in rows), "rows": rows,
            "summary": summarize(rows)}


def report(plans, output):
    """Text, JSON and the one visual report: its replays, with the suite's tables on top."""
    from twwarhammer3.battle import report as trials
    from twwarhammer3.battle import report_html

    data = gather(plans)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output.with_name(output.name + ".json"), data)
    output.with_name(output.name + ".txt").write_text(render(data))
    visual = trials.collect([], benchmark_plans=plans)
    report_html.write(output.with_name(output.name + ".html"), {**visual, "suite": data["summary"]})
    return data
