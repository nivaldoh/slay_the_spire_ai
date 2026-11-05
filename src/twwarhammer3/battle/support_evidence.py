"""Offline annotations for support timing, independent of controller metadata.

SWE-bench's swebench/harness/reporting.py supplies the planned-attempt join pattern:
missing and failed attempts stay in the denominator. State flags produce observation
brackets, not precise contact times, flank detection or causal explanations. Independent
video/replay labels are still required by the proposed live procedure.
"""

import argparse
import json
import math
from pathlib import Path

from gameai.provenance import sha256
from twwarhammer3.battle.support_timing import OUT, TYPES, identities
from twwarhammer3.protocol import ProtocolError


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def first_bracket(samples, predicate):
    """First observed true with its last false reading. Unknowns widen the interval."""
    previous = None
    for sample in samples:
        value = predicate(sample)
        if value is True:
            return {"label": "observed", "interval_ms": [previous, sample["time_ms"]],
                    "seq": sample.get("seq"), "basis": "public unit flags; contact candidate"}
        if value is False:
            previous = sample["time_ms"]
    return {"label": "unclear", "interval_ms": None, "reason": "not observed in available samples"}


def unit_at(observation, uid):
    return next((u for side in ("friendly", "enemy") for u in observation.get(side, [])
                 if u.get("id") == uid and not u.get("error")), None)


def melee(observation, uid):
    unit = unit_at(observation, uid)
    return None if unit is None or "state" not in unit else "melee" in unit["state"]


def lost_support(observation, uid):
    unit = unit_at(observation, uid)
    if unit is None or "state" not in unit or "men" not in unit:
        return None
    return bool(OUT.intersection(unit["state"])) or unit["men"] == 0


def together(observation, ids):
    flags = [melee(observation, ids[role]) for role in ("infantry", "enemy")]
    if None in flags:
        return None
    return all(flags)


