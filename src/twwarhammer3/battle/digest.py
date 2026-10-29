"""Readable digests of saved battle evidence, for reviewing a policy's mistakes.

    python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>                 episode table
    python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>/episode-0000    decision lines
    python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>/episode-0000 --at 95
    python -m twwarhammer3 digest runs/twwarhammer3/battle/<job> --units         unit fates

An episode prints its result line, then one line per decision that sent orders or carries a
model's reason: battle time, both sides' strength in the state the policy saw (units still
fighting / men; enemies as seen of the roster), tickets, point holders and supplies where
the battle type has them, the measured delay, the orders, the engine's rejections, a
commander's adopted plan with its age and the model's reason. A batch that failed
validation adds an ``invalid:`` line. An episode with observation write times (harness b51)
says whether it ran at 1x by the Windows clock; one outside the band warns, here and above
the job's table. A run of decisions that sent no new orders becomes
one line with the last reason. Then the final state and the model's last notes. ``--at``
prints the one decision nearest a battle time in full: the prompt, the raw reply, a
commander's plan, dropped items, the orders, a validation error and the engine's verdicts.
``--units`` prints, per episode, each unit's first and last observed men and ammunition,
when it was first seen in melee and routing, and the engine's refusals by error. It only
reads evidence.
"""

import json
from collections import Counter
from itertools import groupby
from pathlib import Path

from twwarhammer3.battle.commander import describe_plan
from twwarhammer3.battle.controllers import policy_parts
from twwarhammer3.battle.llm import describe_orders, short_type
from twwarhammer3.battle.stats import row

ONE_X = (0.99, 1.01)  # battle s per Windows s; the owner's "(a)" on this band, 2026-10-29


def strength(observation: dict) -> str:
    friendly = [u for u in observation.get("friendly", []) if u.get("men")]
    fighting = [u for u in friendly if not {"routing", "shattered"} & set(u.get("state", []))]
    enemy = observation.get("enemy", [])
    roster = len(observation.get("enemy_roster", []))
    return (f"us {len(fighting)}/{len(friendly)}u {sum(u['men'] for u in friendly)}m"
            f"  seen {len(enemy)}/{roster}u {sum(u.get('men', 0) for u in enemy)}m")


def objectives(observation: dict) -> str:
    """Tickets, capture point holders and supplies, for battle types that have them."""
    mode = observation.get("mode") or {}
    parts = []
    if mode.get("tickets"):
        parts.append("tickets " + " ".join(f"{entry['side']} {entry['tickets']}"
                                           for entry in mode["tickets"])
                     + (f" of {mode['tickets_goal']}" if mode.get("tickets_goal") else ""))
    if mode.get("capture_points"):
        holders = [point.get("holder") or "-" for point in mode["capture_points"]]
        parts.append("points " + ",".join(holders))
    if mode.get("supplies") is not None:
        parts.append(f"supplies {mode['supplies']}")
    return ("  " + "; ".join(parts)) if parts else ""


def _measures(result: dict) -> str:
    """The battle type's objective measures of an episode: shares held, then counts."""
    measures = result.get("objectives") or {}
    parts = [f"{label} {measures[key]:.0%}" for key, label in (
        ("victory_held", "victory points held"), ("key_held", "key building"))
        if measures.get(key) is not None]
    parts += [f"{label} {measures[key]}" for key, label in (
        ("supplies_left", "supplies left"), ("build", "built"), ("reinforce", "reinforced"),
        ("tickets", "tickets")) if key in measures]
    return "; " + ", ".join(parts) if parts else ""


def _units(observation: dict) -> list[str]:
    lines = []
    for side in ("friendly", "enemy"):
        for unit in observation.get(side, []):
            lines.append(f"  {unit['id']} {short_type(unit.get('type'))}: {unit.get('men')}/"
                         f"{unit.get('men0')} men at ({unit.get('x') or 0:.0f},"
                         f" {unit.get('z') or 0:.0f}) " + " ".join(unit.get("state") or []))
    return lines


def _decision_lines(items: list) -> list[str]:
    """One line per decision, except that a run of decisions with no new orders is one."""
    lines = []
    for quiet, group in groupby(items, key=lambda item: isinstance(item, dict) and item["quiet"]):
        group = list(group)
        if quiet and len(group) > 1:
            first, last = group[0], group[-1]
            lines.append(f"{first['s']:6.0f}s  {first['state']}  no new orders x{len(group)}"
                         f" until {last['s']:.0f}s | {last['reason']}")
        else:
            lines += [item if isinstance(item, str) else item["line"] + item.get("ack", "")
                      for item in group]
    return lines


