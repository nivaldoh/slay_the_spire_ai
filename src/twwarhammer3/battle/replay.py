"""Public, recorded battle frames and factual events for the offline report.

No interpolation, hidden evaluation state, model narration, or outcome-based selection.
Every derived event identifies the observation or acknowledgement that supports it.
"""

import json
import math
from pathlib import Path

from twwarhammer3.battle.capture import RECORDER_VERSION
from twwarhammer3.battle.llm import short_type

SCHEMA = 1
UNIT_FIELDS = ("id", "type", "name", "class", "commander", "x", "z", "bearing", "men", "men0",
               "hp", "morale", "state", "target", "destination", "abilities", "ammo", "ammo0",
               "range", "dest", "command_queue", "navigation", "attack_mode", "flying", "error")
FRAME_FIELDS = ("time_ms", "seq", "phase", "magic", "army", "mode", "remaining_ms", "result")


def records(path: Path):
    """Read complete records; retain malformed-line warnings without inventing frames."""
    if path.exists():
        for number, line in enumerate(path.read_text().splitlines(), 1):
            try:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("not an object")
                yield number, value
            except ValueError:
                yield number, {"kind": "unreadable", "error": "Incomplete or invalid JSON"}


def unit_name(unit: dict) -> str:
    return unit.get("name") or short_type(unit.get("type")).replace("_", " ").title()


def public_frame(observation: dict, source: dict) -> dict:
    frame = {key: observation[key] for key in FRAME_FIELDS if key in observation}
    for side in ("friendly", "enemy"):
        frame[side] = [{key: unit[key] for key in UNIT_FIELDS if key in unit}
                       for unit in observation.get(side, [])]
    frame["enemy_roster"] = [{key: unit[key] for key in ("id", "type", "dead", "name")
                              if key in unit} for unit in observation.get("enemy_roster", [])]
    frame["source"] = source
    return frame


def state_events(frames: list[dict], protected: list[str]) -> list[dict]:
    events, seen_dead, contact, known = [], set(), False, {}

    def add(kind, frame, caption, unit=None):
        events.append({"kind": kind, "time_ms": frame["time_ms"], "caption": caption,
                       "unit": unit, "source": frame["source"]})

    def qualifiers(unit, type_):
        return ((" · general" if unit.get("commander") else "")
                + (" · protected unit" if type_ in protected else ""))

    previous = None
    for frame in frames:
        units = {u["id"]: u for side in ("friendly", "enemy") for u in frame[side]}
        for uid, unit in units.items():
            known[uid] = {**known.get(uid, {}), **unit}
        old = ({u["id"]: u for side in ("friendly", "enemy") for u in previous[side]}
               if previous else {})
        for uid, unit in units.items():
            before = old.get(uid)
            states = unit.get("state")
            prior = before.get("state") if before else None
            label = (f"{uid} {unit_name(unit)}" + (" (general)" if unit.get("commander") else "")
                     + (" (protected)" if unit.get("type") in protected else ""))
            effect = (unit.get("morale") or {}).get("effect")
            suffix = f" · Morale effect: “{effect}”" if effect else ""
            # A missing unit/state never supports a transition, especially a death.
            if states is not None and prior is not None:
                if "melee" in states and "melee" not in prior and not contact:
                    add("contact", frame, f"First observed melee: {label}" + suffix, uid)
                    contact = True
                if "routing" in states and "routing" not in prior:
                    add("rout", frame, f"{label} observed routing" + suffix, uid)
                if ("routing" in prior and "routing" not in states
                        and "shattered" not in states and unit.get("men", 0) > 0):
                    add("rally", frame, f"{label} observed rallied" + suffix, uid)
            if (before and before.get("men", 0) > 0 and unit.get("men") == 0
                    and uid not in seen_dead):
                add("death", frame, f"{label} has no men remaining"
                    + qualifiers(unit, unit.get("type")), uid)
                seen_dead.add(uid)
        for unit in frame["enemy_roster"]:
            if unit.get("dead") is True and unit["id"] not in seen_dead:
                add("death", frame, f"{unit['id']} {unit_name(unit)}: observed dead in roster"
                    + qualifiers(known.get(unit["id"], {}), unit.get("type")), unit["id"])
                seen_dead.add(unit["id"])
        if previous:
            old_points = {p["id"]: p for p in (previous.get("mode") or {}).get("capture_points", [])
                          if "id" in p}
            for point in (frame.get("mode") or {}).get("capture_points", []):
                before = old_points.get(point.get("id"))
                if (before and "holder" in before and "holder" in point
                        and point["holder"] != before["holder"]):
                    add("objective", frame,
                        f"{point['id']} ownership: {before['holder']} → {point['holder']}")
            for threshold in (300000, 60000, 10000):
                a, b = previous.get("remaining_ms"), frame.get("remaining_ms")
                if a is not None and b is not None and a > threshold >= b >= 0:
                    add("timer", frame, f"Timer observed at {b / 1000:g} s remaining")
        previous = frame
    return events


