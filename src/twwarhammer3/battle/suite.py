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

from gameai.llm import InvalidReply
from gameai.provenance import REPO_ROOT, write_json
from twwarhammer3.battle.benchmark import EFFORT, MODEL, SUITE, collect
from twwarhammer3.battle.report import mean_interval, trial_metrics, wilson
from twwarhammer3.battle.skills import SHOOTERS

# JUDGEMENT: Suite arms — Claude, 2026-11-04, overnight goal: the methods the code has today,
# frozen, at Haiku low: no orders; run at the nearest enemy; the scripted class skills; a script
# that gathers and hits one enemy together (reference.py Concentrate limits); one model; one model
# per unit class; one model over the skills; graphs a model writes before each scenario, with
# model target hints in battle (GaP's own idea). Another model, effort or split is another arm;
# what the comparison answers rests on these.
# JUDGEMENT: Class team — Claude, 2026-11-04, overnight goal: team.CLASS_PARTITION gives one
# member each to shooters, to fast or monstrous units and to the rest, on every scenario, so one
# frozen team plays them all. A split by unit, by type, by position or by a planner is another arm.
PAID = ["--provider", "anthropic"]
GRAPH_TEMPLATE = Path("configs/twwarhammer3/graphs/suite-gap.json")
ARMS = {
    "hold": ["--policy", "hold"],
    "rush": ["--policy", "rush_nearest"],
    "skills": ["--policy", "skills"],
    "concentrate": ["--policy", "twwarhammer3.battle.reference:Concentrate"],
    "single": ["--policy", f"llm_rules@{MODEL}/{EFFORT}", *PAID],
    "team": ["--policy", f"team_llm_rules@{MODEL}/{EFFORT}", *PAID],  # ClassTeam in a suite
    "commander": ["--policy", f"commander@{MODEL}/{EFFORT}", *PAID],
    "gap": ["--policy", "configured", *PAID],  # plus each scenario's written artifact
}
REFERENCE = "single"
CONTROLS = {"commander": "skills"}  # the same executor with no model: read its wins against this
# JUDGEMENT: Local odds radius — Claude, 2026-11-04: men within 80 m (about two unit widths) of a
# fighting unit count as that fight. A wider radius blends fights and moves the number toward the
# whole-army ratio; a narrower one misses supporting units.
LOCAL_M = 80
GAP_S = 3  # a recorder gap this short does not end a group's stretch
AUTHOR_TRIES = 3


def author_task(scenario):
    """The public task a graph author reads: goal, roles, rosters and our own starting places.

    The enemy's start is private setup, and no tactic is named: what to do is the author's.
    """
    expect = scenario["expect"]
    role = "defender" if expect["player_defends"] else "attacker"
    placed = scenario.get("deployment", {}).get("friendly")
    units = ([f"{place['type']} at x={place['x']}, z={place['z']}" for place in placed]
             if placed else scenario["player"]["units"])
    return (f"Win this {scenario.get('battle_type', 'classic')} battle as the {role}: any engine"
            f" win counts, and the {expect['time_limit_s']} s timer ends it. Within an outcome,"
            " keep your own army and destroy or rout the enemy's. Coordinates are metres: x east,"
            " z north, on a map from -512 to 512. Your units: " + "; ".join(units) + ". The enemy"
            " roster: " + ", ".join(scenario["enemy"]["units"]) + ". Enemy positions are unknown"
            " until seen. Each member's graph must get its units into the fight: a graph that"
            " waits for contact needs another member that starts it. The battle goes on after"
            " one target falls, and a graph that reaches end gives no more orders.")


def author(directory, scenario_names, ledger, *, send=None):
    """Graphs for each scenario, written before any battle; each failed try keeps its folder.

    A scenario gets AUTHOR_TRIES whole tries, so one bad reply costs that scenario a little
    money rather than the night its arm; what every try cost counts as the arm's writing cost.
    """
    from twwarhammer3.battle import graph_author
    from twwarhammer3.battle.setup import scenarios

    known, directory, totals = scenarios(), Path(directory), {}
    for name in scenario_names:
        for attempt in range(1, AUTHOR_TRIES + 1):
            try:
                manifest = graph_author.generate(
                    REPO_ROOT / GRAPH_TEMPLATE, author_task(known[name]),
                    directory / name / f"attempt-{attempt}", ledger, model=MODEL, effort=EFFORT,
                    provider="anthropic", send=send)
            except (InvalidReply, ValueError) as exc:
                totals[name] = {"status": "failed", "tries": attempt, "error": str(exc)}
                continue
            totals[name] = {"status": "ready", "tries": attempt, **manifest["totals"]}
            break
    return totals