def annotate(episode: Path):
    paths = [episode / "trace.jsonl", episode / "result.json"]
    if not any(p.exists() for p in paths):
        return {"status": "missing", "engine_result": None, "H": None}
    issues = []
    try:
        result = json.loads(paths[1].read_text())
    except (OSError, ValueError) as exc:
        result = {}
        issues.append(f"result unreadable: {exc}")
    rows = []
    try:
        for number, line in enumerate(paths[0].read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("trace row is not an object")
                rows.append(row)
            except ValueError as exc:
                issues.append(f"trace line {number} unreadable: {exc}")
    except OSError as exc:
        issues.append(f"trace unreadable: {exc}")
    endings = [r["observation"] for r in rows if isinstance(r.get("observation"), dict)
               and r["observation"].get("result") in ("won", "lost", "draw")]
    recorded = (result.get("engine_ending") or {}).get("result")
    outcome = recorded if recorded in ("won", "lost", "draw") else (
        endings[0]["result"] if endings else None)
    # Only real observation rows; acknowledgements and decision metadata cannot create effects.
    samples = {}
    for row in rows:
        obs = row.get("observation")
        if obs and obs.get("friendly") and finite(obs.get("time_ms")):
            samples[(obs.get("battle"), obs.get("seq"))] = obs
    ordered = sorted(samples.values(), key=lambda o: (o["time_ms"], o.get("seq", 0)))
    report = {"status": result.get("status"), "engine_result": outcome, "H": None,
              "input_sha256": {p.name: sha256(p) for p in paths if p.exists()}, "issues": issues,
              "orders": [r for r in rows if r.get("kind") in ("decision", "ack", "invalid")],
              "windows_clock": {k: v for k, v in result.items() if k.startswith("windows_clock")},
              "windows_samples": [{k: r.get(k) for k in (
                  "latest_seq", "latest_written_windows_ns", "decision_time_ms")}
                  for r in rows if r.get("latest_written_windows_ns")],
              "measurement_status": "unverified; independent event labels required"}
    if result.get("invalid"):
        report["issues"].append("invalid or rejected orders")
    if result.get("status") not in ("won", "lost", "draw"):
        report["issues"].append("attempt did not complete cleanly")
    if not ordered:
        report["issues"].append("no observations")
        return report
    try:
        ids = identities(ordered[0])
        if any(identities(o) != ids for o in ordered):
            raise ProtocolError("identity changed within attempt")
        if len({o.get("battle") for o in ordered}) != 1:
            raise ProtocolError("multiple battles in trace")
    except ProtocolError as exc:
        report["issues"].append(str(exc))
        return report
    report["ids"] = ids
    report["initial_observation"] = ordered[0]
    report["cue"] = first_bracket(ordered, lambda o: together(o, ids))
    report["cavalry_melee"] = first_bracket(ordered, lambda o: melee(o, ids["cavalry"]))
    report["cavalry_movement"] = first_bracket(ordered, lambda o: (
        "moving" in unit_at(o, ids["cavalry"])["state"]
        if unit_at(o, ids["cavalry"]) and "state" in unit_at(o, ids["cavalry"]) else None))
    report["support_loss"] = first_bracket(ordered, lambda o: lost_support(o, ids["infantry"]))
    report["support_loss"]["basis"] = "routing/shattered/zero-men proxy; review required"
    contact, loss = report["cavalry_melee"]["interval_ms"], report["support_loss"]["interval_ms"]
    # JUDGEMENT: Sampling interpretation — Codex, 2026-11-04: only disjoint brackets order
    # events; overlapping/same-frame events remain unknown. Point estimates could reverse
    # the claimed support dependency. These annotations do not confirm the tactic.
    report["contact_before_support_loss"] = (
        True if contact and loss and loss[0] is not None and contact[1] <= loss[0] else
        False if contact and loss and contact[0] is not None and loss[1] <= contact[0] else None)
    report["sampling_intervals_ms"] = [b["time_ms"] - a["time_ms"]
                                        for a, b in zip(ordered, ordered[1:])]
    if endings:
        ending = endings[0]
    elif outcome and result.get("terminal_condition"):
        ending = {"result": outcome, "time_ms": result["engine_ending"].get("battle_ms"),
                  "friendly": result.get("terminal_friendly") or [],
                  "final": {"benchmark": result["terminal_condition"]}}
    else:
        report["issues"].append("no engine ending measurement")
        return report
    if outcome != ending["result"]:
        report["issues"].append("inconsistent engine endings")
    # The final private read is frozen by the engine-ending callback, not the last moving frame.
    terminal = (ending.get("final") or {}).get("benchmark") or {}
    by_id = {u.get("id"): u for u in terminal.get("units", [])}
    report["ending_units"] = []
    hp = []
    for role in ("infantry", "cavalry"):
        uid = ids[role]
        raw = by_id.get(uid)
        visible = unit_at(ending, uid) or {}
        report["ending_units"].append({"role": role, "id": uid, "raw": raw,
                                       "morale": visible.get("morale"),
                                       "morale_basis_ms": ending["time_ms"]})
        if (raw and raw.get("type") == TYPES[role]
                and finite(raw.get("hp")) and 0 <= raw["hp"] <= 1 and not raw.get("error")):
            hp.append(raw["hp"])
    if len(by_id) == len(terminal.get("units", [])) == 2 and len(hp) == 2:
        # Rests on JUDGEMENT docs/twwarhammer3/support-timing.md Proposed readiness check.
        report["H"] = sum(hp) / 2
    else:
        report["issues"].append("missing/ambiguous first-ending HP; no missing-as-dead inference")
    return report


def summarize(plan_path: Path):
    plan = json.loads(plan_path.read_text())
    attempts = []
    for job in plan["jobs"]:
        evidence = {}
        try:
            directory = Path(job["output"])
            evidence = annotate(directory / "episode-0000")
            if evidence["status"] != "missing":
                manifest = json.loads((directory / "manifest.json").read_text())
                for key in ("source_revision", "source_files", "scenario"):
                    if manifest.get(key) != plan.get(key):
                        evidence.setdefault("issues", []).append(
                            f"manifest {key} differs from plan")
                if not manifest.get("setup_checks"):
                    evidence.setdefault("issues", []).append("lobby setup checks unavailable")
                result = json.loads((directory / "episode-0000/result.json").read_text())
                if not result.get("setup_checks"):
                    evidence.setdefault("issues", []).append("battle setup checks unavailable")
                expected_policy = job["args"][job["args"].index("--policy") + 1]
                if result.get("policy") != expected_policy:
                    evidence.setdefault("issues", []).append("controller differs from plan")
        except (OSError, ValueError, TypeError, KeyError) as exc:
            evidence = {"status": "unreadable", "H": None, "engine_result": None, **evidence}
            evidence.setdefault("issues", []).append(str(exc))
        attempts.append({"block": job["block"], "arm": job["arm"],
                         "output": job["output"], **evidence})
    primary = [a for a in attempts if a["arm"] in ("contact", "delayed")]
    contact = [a for a in primary if a["arm"] == "contact"]
    delayed = [a for a in primary if a["arm"] == "delayed"]
    complete = (len(contact) == len(delayed) == 3
                and all(a.get("engine_result") and not a.get("issues") for a in primary))
    # Rests on JUDGEMENT docs/twwarhammer3/support-timing.md Proposed readiness check.
    wins = complete and all(a["engine_result"] == "won" for a in contact) and all(
        a["engine_result"] != "won" for a in delayed)
    condition = (complete and len({a["engine_result"] for a in primary}) == 1
                 and all(a.get("H") is not None for a in primary)
                 and min(a["H"] for a in contact) - max(a["H"] for a in delayed) >= .10 - 1e-12)
    return {"plan_sha256": sha256(plan_path), "attempts": attempts,
            "proposed_numerical_contrast": bool(wins or condition),
            "readiness": "unverified", "reason": "Setup/action effects and independently confirmed "
            "later contact/interaction require the agreed live check; numbers alone cannot pass."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path, help="new JSON annotation report")
    args = parser.parse_args()
    report = summarize(args.plan)
    with args.output.open("x") as file:
        json.dump(report, file, indent=2)


if __name__ == "__main__":
    main()
