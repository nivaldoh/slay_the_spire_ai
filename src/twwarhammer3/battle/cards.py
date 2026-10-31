"""Tactic cards: a declared battle, its controls, a frozen signature, its board and verdict.

A card ([tactic-cards.md](../../../docs/twwarhammer3/tactic-cards.md)) is a minimal battle
that only one tactic should win. Its foils (naive plays) must lose and its witness (a
disclosed scripted bot) must win. Both are declared here with the admission rule before
a confirmation round, so the board and the verdict come from the job evidence alone.
The launch is the sampling unit: one episode per controller and added age counts in each
launch, and a rematch of the same controller at the same added age in that launch (the same
instance again) is skipped. A cell mixing setups (scenario, game build, pack, mod cadence)
or controller sources (policy file, prompt, routing pin, the model strings the provider
reported serving) is starred, so a drift in any of them never pools silently.
"""

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from twwarhammer3.battle.controllers import policy_parts
from twwarhammer3.battle.report import wilson
from twwarhammer3.battle.stats import JOBS_ROOT

WITNESS = "twwarhammer3.battle.calibration:SnapHitAndRun"
CARDS = {
    "chariot": {
        "scenario": "grn-chariot-emp-swordsmen-hard",
        "tactic": "cycle charging: charge, pull out, charge again instead of grinding",
        # hold is no foil here: the AI defends, so standing still loses on the timer by the
        # mode's rule (1205 s, bench-b32-chariothard-floor-hold-20261018).
        # JUDGEMENT: Foils — assistant, 2026-10-18 (b33): the two naive floors, both grinding in
        # melee; no foil rides straight through. The owner kept c1's record; another foil set
        # changes whether a new round's win shows the tactic.
        "foils": ("attack_nearest", "rush_nearest"),
        # (controller, added age ms, decision interval ms) -> wins required in the round.
        # The gate witness decides at tick rate on 5 s-old information. A model-pace gate
        # (5 s age, one decision per 5 s) was dropped on 2026-10-18 17:45 UTC, during E2;
        # the witness by age and interval is the card's tolerance table (tactic-cards.md).
        # JUDGEMENT: gate sizes (foils 0 of 10 at 0 s; witness 4 of its first 5 at 5 s, 1 cycle
        # each) are the assistant's (b33/b34, 2026-10-18), not the owner's: decision 3 proposes
        # 0/14 and 10/14 at 2 s/2 s. c1's "admitted" and the foils' bound 0.26 rest on them.
        "witnesses": {(WITNESS, 5000, 0): 4},
        "foil_launches": 10,  # a foil that wins 20% of battles passes 10 of 10 losses 11%
        "witness_launches": 5,  # 4 of 5 passes a 0.5 witness 19% and fails a 0.8 one 26%
        "cycles": 1,  # each witness win shows at least this many cycles
        # JUDGEMENT?: Pre-registration label — assistant, 2026-10-19 (e2777f4): the verdict names
        # 5396182, though forfeit scoring (b35) and the printed rule text (e2777f4, 1b56ed5) came
        # later; naming the latest rule revision instead drops c1's "pre-registered" claim.
        "rule_revision": "5396182",  # the commit that pre-registered the rule
    },
}
# JUDGEMENT: Cycle signature — assistant, 2026-10-18: v1 merges sub-3 s gaps and counts
# acknowledged moves through end+1 s. Requiring separation changes admission and tactic
# attribution; the owner preserved c1, but new uses of this signature remain a choice.
MERGE_S = 3  # melee-flag gaps shorter than this are one engagement (1 Hz frames flicker)


def records(path: Path):
    """The JSON records of a trace or replay file, one per line."""
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def served(episode_dir: Path) -> tuple:
    """The dated model strings OpenRouter reported serving the episode's calls; empty for
    scripted controllers and for OpenAI, which returns only the model's alias."""
    trace = episode_dir / "trace.jsonl"
    if not trace.exists():
        return ()
    names = {attempt.get("backend_model")
             for record in records(trace) if record.get("kind") == "model_exchange"
             for attempt in record.get("attempts") or []}
    return tuple(sorted(name for name in names if name))