def episode_digest(episode: Path, decisions: bool = True) -> str:
    path = episode / "result.json"
    result = json.loads(path.read_text()) if path.exists() else {"status": "running"}
    delays = result.get("delays_ms") or []
    llm = result.get("llm") or {}
    policy = f"; policy {result['policy']}" if result.get("policy") else ""
    error = f"; error: {result['error']}" if result.get("error") else ""
    lines = [
        f"{episode.name}: {result['status']} at {result.get('battle_s', '?')} s battle time;"
        f" {result.get('decisions', 0)} decisions, {result.get('invalid', 0)} invalid;"
        f" delay mean {result.get('delay_s')} s max {max(delays, default=0) / 1000:.1f} s;"
        f" ${llm.get('usd', 0):.4f}{policy}{_measures(result)}{error}",
    ]
    if "windows_clock_ratio" in result:
        lines.append(one_x(result))
    if "members" in (result.get("card", {}).get("disclosure") or {}):
        # Team evidence recorded before ``polls`` counts the dispatcher's requests.
        lines.append("team: header decisions/delay count member batches (dispatcher requests in"
                     " result.json polls); member timings below" if "polls" in result else
                     "team: header decisions/delay describe dispatcher polls; member timings below")
    observation, last, notes, refused = None, None, {}, False
    items, pending = [], {}
    for raw in (episode / "trace.jsonl").open():
        record = json.loads(raw)
        kind = record["kind"]
        if kind in ("observation", "battle", "roster", "result"):
            last = record["observation"]
            if kind == "observation":
                observation = last
        elif kind == "decision":
            behavior = record.get("behavior") or {}
            if "notes" in behavior:  # a team member's notes are its own
                notes[behavior.get("member")] = behavior["notes"]
            quiet = not record["orders"] and "plan" not in behavior and not refused
            refused = False
            if not record["orders"] and not behavior.get("reason"):
                continue
            reason = f" | {behavior['reason']}" if behavior.get("reason") else ""
            if behavior.get("member"):
                reason += (f" | {behavior['decision']} from {behavior['source_ms'] / 1000:.1f}s")
            plan = (f"  plan ({behavior['plan_age_s']:.1f} s old): "
                    f"{describe_plan(behavior['plan'])}" if "plan" in behavior else "")
            state = strength(observation) + objectives(observation)
            item = {"s": record["time_ms"] / 1000, "state": state,
                    "reason": behavior.get("reason"),
                    "quiet": quiet,
                    # A team member's delay runs from its own source state.
                    "source_ms": behavior.get("source_ms", record["time_ms"]),
                    "line": f"{record['time_ms'] / 1000:6.0f}s  {state}"
                            f"  {describe_orders(record['orders'])}{plan}{reason}"}
            pending[record["request"]] = item
            items.append(item)
        elif kind == "ack" and record["request"] in pending:
            item = pending.pop(record["request"])
            rejected = [f"{r['unit']} {r.get('error')}" for r in record["ack"].get("results", [])
                        if not r.get("ok")]
            delay = (record["ack"]["applied_ms"] - item["source_ms"]) / 1000
            item["ack"] = f"  [delay {delay:.1f}s" + (
                f"; rejected {', '.join(rejected)}]" if rejected else "]")
        elif kind == "invalid":
            items.append(f"        invalid: {record['error']}")
            refused = True  # its decision sent no orders, but not by choice
        elif kind == "team" and record["event"] == "feedback":
            latency = record["latency"]
            # Quiet member no-ops are still in the trace, but do not crowd the digest.
            if record["ack"].get("results") or record["source"] != "engine":
                age = (f"; member age {latency['delay_ms'] / 1000:.1f}s"
                       if "delay_ms" in latency else "")
                items.append(f"        {record['decision']}: {record['source']} feedback{age}"
                             f"; worker {latency['think_s']:.3f}s"
                             f"; {record['ack'].get('validation_error', '')}".rstrip("; "))
    if decisions:
        lines += _decision_lines(items)
    if last:
        lines.append(f"final at {last.get('time_ms', 0) / 1000:.0f} s: {strength(last)}"
                     f"{objectives(last)}")
        lines += _units(last)
    lines += [f"notes{f' ({member})' if member else ''}: " + text.replace("\n", " / ")
              for member, text in notes.items() if text]
    return "\n".join(lines)