def written_graphs(directory, scenario):
    """The scenario's ready artifact: the last try, the one that succeeded."""
    tries = sorted((Path(directory).resolve() / scenario).glob("attempt-*"))
    if not tries or json.loads((tries[-1] / "manifest.json").read_text())["status"] != "ready":
        raise ValueError(f"no ready graphs for {scenario} in {directory}")
    return tries[-1]


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
                args += ["--controller-config", str(written_graphs(graphs, scenario))]
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


def killed(result):
    """Percent of the enemy's men dead at the end. taken reads 100 on every win; this does not."""
    enemy = (result.get("final") or {}).get("enemy") or {}
    men0, men = enemy.get("men0"), enemy.get("men")
    if not men0 or men is None:
        return None
    return round(100 * (1 - men / men0), 1)


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
      fights. Only enemies the recorder can see count. On recorded battles it mostly restates
      who won: its first 60 s do not separate wins from losses (benchmark.md).
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


def groups_of(units, groups):
    """Each unit's group: the declared centre nearest where it started."""
    return {key: min(groups, key=lambda group: math.hypot(group["x"] - unit["x"],
                                                          group["z"] - unit["z"]))["name"]
            for key, unit in units.items() if unit.get("x") is not None}


def lanes(frames, members):
    """What each group was doing, second by second: [from_s, to_s, "ready" or "fight"].

    A group fights while any of its able units is in melee, and is ready while it has able
    units and none is. It ends when it has none: routed, shattered or dead, for now. These
    are recorded states, so a stretch is a reading of what happened, not of what was meant.
    """
    result = {name: [] for name in dict.fromkeys(members.values())}
    for name, spans in result.items():
        for frame in frames:
            units = [unit for unit in frame.get("friendly") or []
                     if members.get(unit.get("id")) == name and able(unit)]
            if not units:
                continue
            state = "fight" if any("melee" in (u.get("state") or []) for u in units) else "ready"
            second = round(frame["time_ms"] / 1000, 1)
            if spans and spans[-1][2] == state and second - spans[-1][1] <= GAP_S:
                spans[-1][1] = second
            else:
                spans.append([second, second, state])
    return result


def clock(seconds):
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def melee_units(frame, members, group, side="friendly"):
    return [unit for unit in frame.get(side) or [] if members.get(unit.get("id")) == group
            and able(unit) and "melee" in (unit.get("state") or []) and unit.get("x") is not None]


def first_melee(frames, members, side):
    """The first battle second, and a unit, each group had in melee."""
    first = {}
    for frame in frames:
        for group in dict.fromkeys(members.values()):
            fighting = melee_units(frame, members, group, side)
            if group not in first and fighting:
                first[group] = (round(frame["time_ms"] / 1000, 1), fighting[0])
    return first


def units_of(frame, members, groups):
    return [unit for unit in frame.get("friendly") or [] if members.get(unit.get("id")) in groups
            and able(unit) and unit.get("x") is not None]


def joined(rule, frames, members):
    """Where the reserve first fought: beside a group only if it stood near that group's units."""
    who, first = rule["who"], first_melee(frames, members, "friendly").get(rule["who"])
    if first is None:
        return f"{who} never fought"
    when, unit = first
    frame = next(item for item in frames if item["time_ms"] / 1000 >= when)
    near = [members[other["id"]] for other in units_of(frame, members, rule["among"])
            if within(unit, other)]
    if not near:
        return f"{who} first fought away from both groups, at {clock(when)}"
    return f"{who} joined the {near[0]} at {clock(when)}"