# Which failures forfeit rests on JUDGEMENT src/twwarhammer3/battle/play.py Operator errors and
# Forfeit split; a truncation's forfeit on JUDGEMENT src/twwarhammer3/battle/play.py Wall cap.
def outcome(episode: dict) -> str:
    """won, lost, forfeit (a loss) or excluded (rerun). The battle never waits: a controller
    failure or a truncation during a battle forfeits. Game and setup failures, interrupts and
    operator stops (budget_exhausted; an HTTP 402 policy_failure before b35) are excluded."""
    # REVIEW(owner): adopt the agreed next-evaluator phase rule separately from c1:
    # score constructor failure as unsuccessful and preserve observed engine endings.
    status = episode.get("status")
    if status == "won" and episode.get("ended_by") != "time_limit":
        return "won"
    if status in ("won", "lost", "draw"):
        return "lost"
    if (status in ("policy_failure", "truncated") and episode.get("battle")
            and "APIError: HTTP 402" not in str(episode.get("error"))):
        return "forfeit"
    return "excluded"


# The new benchmark's reading of an episode, beside the card rule above, which keeps every
# historical number. Nothing scores with it yet; a changed rule gets a new version. Shaped
# like SWE-bench's run report (swebench/harness/reporting.py, make_run_report): one label per
# episode from its evidence, with errors and missing runs kept apart from losses.
BENCHMARK_OUTCOME_VERSION = 1


# Which failures end a battle rests on JUDGEMENT src/twwarhammer3/battle/play.py Operator errors
# and Forfeit split; a truncation on JUDGEMENT src/twwarhammer3/battle/play.py Wall cap.
# JUDGEMENT: Benchmark-outcome rows — Claude, 2026-10-31: statuses map to benchmark.md's outcome
# rows of that date; provider, budget, wall-cap and unknown-cause stops stay unresolved. Another
# mapping moves episodes into or out of the denominator of any reader adopting version 1.
def benchmark_outcome(result: dict | None) -> str:
    """won, lost or draw as the engine ended it (timer endings included; a later error or stop
    keeps it); forfeit (the controller's own code failed for good in the battle); not_built;
    operator_stop or setup_or_game_failure (shown separately); never_started (no result, or no
    battle began); or unresolved (provider, key, credit, budget and wall-cap stops, a silent or
    restarted game, an exception in our own code: rules still to settle)."""
    if result is None or result.get("status") in (None, "missing_result"):
        return "never_started"
    status, error = result["status"], str(result.get("error"))
    ending = (result.get("engine_ending") or {}).get("result")
    if ending in ("won", "lost", "draw"):
        return ending
    if status in ("won", "lost", "draw"):
        return status
    if status == "interrupted":
        return "operator_stop"
    # A protocol refusal names its cause (a failed setup check, a paused or slowed battle, a
    # failed custom ending); so does a team's partition or dispatcher fault (TeamHarnessError).
    if status == "unsupported_or_invalid":
        return "setup_or_game_failure"
    if status == "policy_failure" and error.startswith("controller construction:"):
        return "not_built"
    if not result.get("battle"):
        return "never_started"
    # A provider error (an APIError; HTTP 401 and 402 were policy failures before b35) and a
    # wall cap, even one a failed cleanup followed, are still to settle.
    if (status == "policy_failure" and "APIError" not in error
            and result.get("reason") != "episode_timeout"):
        return "forfeit"
    return "unresolved"


def engagements(frames: list[dict], unit_id: str) -> list[list[float]]:
    """[start, end] battle seconds of each engagement: runs of the unit's melee flag, with
    gaps under MERGE_S merged."""
    spans = []
    for frame in frames:
        unit = next((u for u in frame.get("friendly", []) if u.get("id") == unit_id), None)
        if unit is None or "melee" not in unit.get("state", []):
            continue
        now = frame.get("time_ms", 0) / 1000
        if spans and now - spans[-1][1] < MERGE_S:
            spans[-1][1] = now
        else:
            spans.append([now, now])
    return spans