def decision_at(episode: Path, seconds: float) -> str:
    """The logged decision nearest a battle time, whole: the prompt its reply answers, the
    raw reply, a commander's plan, dropped items, the orders, a validation error and the
    engine's verdict on each order.

    Of a model controller's decisions only those that carry a reply count. A commander's
    reply answers the prompt of its previous request; the direct controller's, the prompt
    logged beside it.
    """
    decisions, acks = [], {}
    asked, refused = None, None
    for raw in (episode / "trace.jsonl").open():
        record = json.loads(raw)
        if record["kind"] == "invalid":
            refused = record
        elif record["kind"] == "ack":
            acks[record["request"]] = record
        elif record["kind"] == "decision":
            behavior = record.get("behavior") or {}
            # A team member's prompt shows its own source state, not the dispatch state.
            prompt = ((behavior["prompt"], behavior.get("source_ms", record["time_ms"]))
                      if "prompt" in behavior else None)
            commander = behavior.get("type") == "commander"
            if prompt and not commander:
                asked = prompt
            record.update(asked=asked if behavior.get("attempts") else None, refused=refused)
            if prompt and commander:
                asked = prompt
            decisions.append(record)
            refused = None
    if not decisions:
        return f"{episode.name}: no logged decisions"
    replies = [record for record in decisions if record["asked"]]
    record = min(replies or decisions, key=lambda item: abs(item["time_ms"] / 1000 - seconds))
    behavior = record.get("behavior") or {}
    model = f", {behavior['model']}/{behavior.get('effort')}" if behavior.get("model") else ""
    source_ms = behavior.get("source_ms", record["time_ms"])  # a team member's own state
    lines = [f"{episode.name} {record['request']}: state at {source_ms / 1000:.1f} s,"
             f" decided at {record.get('decision_time_ms', record['time_ms']) / 1000:.1f} s"
             f"{model}"]
    if record["asked"]:
        prompt, sent_ms = record["asked"]
        lines += [f"-- prompt (state at {sent_ms / 1000:.1f} s):", prompt]
    for attempt in behavior.get("attempts") or []:
        lines += [f"-- reply ({attempt.get('status')}, {attempt.get('seconds', 0):.1f} s,"
                  f" ${attempt.get('usd', 0):.4f}):", attempt.get("text") or ""]
    if "plan" in behavior:
        lines.append(f"-- plan ({behavior['plan_age_s']:.1f} s old):"
                     f" {describe_plan(behavior['plan'])}")
    lines += [f"   dropped {item}" for item in behavior.get("dropped", [])]
    lines.append(f"-- orders: {describe_orders(record['orders'])}")
    if record["refused"]:
        lines.append(f"-- invalid, so none were sent: {record['refused']['error']}")
    ack = acks.get(record["request"])
    if not ack:
        lines.append("-- engine: no acknowledgement in the trace")
        return "\n".join(lines)
    lines.append(f"-- engine applied at {ack['ack']['applied_ms'] / 1000:.1f} s"
                 f" (delay {(ack['ack']['applied_ms'] - source_ms) / 1000:.1f} s):")
    for result in ack["ack"].get("results", []):
        index = result.get("index") or 0
        order = (describe_orders([record["orders"][index - 1]])
                 if 0 < index <= len(record["orders"]) else result.get("unit"))
        verdict = ("queued" if result.get("queued") else "ok") if result.get("ok") else (
            f"REJECTED {result.get('error')}")
        lines.append(f"   {index}. {order}: {verdict}")
    return "\n".join(lines)


DIGEST_COLUMNS = ("episode", "policy", "outcome", "battle_s", "own_left", "enemy_left",
                  "decisions", "invalid", "delay_s", "usd")


def _draw(manifest: dict) -> str:
    """A random job's draw: seed, every side's race and the map."""
    config, scenario = manifest["config"], manifest.get("scenario") or {}
    if config.get("seed") is None or not scenario.get("map"):
        return ""
    enemy = scenario.get("enemy")  # one army, a list (free-for-all) or none (survival)
    armies = [scenario["player"], *(enemy if isinstance(enemy, list) else [enemy] if enemy else [])]
    return (f" (seed {config['seed']}: {' vs '.join(army['subculture'] for army in armies)}"
            f" on {scenario['map']})")


def ran_at_1x(result: dict) -> bool:
    """Whether the battle and each of its 30 s stretches stayed within ONE_X."""
    values = [result["windows_clock_ratio"], *(result.get("windows_clock_range") or [])]
    return all(ONE_X[0] <= value <= ONE_X[1] for value in values)