def reached(rule, frames, members):
    """When one group first fought within LOCAL_M of the other's fight, after that fight began."""
    start = first_melee(frames, members, "friendly").get(rule["a"])
    for frame in frames if start else ():
        help_ = melee_units(frame, members, rule["b"])
        if any(within(a, b) for a in melee_units(frame, members, rule["a"]) for b in help_):
            return rule["text"].format(gap=clock(frame["time_ms"] / 1000 - start[0]))
    return rule["never"]


def answer(rule, frames, members, foes):
    """The battle's own question, answered from the recorded states in one sentence."""
    kind, ours = rule["kind"], first_melee(frames, members, "friendly")
    theirs = first_melee(frames, foes, "enemy")
    if kind == "joined":
        return joined(rule, frames, members)
    if kind == "reached":
        return reached(rule, frames, members)
    if kind == "apart":
        if rule["a"] not in ours or rule["b"] not in ours:
            return rule["never"]
        (at_a, a), (at_b, b) = ours[rule["a"]], ours[rule["b"]]
        metres = round(math.hypot(a["x"] - b["x"], a["z"] - b["z"]), -1)
        return f"Two fights {metres:.0f} m apart, starting {clock(abs(at_a - at_b))} apart"
    if kind == "waves":
        if rule["a"] not in theirs or rule["b"] not in theirs:
            return rule["never"]
        return rule["text"].format(gap=clock(abs(theirs[rule["a"]][0] - theirs[rule["b"]][0])))
    if kind == "spread":
        times = [when for when, _ in theirs.values()]
        groups = len(set(foes.values()))
        if len(times) < groups:
            return f"Reached {len(times)} of {groups} enemy groups"
        broke = first_broken(frames, foes)
        first = f"{broke[0]} broke at {clock(broke[1])}" if broke else "No enemy group broke"
        return f"{first}; all {groups} in contact by {clock(max(times))}"
    who = rule["who"]
    first = f"first in melee at {clock(ours[who][0])}" if who in ours else "never in melee"
    return f"{who} {first}; fired {spent(frames, members, who)}% of their ammunition"


def first_broken(frames, foes):
    """The first enemy group, and second, with every unit in sight routing or shattered."""
    fought = set()
    for frame in frames:
        units = [unit for unit in frame.get("enemy") or [] if unit.get("id") in foes]
        fought |= {foes[unit["id"]] for unit in units if "melee" in (unit.get("state") or [])}
        for group in fought:
            own = [unit for unit in units if foes[unit["id"]] == group]
            if own and not any(able(unit) for unit in own):
                return group, frame["time_ms"] / 1000
    return None


def spent(frames, members, group):
    """Percent of a group's starting ammunition gone by its last reading."""
    last = {}
    start = {}
    for frame in frames:
        for unit in frame.get("friendly") or []:
            if members.get(unit.get("id")) == group and unit.get("ammo") is not None:
                start.setdefault(unit["id"], unit["ammo"])
                last[unit["id"]] = unit["ammo"]
    total = sum(start.values())
    return round(100 * (1 - sum(last.values()) / total)) if total else 0


def battle_story(row, notes):
    """One played battle for the page: its groups and what each did, by the recorder."""
    episode = Path(row["output"]) / "episode-0000"
    path = episode / "result.json"
    if not row["outcome"] or not path.exists():
        return None
    start = json.loads(path.read_text()).get("start") or {}
    members = groups_of(start.get("friendly") or {}, notes["groups"])
    foes = groups_of(start.get("enemy") or {}, notes["enemy"])
    frames = read_frames(episode)
    return {"output": row["output"], "arm": row["arm"], "outcome": row["outcome"],
            "battle_s": row["battle_s"], "taken": row["taken"], "groups": members,
            "lanes": lanes(frames, members),
            "answer": answer(notes["answer"], frames, members, foes)}