def cycles(episode_dir: Path) -> int | None:
    """Engagements, other than the unit's last, with an accepted move order of that unit
    applied from the first melee frame to 1 s after the last.

    It counts pull-out attempts, not achieved separation or a proven new charge: an
    attack-only play scores 0 even when the engine carries its unit out of melee and it
    charges again.
    """
    replay, trace = episode_dir / "replay.jsonl", episode_dir / "trace.jsonl"
    if not replay.exists() or not trace.exists():
        return None
    frames = list(records(replay))
    moves, applied = {}, []
    for record in records(trace):
        if record.get("kind") == "decision":
            moves[record.get("request")] = record.get("orders") or []
        elif record.get("kind") == "ack":
            ack = record.get("ack") or {}
            orders = moves.pop(record.get("request"), [])
            for result in ack.get("results", []):
                index = result.get("index", 0) - 1
                if result.get("ok") and 0 <= index < len(orders) \
                        and orders[index].get("type") == "move":
                    applied.append((orders[index]["unit"], ack.get("applied_ms", 0) / 1000))
    units = {unit["id"] for unit in (frames[0].get("friendly", []) if frames else [])}
    return sum(1 for unit in units for start, end in engagements(frames, unit)[:-1]
               if any(who == unit and start <= when <= end + 1 for who, when in applied))


def jobs(paths: list[Path]) -> list[Path]:
    """Job directories, with a directory of queue plans expanded to the plans' outputs."""
    found = []
    for path in paths:
        plans = sorted(p for p in path.glob("*.json") if not p.name.endswith("-state.json"))
        if (path / "manifest.json").exists() or not plans:
            found.append(path)
            continue
        for plan in plans:
            found += [Path(job["output"]) for job in json.loads(plan.read_text()).get("jobs", [])]
    return list(dict.fromkeys(found))  # a replacement plan can name the same output