def one_x(result: dict) -> str:
    """The 1x line of an episode with observation write times (harness b51)."""
    stretches = result.get("windows_clock_range")
    measure = (f"{result['windows_clock_ratio']:.4f} battle s per s over"
               f" {result['windows_clock_s']:.0f} s"
               + (f", stretches of at least 30 s (longest {result['windows_clock_longest_s']:.0f}"
                  f" s) {stretches[0]:.4f}-{stretches[1]:.4f}" if stretches else ""))
    if ran_at_1x(result):
        return f"1x by the Windows clock: {measure} (band {ONE_X[0]}-{ONE_X[1]})"
    return (f"WARNING: not 1x by the Windows clock: {measure}, outside {ONE_X[0]}-{ONE_X[1]};"
            " tell the owner")


def build_warning(job: Path) -> str | None:
    """The warning a job's game build earns when Steam updated it past the pin."""
    path = job / "manifest.json"
    deployment = (json.loads(path.read_text()).get("deployment") or {}) if path.exists() else {}
    if deployment.get("steam_build_pinned") is False:
        return (f"WARNING: game build {deployment.get('steam_build_id')} is not the pinned"
                " build; tell the owner before comparing results")
    return None


def job_digest(job: Path) -> str:
    manifest = json.loads((job / "manifest.json").read_text())
    config = manifest["config"]
    controllers = []  # a model controller with the model and effort it played with
    for name in config["policy"].split(","):
        _, model, effort = policy_parts(name, config)
        controllers.append(name + (f" {model}/{effort}" if model else ""))
    lines = [f"{job.name}: {manifest['status']}, policy {','.join(controllers)}"
             + f", scenario {config['scenario']}" + _draw(manifest)
             + f", source {manifest['source_revision'][:7]}",
             "| " + " | ".join(DIGEST_COLUMNS) + " |", "|" + "---|" * len(DIGEST_COLUMNS)]
    warnings = [build_warning(job)]
    for path in sorted(job.glob("episode-*/result.json")):
        item = row(job, path.parent)  # the register's base name; the table names the trial's
        result = json.loads(path.read_text())
        item["policy"] = result.get("policy", item["policy"])
        lines.append("| " + " | ".join(str(item[column]) for column in DIGEST_COLUMNS) + " |")
        if "windows_clock_ratio" in result and not ran_at_1x(result):
            warnings.append(f"WARNING: {path.parent.name} did not run at 1x by the Windows"
                            " clock; tell the owner (its digest has the numbers)")
    return "\n".join([*filter(None, warnings), *lines])


def unit_fates(episode: Path) -> str:
    """One table row per unit seen in the episode, then the engine's refusals by error."""
    fates, refusals = {}, Counter()
    for raw in (episode / "trace.jsonl").open():
        record = json.loads(raw)
        if record["kind"] == "ack":
            refusals.update(result.get("error", "unknown")
                            for result in record["ack"].get("results", []) if not result.get("ok"))
        observation = record.get("observation") or {}
        seconds = observation.get("time_ms", 0) / 1000
        for side in ("friendly", "enemy"):
            for unit in observation.get(side, []):
                if "men" not in unit:
                    continue
                fate = fates.setdefault(unit["id"], {
                    "side": side, "type": short_type(unit.get("type")), "men0": unit["men"],
                    "ammo0": unit.get("ammo"), "melee": None, "routing": None})
                fate.update(men=unit["men"], ammo=unit.get("ammo"))
                for flag in ("melee", "routing"):
                    if flag in unit.get("state", []) and fate[flag] is None:
                        fate[flag] = seconds
    lines = [f"{episode.name} units:", "| side | id | type | men | ammo | first melee s"
             " | first routing s |", "|---|---|---|---|---|---|---|"]
    for uid, fate in fates.items():
        ammo = f"{fate['ammo0']} → {fate['ammo']}" if fate["ammo0"] else ""
        times = [f"{fate[flag]:.1f}" if fate[flag] is not None else ""
                 for flag in ("melee", "routing")]
        lines.append(f"| {fate['side']} | {uid} | {fate['type']} | {fate['men0']} → {fate['men']}"
                     f" | {ammo} | {' | '.join(times)} |")
    lines.append("engine refusals: " + (", ".join(f"{error} {count}" for error, count
                                                  in refusals.most_common()) or "none"))
    return "\n".join(lines)


def units_digest(path: Path) -> str:
    episodes = [path] if (path / "trace.jsonl").exists() else sorted(
        episode for episode in path.glob("episode-*") if (episode / "trace.jsonl").exists())
    return "\n\n".join(unit_fates(episode) for episode in episodes)


def digest(path: Path) -> str:
    return episode_digest(path) if (path / "trace.jsonl").exists() else job_digest(path)