def scenario_pictures(rows, notes):
    """The page's picture of each scenario: the declared problem, starts from a played battle."""
    pictures = {}
    for row in rows:
        note = notes.get(row["scenario"]) or {}
        if not note.get("groups"):
            continue
        picture = pictures.setdefault(row["scenario"], {**note, "battles": []})
        story = battle_story(row, note)
        if story is None:
            continue
        picture["battles"].append(story)
        if "start" not in picture:
            path = Path(row["output"]) / "episode-0000/result.json"
            start = json.loads(path.read_text())["start"]
            place = {"friendly": note["groups"], "enemy": note["enemy"]}
            picture["start"] = {side: [
                {"x": start[side][key]["x"], "z": start[side][key]["z"], "group": group}
                for key, group in groups_of(start[side], place[side]).items()]
                for side in place}
    return pictures


def measure(row):
    """One planned battle along every dimension; a battle not played keeps Nones."""
    directory = Path(row["output"])
    path = directory / "episode-0000" / "result.json"
    result = json.loads(path.read_text()) if path.exists() else None
    empty = {"own": None, "taken": None, "killed": None, "battle_s": None, "usd": None,
             "authoring_usd": None, "calls": None, "tokens": None, "think_s": None, "age_s": None,
             "age_p90_s": None, "plan_age_s": None, "orders": None, "refused": None,
             "bad_replies": None, "call_failures": None, "first_contact_s": None,
             "spread_s": None, "idle_share": None, "local_share": None}
    if result is None or not row["evidence_matches_plan"]:
        return empty
    metrics = trial_metrics(path.parent, result)
    llm = result.get("llm") or {}
    trace = metrics["trace"]
    return {"own": row["condition"], "taken": taken(result), "killed": killed(result),
            "battle_s": result.get("battle_s"),
            "usd": llm.get("usd", 0), "authoring_usd": authoring_usd(result),
            "calls": llm.get("calls", 0),
            "tokens": (llm.get("input_tokens") or 0) + (llm.get("output_tokens") or 0),
            "think_s": metrics["call_seconds"]["p50"], "age_s": metrics["order_age_s"]["p50"],
            "age_p90_s": metrics["order_age_s"]["p90"], "plan_age_s": metrics["plan_age_s"]["p50"],
            "orders": trace.get("orders", 0), "refused": sum(metrics["rejections"].values()),
            "bad_replies": metrics["reply_validation"]["failed"],
            "call_failures": metrics["transport_failures"],
            **coordination(read_frames(path.parent))}


def authoring_usd(result):
    """What writing this scenario's graphs cost, failed tries too, apart from playing them."""
    artifact = ((result.get("card") or {}).get("disclosure") or {}).get("artifact")
    if not artifact:
        return 0
    tries = Path(artifact["directory"]).parent.glob("attempt-*/manifest.json")
    return round(sum(json.loads(path.read_text())["totals"].get("usd", 0) for path in tries), 7)


def mean(values):
    kept = [value for value in values if value is not None]
    return round(statistics.mean(kept), 3) if kept else None


def points(value):
    return None if value is None else round(value, 1)


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