def battles(card: dict, directories: list[Path], teams: list | None = None
            ) -> tuple[list[dict], int]:
    """One row per launch, controller and added age, and how many rematch rows of a
    controller at an added age already counted in its launch were skipped. Team episodes
    are left out; ``teams``, when given, collects their job/episode names."""
    rows, seen, skipped = [], set(), 0
    seen_jobs = set()
    for job in directories:
        job = job.resolve()
        if job in seen_jobs:
            continue
        seen_jobs.add(job)
        try:
            manifest = json.loads((job / "manifest.json").read_text())
        except (OSError, ValueError):
            continue
        if (manifest.get("scenario") or {}).get("name") != card["scenario"]:
            continue
        config, deployment = manifest["config"], manifest.get("deployment") or {}
        # JUDGEMENT?: Cell identity — assistant, 2026-10-18 (b33) and later: a cell mixing these
        # fields, build, pack or cadence is starred and fails admission; the harness revision and
        # `scoring` are not among them. Adding the revision stars c1 (b34-b36): not admitted.
        setup = json.dumps([manifest["scenario"].get(key) for key in (
            "map", "player", "enemy", "expect", "attacker", "battle_type")], sort_keys=True)
        for episode in manifest.get("episodes", []):
            control = episode.get("card") or {}
            # JUDGEMENT: Team rows — Claude, 2026-10-31 (multi-agent-implementation.md Next 1): a
            # team episode is left off the board. Taking it pools both members' decisions into
            # one information age and the team's source under one hash; any team row rests on it.
            if "members" in (control.get("disclosure") or {}):
                if teams is not None:
                    teams.append(f"{job.name}/{episode.get('episode')}")
                continue
            name = episode.get("policy") or control.get("name") or ""
            age_ms = episode.get("delay_ms") or 0
            # JUDGEMENT?: Sampling unit — assistant, 2026-10-18 (b33; the rematch skip 1b56ed5,
            # 10-19): one row per launch, controller and age. Counting episodes changes n
            # wherever a rematch repeats a controller (no such row among today's 103).
            if (job, name, age_ms) in seen:
                skipped += 1
                continue
            seen.add((job, name, age_ms))
            base, model, effort = policy_parts(name, config)
            # A model plays a prompt version (its tuning surface): another version is
            # another row, not a starred pool.
            label = f"{base} {control['version']}" if model and control.get("version") else base
            delays = sorted(episode.get("delays_ms") or [])
            age_p50 = statistics.median(delays) / 1000 if delays else None
            battle_s, decisions = episode.get("battle_s"), episode.get("decisions")
            directory = job / str(episode.get("episode"))
            rows.append({
                "job": job.name, "instance": str(job), "outcome": outcome(episode),
                "started": episode.get("started_at") or "",
                "controller": f"{label}@{model}/{effort}" if model else name,
                "age_ms": age_ms, "interval_ms": config.get("interval_ms") or 0,
                "setup": (setup, deployment.get("steam_build_id"),
                          (deployment.get("pack") or {}).get("sha256"),
                          config.get("observe_ms"), config.get("tick_ms")),
                # A model's prompt is its tuning surface, so another prompt is another source;
                # so are another routing pin and another served model version.
                "source": (control.get("source_sha256") or control.get("version"),
                           manifest.get(f"{base}_prompt_sha256"),
                           json.dumps((config.get("model_routing") or {}).get(model) or None,
                                      sort_keys=True), served(directory)),
                "battle_s": battle_s,
                "age_p50_s": age_p50,
                "age_p90_s": delays[-(-9 * len(delays) // 10) - 1] / 1000 if delays else None,
                # A timing proxy, not an exact time average: median issue age plus half
                # the mean decision gap does not account for unequal gaps or missed orders.
                "info_age_s": (age_p50 + battle_s / decisions / 2
                               if age_p50 is not None and battle_s and decisions else None),
                "cycles": cycles(directory),
            })
    return rows, skipped


def _median(rows: list[dict], field: str):
    values = [row[field] for row in rows if row[field] is not None]
    return statistics.median(values) if values else None


def board(name: str, paths: list[Path] | None = None) -> str:
    """The card's table over the given jobs (default: every job of its scenario) and, for
    given directories that include a control cell, the admission verdict under the declared
    rule. After the foils, cells sort by their information age, so a model row lands on the
    witness's tolerance curve."""
    card = CARDS[name]
    default = paths is None
    directories = sorted(JOBS_ROOT.iterdir()) if default else jobs(paths)
    unrun = [] if default else [d.name for d in directories if not (d / "manifest.json").exists()]
    teams = []
    rows, skipped = battles(card, [d for d in directories if d.is_dir()], teams)
    cells = defaultdict(list)
    for row in rows:
        cells[(row["controller"], row["age_ms"], row["interval_ms"])].append(row)
    launches = len({row["instance"] for row in rows})
    lines = [f"Card {name}: {card['scenario']} ({card['tactic']})",
             f"{len(rows)} controller/age rows from {launches} "
             f"launch{'es' if launches != 1 else ''}"
             + (f" ({skipped} rematch rows of an already counted controller skipped)"
                if skipped else "")
             + (f"; {len(teams)} team episodes left off (not on the board yet)" if teams else "")
             + "; a cell mixing setups or controller sources is marked *; added age and"
             " interval round up to the observation cadence; issue ages are measured",
             f"{'controller':36} age pace   n won forf excl  win [95%]        cycles  "
             "no-cycle wins  battle s  age p50/p90 s  info proxy s"]

    def order(key):
        age = _median([r for r in cells[key] if r["outcome"] != "excluded"], "info_age_s")
        return (key[0] not in card["foils"], age if age is not None else math.inf, str(key))

    for key in sorted(cells, key=order):
        group = cells[key]
        scored = [row for row in group if row["outcome"] != "excluded"]
        won = sum(row["outcome"] == "won" for row in scored)
        forfeits = sum(row["outcome"] == "forfeit" for row in scored)
        ci = wilson(won, len(scored))
        mixed = "*" if mixes(scored) else ""
        label = key[0].removeprefix("twwarhammer3.battle.calibration:") + mixed

        def median(field, digits=0):
            value = _median(scored, field)
            return f"{value:.{digits}f}" if value is not None else "-"

        interval = f"[{ci[0]:.2f}, {ci[1]:.2f}]" if ci else "-"
        win = f"{won / len(scored):.2f} {interval}" if scored else "-"
        bare = sum(row["outcome"] == "won" and row["cycles"] == 0 for row in scored)
        lines.append(f"{label:36} {key[1] / 1000:3g} {key[2] / 1000:4g} {len(scored):3} {won:3} "
                     f"{forfeits:4} {len(group) - len(scored):4}  {win:18} {median('cycles'):>5}"
                     f"  {bare:13}  {median('battle_s'):>8}  {median('age_p50_s', 1):>6}"
                     f"/{median('age_p90_s', 1):<5}  {median('info_age_s', 1):>10}")
    lines.append("cycles (median): acknowledged move attempts during an engagement (through"
                 " 1 s after its last frame), followed by another engagement; this does not"
                 " establish separation or a new charge. info proxy: median issue age plus"
                 " half the mean decision gap, not a measured reaction window or exact time"
                 " average")
    if unrun:
        lines.append("planned, not run: " + ", ".join(unrun))
    controls = [(foil, 0, 0) for foil in card["foils"]] + list(card["witnesses"])
    if not default and any(key in cells for key in controls):
        lines += verdict(card, cells)
    return "\n".join(lines)


def mixes(rows: list[dict]) -> bool:
    """Whether scored rows of one cell differ in setup or controller source (an excluded
    launch that never reached a model call has no served strings and says nothing)."""
    scored = [r for r in rows if r["outcome"] != "excluded"]
    return len({r["setup"] for r in scored}) > 1 or len({r["source"] for r in scored}) > 1


def verdict(card: dict, cells: dict) -> list[str]:
    """A foil win anywhere is a leak; the witness is judged on the first launches of its
    cell, in the order they started, so the rule never loosens as launches accumulate."""
    need, problems = card["foil_launches"], []
    for foil in card["foils"]:
        # A foil's forfeit shows nothing about how it plays, so it is no launch.
        # JUDGEMENT?: Foil forfeits — assistant, 2026-10-18 (ca84106; b35 makes every forfeit a
        # loss, foils excepted only in tactic-cards.md). As a loss, a crashing foil would fill its
        # launches without playing; 0 of 23 recorded foil rows forfeited.
        scored = [r for r in cells.get((foil, 0, 0), []) if r["outcome"] in ("won", "lost")]
        wins = sum(r["outcome"] == "won" for r in scored)
        if wins:
            problems.append(f"{foil} won {wins} of {len(scored)}")
        elif len(scored) < need:
            problems.append(f"{foil} has {len(scored)} of {need} launches")
    need = card["witness_launches"]
    for key, required in card["witnesses"].items():
        scored = sorted((r for r in cells.get(key, []) if r["outcome"] != "excluded"),
                        key=lambda r: r["started"])[:need]
        wins = [r for r in scored if r["outcome"] == "won"]
        label = f"witness at {key[1] / 1000:g} s age, {key[2] / 1000:g} s interval"
        if len(scored) < need:
            problems.append(f"{label} has {len(scored)} of {need} launches")
        elif len(wins) < required:
            problems.append(f"{label} won {len(wins)} of {len(scored)}, needs {required}")
        if any(r["cycles"] is None for r in wins):
            problems.append(f"{label}: a win has no replay to show its cycles")
        elif any(r["cycles"] < card["cycles"] for r in wins):
            problems.append(f"{label}: a win shows fewer than {card['cycles']} cycles")
    for key in [(foil, 0, 0) for foil in card["foils"]] + list(card["witnesses"]):
        if mixes(cells.get(key, [])):
            problems.append(f"{key[0]} at {key[1] / 1000:g} s/{key[2] / 1000:g} s mixes setups"
                            " or sources")
    wins = ", ".join(f"{n} of {need} at {k[1] / 1000:g} s age/{k[2] / 1000:g} s interval"
                     for k, n in card["witnesses"].items())
    rule = (f"Rule (pre-registered at {card['rule_revision']}): every foil loses at 0 s in each "
            f"of {card['foil_launches']} launches; the witness wins {wins} in its first launches, "
            f"each win with at least {card['cycles']} cycle. Signature v1: melee-flag gaps under "
            f"{MERGE_S} s merge into one engagement; a cycle is an applied move order inside an "
            "engagement other than the last.")
    return ["", rule, "Verdict: " + ("admitted" if not problems else "not admitted: "
                                     + "; ".join(problems))]