def order_events(decisions: list[dict], frames: list[dict]) -> list[dict]:
    events = []
    for index, decision in enumerate(decisions):
        applied = decision.get("applied_ms")
        for item in decision["orders"]:
            order, ack = item["order"], item.get("ack")
            if not ack or applied is None:
                continue
            event = {"time_ms": applied, "decision": index, "unit": order.get("unit"),
                     "source": decision.get("ack_source")}
            if not ack.get("ok"):
                events.append({**event, "kind": "rejected",
                               "caption": f"{order.get('unit', 'army')} {order.get('type')}: "
                                          f"rejected · {ack.get('error', 'unknown code')}"})
            elif order.get("type") == "ability":
                events.append({**event, "kind": "ability",
                               "caption": f"{order.get('unit')} ability acknowledged: "
                                          f"{order.get('ability')}"})
            elif order.get("type") == "attack" and not ack.get("queued"):
                # Stop at another issued order: it may have superseded this attack.
                stop = min((other["applied_ms"] for other in decisions[index + 1:]
                            if other.get("applied_ms") is not None
                            and any(o["order"].get("unit") == order.get("unit")
                                    and (o.get("ack") or {}).get("ok") for o in other["orders"])),
                           default=applied + 5001)
                for frame in frames:
                    if not applied < frame["time_ms"] <= min(applied + 5000, stop - 1):
                        continue
                    unit = next((u for u in frame["friendly"] if u["id"] == order.get("unit")),
                                None)
                    target = next((u for u in frame["enemy"] if u["id"] == order.get("target")),
                                  None)
                    if (unit and target and target.get("men", 0) > 0 and unit.get("men", 0) > 0
                            and "state" in unit
                            and ("idle" in unit["state"] or not unit.get("target"))):
                        events.append({**event, "time_ms": frame["time_ms"],
                                       "source": frame["source"], "kind": "lapsed",
                                       "caption": f"{unit['id']} order lapsed: idle or no target "
                                                  f"observed within 5 s; {target['id']} still "
                                                  "visible alive"})
                        break
    timed = [d for d in decisions if d.get("latency", {}).get("think_s") is not None]
    if timed:
        longest = max(timed, key=lambda d: d["latency"]["think_s"])
        events.append({"kind": "longest_think", "time_ms": longest["time_ms"],
                       "decision": decisions.index(longest), "source": longest["source"],
                       "caption": f"Longest recorded think: {longest['latency']['think_s']:g} s"})
    return events


def latency_parts(decision: dict) -> dict:
    attempts, latency = decision.get("attempts", []), decision.get("latency", {})
    calls = (sum(a["seconds"] for a in attempts)
             if attempts and all(a.get("seconds") is not None for a in attempts) else None)
    provider = (sum(a["provider_processing_ms"] / 1000 for a in attempts)
                if attempts and all(a.get("provider_processing_ms") is not None for a in attempts)
                else None)
    return {"provider_s": provider, "call_s": calls,
            "transport_residual_s": (calls - provider
                                     if calls is not None and provider is not None else None),
            "harness_roundtrip_residual_s": (latency["roundtrip_s"] - latency["think_s"]
                                             if "roundtrip_s" in latency and "think_s" in latency
                                             else None)}