# JUDGEMENT: Scenario tie-break — Claude, 2026-11-04, overnight goal: within an outcome arms compare
# on own + taken; the mirror uses own alone. On the first 26 battles own alone turns gap against
# single from 5-1 to 3-3, team from 3-2 to 1-4 and commander from 5-0 to 4-1.
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
    return {"scenarios": len(gaps), "mean": points(interval["mean"]),
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
            "win_text": bound_text(win_bound(wins, len(done))),
            "scenarios_won": len({r["scenario"] for r in done if r["outcome"] == "won"}),
            "scenarios_played": len({r["scenario"] for r in done}),
            "own": points(mean([r["own"] for r in done])),
            "taken": points(mean([r["taken"] for r in done])),
            "killed": points(mean([r["killed"] for r in done])),
            "battle_s": median([r["battle_s"] for r in done]),
            "usd": mean([r["usd"] for r in done]),
            "authoring_usd": mean([r["authoring_usd"] for r in done]),
            "usd_total": round(sum(r["usd"] or 0 for r in mine), 4),
            "usd_per_win": round(sum(r["usd"] or 0 for r in done) / wins, 4) if wins else None,
            "calls": mean([r["calls"] for r in done]),
            "think_s": median([r["think_s"] for r in done]),
            "age_s": median([r["age_s"] for r in done]),
            "age_p90_s": median([r["age_p90_s"] for r in done]),
            "plan_age_s": median([r["plan_age_s"] for r in done]),
            "orders": mean([r["orders"] for r in done]),
            "refused_share": (round(sum(r["refused"] for r in decided)
                                    / sum(r["orders"] for r in decided), 3) if decided else None),
            "bad_replies": sum(r["bad_replies"] or 0 for r in done),
            "call_failures": sum(r["call_failures"] or 0 for r in done),
            "spread_s": median([r["spread_s"] for r in done]),
            "idle_share": mean([r["idle_share"] for r in done]),
            "local_share": mean([r["local_share"] for r in done]),
            **({"paired": {**paired(rows, arm, REFERENCE, scenarios),
                           "taken": taken_difference(rows, arm, REFERENCE, scenarios)}}
               if arm != REFERENCE and REFERENCE in arms else {}),
            **({"control": {**paired(rows, arm, CONTROLS[arm], scenarios),
                            "taken": taken_difference(rows, arm, CONTROLS[arm], scenarios)}}
               if CONTROLS.get(arm) in arms else {})}
    matrix = {scenario: {arm: [{"outcome": r["outcome"] or r["status"],
                                "own": None if r["own"] is None else round(r["own"], 1),
                                "taken": r["taken"]}
                               for r in rows if r["scenario"] == scenario and r["arm"] == arm]
                         for arm in arms} for scenario in scenarios}
    witnessed = {scenario: sorted({r["arm"] for r in rows if r["scenario"] == scenario
                                   and r["outcome"] == "won"}) for scenario in scenarios}
    return {"arms": table, "matrix": matrix, "witnessed_by": witnessed}


def bound_text(bound):
    if bound is None:
        return None
    if "lower" not in bound:
        return f"below {bound['upper']:.0%}"
    return f"{bound['lower']:.0%}-{bound['upper']:.0%}"


COLUMNS = (("won", lambda a: f"{a['wins']}/{a['completed']}"),
           ("win 95%", lambda a: bound_text(a["win_bound"])), ("own", lambda a: a["own"]),
           ("taken", lambda a: a["taken"]), ("killed", lambda a: a["killed"]),
           ("$/battle", lambda a: a["usd"]),
           ("$ author", lambda a: a["authoring_usd"]),
           ("calls", lambda a: a["calls"]), ("think s", lambda a: a["think_s"]),
           ("age s", lambda a: a["age_s"]), ("p90 s", lambda a: a["age_p90_s"]),
           ("plan s", lambda a: a["plan_age_s"]), ("refused", lambda a: a["refused_share"]),
           ("bad replies", lambda a: a["bad_replies"]),
           ("failed calls", lambda a: a["call_failures"]), ("spread s", lambda a: a["spread_s"]),
           ("idle", lambda a: a["idle_share"]), ("local", lambda a: a["local_share"]))


def render(data):
    lines = [f"{SUITE}: {data['completed']}/{data['planned']} planned battles completed."
             " Exploratory: no ranking is claimed from these counts.", "",
             " | ".join(["arm", *[name for name, _ in COLUMNS]])]
    for arm, row in data["summary"]["arms"].items():
        lines.append(" | ".join([arm, *[str(read(row)) for _, read in COLUMNS]]))
    lines.append("")
    for arm, row in data["summary"]["arms"].items():
        for pair in (row.get("paired"), row.get("control")):
            if pair:
                gap = pair["taken"]
                lines.append(f"{arm} against {pair['against']}: better on {pair['better']}"
                             f" scenarios, worse on {pair['worse']}, tied on {pair['tied']};"
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
        rows += [{**row, **measure(row)} for row in data["rows"]]
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
    notes = json.loads(report_html.NOTES_PATH.read_text())
    visual = trials.collect([], benchmark_plans=plans)
    pictures = scenario_pictures(data["rows"], notes["scenarios"])
    page = {**data["summary"], "pictures": pictures, "scenarios": list(pictures),
            "page": {**notes.get("suite", {}), "plans": [Path(plan).stem for plan in plans]}}
    report_html.write(output.with_name(output.name + ".html"), {**visual, "suite": page})
    return data