def build(episode: Path, manifest: dict | None = None) -> dict:
    manifest = manifest or json.loads((episode.parent / "manifest.json").read_text())
    result_path = episode / "result.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    frames, decisions, warnings, terrain, armies = {}, [], [], None, None
    by_request, notes, pending_invalid, battle, job = {}, None, None, None, None
    for line, record in records(episode / "trace.jsonl"):
        source = {"file": "trace.jsonl", "line": line}
        kind = record.get("kind")
        obs = record.get("observation")
        if isinstance(obs, dict) and obs.get("time_ms") is not None:
            battle, job = obs.get("battle", battle), obs.get("job", job)
            terrain = obs.get("terrain") or terrain
            armies = obs.get("armies") or armies
            frames[(obs["time_ms"], obs.get("seq"))] = public_frame(obs, source)
        if kind == "unreadable":
            warnings.append({**source, "error": record["error"]})
        elif kind == "invalid":
            pending_invalid = {**record, "source": source}
        elif kind == "decision":
            behavior = record.get("behavior") or {}
            new_notes = behavior.get("notes", notes)
            decision = {key: record[key] for key in ("request", "seq", "time_ms",
                                                     "decision_time_ms") if key in record}
            decision.update(
                source=source, reason=behavior.get("reason"), notes=new_notes,
                notes_before=notes, notes_changed=new_notes != notes,
                prompt=behavior.get("prompt"), attempts=behavior.get("attempts", []),
                plan=behavior.get("plan"), plan_age_s=behavior.get("plan_age_s"),
                orders=[{"order": o, "status": "issued; acknowledgement missing"}
                        for o in record.get("orders", [])],
                invalid=pending_invalid)
            notes, pending_invalid = new_notes, None
            by_request[record["request"]] = decision
            decisions.append(decision)
        elif kind == "ack" and record.get("request") in by_request:
            decision = by_request[record["request"]]
            ack = record.get("ack") or {}
            decision.update(applied_ms=ack.get("applied_ms"), ack_source=source,
                            latency=record.get("latency") or {})
            for reply in ack.get("results", []):
                index = reply.get("index", 0) - 1
                if 0 <= index < len(decision["orders"]):
                    decision["orders"][index].update(
                        ack=reply, status="rejected" if not reply.get("ok")
                        else "queued" if reply.get("queued") else "acknowledged")
    recorded = 0
    for line, record in records(episode / "replay.jsonl"):
        source = {"file": "replay.jsonl", "line": line}
        if (record.get("kind") == "unreadable" or record.get("recorder") != RECORDER_VERSION
                or not battle or record.get("battle") != battle or record.get("job") != job
                or not isinstance(record.get("time_ms"), (int, float))):
            warnings.append({**source, "error": "Incomplete or mismatched recorder frame"})
            continue
        frames[(record["time_ms"], -1)] = public_frame(record, source)
        recorded += 1
    ordered = sorted(frames.values(), key=lambda f: (f["time_ms"], f.get("seq", -1)))
    for decision in decisions:
        basis = next((i for i, f in enumerate(ordered) if f.get("seq") == decision.get("seq")
                      and f["time_ms"] == decision["time_ms"]), None)
        applied = decision.get("applied_ms")
        after = next((i for i, f in enumerate(ordered)
                      if applied is not None and f["time_ms"] >= applied), None)
        decision.update(basis_frame=basis, after_frame=after,
                        latency_parts=latency_parts(decision))
        movement = []
        if basis is not None and after is not None:
            first = {u["id"]: u for side in ("friendly", "enemy") for u in ordered[basis][side]}
            for side in ("friendly", "enemy"):
                for unit in ordered[after][side]:
                    prior = first.get(unit["id"])
                    if prior and all(u.get(k) is not None for u in (unit, prior) for k in "xz"):
                        movement.append({"unit": unit["id"], "side": side,
                                         "from": [prior["x"], prior["z"]],
                                         "to": [unit["x"], unit["z"]],
                                         "metres": math.hypot(unit["x"] - prior["x"],
                                                              unit["z"] - prior["z"])})
        decision["displacements"] = movement
    scenario = manifest.get("scenario") or {}
    names_path = episode / "unit_names.json"
    if names_path.exists():
        names = json.loads(names_path.read_text())
        for frame in ordered:
            for side in ("friendly", "enemy", "enemy_roster"):
                for unit in frame[side]:
                    name = names.get(unit["id"])
                    if isinstance(name, str) and name:
                        unit.update(name=name, name_source="unit_names.json")
    events = state_events(ordered, scenario.get("protected", [])) + order_events(decisions, ordered)
    if ordered and result.get("status"):
        events.append({"kind": "end", "time_ms": ordered[-1]["time_ms"],
                       "source": {"file": "result.json"},
                       "caption": f"Recorded ending: {result['status']} · "
                                  f"{result.get('ended_by', 'unclassified')}"})
    events.sort(key=lambda e: e["time_ms"])
    for event in events:
        event["frame"] = next((i for i, f in enumerate(ordered)
                               if f["time_ms"] >= event["time_ms"]), len(ordered) - 1)
    roster = {}
    for frame in ordered:
        for side in ("friendly", "enemy", "enemy_roster"):
            for unit in frame[side]:
                roster[unit["id"]] = {
                    **roster.get(unit["id"], {}),
                    **{k: unit[k] for k in ("id", "type", "class", "commander", "men0",
                                            "name_source") if k in unit},
                    "side": "enemy" if side.startswith("enemy") else side,
                    "name": unit_name(unit),
                    "protected": unit.get("type") in scenario.get("protected", [])}
    return {
        "schema": SCHEMA, "evidence_kind": "recorded", "episode": episode.name,
        "created_at": manifest.get("created_at", ""), "finished_at": result.get("finished_at"),
        "frames": ordered, "decisions": decisions, "events": events,
        "roster": list(roster.values()), "terrain": terrain, "armies": armies,
        "warnings": warnings,
        "frame_source": ("1 Hz recorder plus decision-basis observations; no interpolation"
                         if recorded else
                         "Decision-basis observations from trace.jsonl; no interpolation"),
        "recorder_version": RECORDER_VERSION if recorded else None,
        "sample_interval_ms": (manifest.get("config") or {}).get("observe_ms", 1000),
        "summary": {
            "decisions": len(decisions),
            "orders": sum(len(d["orders"]) for d in decisions),
            "acknowledged_orders": sum("ack" in o for d in decisions for o in d["orders"]),
            "unacknowledged_orders": sum("ack" not in o for d in decisions for o in d["orders"]),
            "rejections": sum(o["status"] == "rejected" for d in decisions for o in d["orders"]),
            "empty_decisions": sum(not d["orders"] for d in decisions),
            "notes_changes": sum(d["notes_changed"] for d in decisions),
        },
    }
