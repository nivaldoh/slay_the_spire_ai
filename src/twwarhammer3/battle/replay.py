"""Public, recorded battle frames and factual events for the offline report.

No interpolation, hidden evaluation state, model narration, or outcome-based selection.
Every derived event identifies the observation or acknowledgement that supports it.
Readable unit identities come from the curated report notes, then the recorded names;
order summaries and "what happened next" facts restate recorded orders and frames only.
"""

import json
import math
import re
import statistics
from pathlib import Path

from twwarhammer3.battle.capture import RECORDER_VERSION
from twwarhammer3.battle.llm import short_type

SCHEMA = 1
UNIT_FIELDS = ("id", "type", "name", "class", "commander", "x", "z", "bearing", "men", "men0",
               "hp", "morale", "state", "target", "destination", "abilities", "ammo", "ammo0",
               "range", "dest", "command_queue", "navigation", "attack_mode", "flying", "error")
FRAME_FIELDS = ("time_ms", "seq", "phase", "magic", "army", "mode", "remaining_ms", "result")
# Role and map glyph by recorded class, for unit types the notes do not describe.
CLASS_ROLES = {"lord": ("Lord or hero", "general"), "hero": ("Lord or hero", "general"),
               "cavalry": ("Cavalry", "cavalry"),
               "missile_cavalry": ("Missile cavalry", "missile_cavalry"),
               "infantry": ("Infantry", "infantry"),
               "missile": ("Missile infantry", "missile_infantry"),
               "artillery": ("Artillery", "artillery"), "monster": ("Monster", "monster")}
STATS = {"speed": "scalar_speed", "armour": "stat_armour", "melee_attack": "stat_melee_attack",
         "melee_defence": "stat_melee_defence", "weapon_damage": "stat_weapon_damage",
         "charge_bonus": "stat_charge_bonus", "morale": "stat_morale", "ammo": "stat_ammo",
         "range_m": "scalar_missile_range"}
ERRORS = {"unreachable": "destination unreachable", "unit_routing": "unit is fleeing",
          "queue_predecessor_failed_or_missing": "the step before it failed or was missing"}
COMPASS = ("north", "north-east", "east", "south-east", "south", "south-west", "west",
           "north-west")
SMALL_WORDS = {"a", "an", "and", "at", "for", "in", "of", "on", "the", "to"}
ACCEPTED = ("acknowledged", "queued")
FACT_WINDOW_MS = 30000
MAX_FACTS = 6


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


def title(text: str) -> str:
    """``knights_of_the_realm`` -> ``Knights of the Realm``."""
    return " ".join(word if index and word in SMALL_WORDS else word[:1].upper() + word[1:]
                    for index, word in enumerate(text.replace("_", " ").split()))


def unit_name(unit: dict) -> str:
    """The recorded name, else the type key without its prefix and asset number."""
    return unit.get("name") or title(re.sub(r"_\d+$", "", short_type(unit.get("type"))))


def ability_name(key) -> str:
    """``wh_main_character_abilities_foe_seeker`` -> ``Foe Seeker``; a spell loses its lore:
    ``wh3_main_spell_tzeentch_blue_fire_of_tzeentch`` -> ``Blue Fire of Tzeentch``."""
    key = str(key or "?")
    return title(key.rsplit("abilities_", 1)[1] if "abilities_" in key
                 else re.sub(r"^wh\d?_[a-z0-9]+_(?:spell_[a-z]+_)?", "", key))


def error_text(code) -> str:
    code = str(code or "unknown")
    wrapped = re.search(r"\(error: (.+)\)$", code)  # a Lua error around the engine's message
    if wrapped:
        code = re.sub(r"unit '\d+' ", "unit ", wrapped[1])
    return ERRORS.get(code, code.replace("_", " "))


def clock(time_ms) -> str:
    return f"{int(time_ms) // 60000}:{int(time_ms) // 1000 % 60:02d}"


def base_stats(text) -> dict:
    """``faction@type:stat=value/...;type:...@@faction@...`` -> {type: {name: number}}."""
    stats = {}
    for army in (text or "").split("@@"):
        for entry in army.split("@", 1)[-1].split(";"):
            unit_type, _, values = entry.partition(":")
            recorded = {key: float(value) for key, value in
                        re.findall(r"(\w+)=(-?\d+(?:\.\d+)?)", values)}
            fields = {name: int(recorded[key]) if recorded[key].is_integer() else recorded[key]
                      for name, key in STATS.items() if key in recorded}
            if unit_type and fields:
                stats.setdefault(unit_type, fields)
    return stats


def initials(name: str) -> str:
    return "".join(word[0] for word in name.split() if word[0].isupper())[:3] or name[:3]


def identify(roster: list[dict], units: dict, stats: dict) -> None:
    """Name, number and describe each unit: a notes entry first, then the recorded name.
    Duplicates are numbered in id order. Without a notes label, two names on one side with
    the same initials (Halberdiers, Handgunners) are labelled by their first three letters."""
    for entry in roster:
        note = units.get(entry.get("type")) or {}
        role, glyph = CLASS_ROLES.get(entry.get("class"), ("Unit", "unknown"))
        if note.get("name"):
            entry.update(name=note["name"], name_source="report_notes.json")
        recorded = stats.get(entry.get("type"))
        entry.update(role=note.get("role", role), glyph=note.get("glyph", glyph),
                     about=note.get("about"), stats=recorded,
                     stats_source="result.json setup.unit_base_stats" if recorded else None,
                     short=note.get("short"))
    for entry in roster:
        side = [other for other in roster if other["side"] == entry["side"]]
        same = [other["id"] for other in side if other["name"] == entry["name"]]
        number = str(same.index(entry["id"]) + 1) if len(same) > 1 else ""
        short = entry["short"] or (entry["name"][:3] if any(
            initials(other["name"]) == initials(entry["name"])
            for other in side if other["name"] != entry["name"]) else initials(entry["name"]))
        entry.update(display=f"{entry['name']} {number}".strip(), short=short + number)


def public_frame(observation: dict, source: dict) -> dict:
    frame = {key: observation[key] for key in FRAME_FIELDS if key in observation}
    for side in ("friendly", "enemy"):
        frame[side] = [{key: unit[key] for key in UNIT_FIELDS if key in unit}
                       for unit in observation.get(side, [])]
    frame["enemy_roster"] = [{key: unit[key] for key in ("id", "type", "dead", "name")
                              if key in unit} for unit in observation.get("enemy_roster", [])]
    frame["source"] = source
    return frame


def find(frame: dict, uid) -> dict | None:
    return next((unit for side in ("friendly", "enemy") for unit in frame[side]
                 if unit.get("id") == uid), None)


def state_events(frames: list[dict], protected: list[str],
                 labels: dict | None = None) -> list[dict]:
    events, seen_dead, contact, known = [], set(), False, {}
    labels = labels or {}

    def add(kind, frame, caption, unit=None):
        events.append({"kind": kind, "time_ms": frame["time_ms"], "caption": caption,
                       "unit": unit, "source": frame["source"]})

    def qualifiers(unit, type_):
        return ((" · general" if unit.get("commander") else "")
                + (" · protected unit" if type_ in protected else ""))

    def label(uid, unit, enemy):
        return (labels.get(uid) or unit_name(unit)) + (" (enemy)" if enemy else "")

    previous = None
    for frame in frames:
        units = {u["id"]: u for side in ("friendly", "enemy") for u in frame[side]}
        enemies = {u["id"] for u in frame["enemy"]}
        for uid, unit in units.items():
            known[uid] = {**known.get(uid, {}), **unit}
        old = ({u["id"]: u for side in ("friendly", "enemy") for u in previous[side]}
               if previous else {})
        for uid, unit in units.items():
            before = old.get(uid)
            states = unit.get("state")
            prior = before.get("state") if before else None
            name = label(uid, unit, uid in enemies)
            effect = (unit.get("morale") or {}).get("effect")
            # A missing unit/state never supports a transition, especially a death.
            if states is not None and prior is not None:
                if "melee" in states and "melee" not in prior and not contact:
                    add("contact", frame, f"First melee: {name}", uid)
                    contact = True
                if "routing" in states and "routing" not in prior:
                    add("rout", frame, f"{name} began fleeing"
                        + qualifiers(unit, unit.get("type"))
                        + (f" · morale: “{effect}”" if effect else ""), uid)
                if ("routing" in prior and "routing" not in states
                        and "shattered" not in states and unit.get("men", 0) > 0):
                    add("rally", frame, f"{name} rallied", uid)
            if (before and before.get("men", 0) > 0 and unit.get("men") == 0
                    and uid not in seen_dead):
                add("death", frame, f"{name} destroyed" + qualifiers(unit, unit.get("type")), uid)
                seen_dead.add(uid)
        for unit in frame["enemy_roster"]:
            if unit.get("dead") is True and unit["id"] not in seen_dead:
                add("death", frame, f"{label(unit['id'], unit, True)} destroyed"
                    + qualifiers(known.get(unit["id"], {}), unit.get("type")), unit["id"])
                seen_dead.add(unit["id"])
        if previous:
            old_points = {p["id"]: p for p in (previous.get("mode") or {}).get("capture_points", [])
                          if "id" in p}
            for point in (frame.get("mode") or {}).get("capture_points", []):
                before = old_points.get(point.get("id"))
                if (before and "holder" in before and "holder" in point
                        and point["holder"] != before["holder"]):
                    add("objective", frame, f"Capture point {point['id']} changed hands: "
                                            f"{before['holder']} → {point['holder']}")
            for threshold in (300000, 60000, 10000):
                a, b = previous.get("remaining_ms"), frame.get("remaining_ms")
                if a is not None and b is not None and a > threshold >= b >= 0:
                    add("timer", frame, f"Timer: {clock(b)} remaining")
        previous = frame
    return events


def order_events(decisions: list[dict], frames: list[dict],
                 labels: dict | None = None) -> list[dict]:
    events = []
    labels = {"army": "Army", **(labels or {})}
    for index, decision in enumerate(decisions):
        applied = decision.get("applied_ms")
        for k, item in enumerate(decision["orders"]):
            order, ack = item["order"], item.get("ack")
            if not ack or applied is None:
                continue
            name = labels.get(order.get("unit"), order.get("unit", "Army"))
            event = {"time_ms": applied, "decision": index, "unit": order.get("unit"),
                     "source": decision.get("ack_source")}
            if not ack.get("ok"):  # steps map one to one to orders
                events.append({**event, "kind": "rejected",
                               "caption": f"Order rejected: {name}: {decision['steps'][k]['text']} "
                                          f"({error_text(ack.get('error'))})"})
            elif order.get("type") == "ability":
                events.append({**event, "kind": "ability",
                               "caption": f"{name} used {ability_name(order.get('ability'))} "
                                          "(acknowledged)"})
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
                                       "caption": f"{name} idle or without a target within 5 s "
                                                  "of its attack order on "
                                                  f"{labels.get(target['id'], target['id'])}, "
                                                  "which was still visible"})
                        break
    # Only model calls are model replies, placed when the reply took effect, not before.
    timed = [d for d in decisions if d.get("attempts") and d.get("applied_ms") is not None
             and d.get("latency", {}).get("think_s") is not None]
    if timed:
        longest = max(timed, key=lambda d: d["latency"]["think_s"])
        events.append({"kind": "longest_think", "time_ms": longest["applied_ms"],
                       "decision": decisions.index(longest), "source": longest["ack_source"],
                       "caption": f"Longest model reply: {longest['latency']['think_s']:.1f} s"})
    return events


def mark_key_events(events: list[dict], roster: list[dict]) -> None:
    """The first contact (the only one state_events reports), each side's first rout, routs
    and deaths of generals and protected units, and the ending are key events."""
    units = {entry["id"]: entry for entry in roster}
    routed = set()
    for event in events:
        unit = units.get(event.get("unit")) or {}
        important = bool(unit.get("commander") or unit.get("protected"))
        key = event["kind"] in ("contact", "end")
        if event["kind"] == "rout":
            key = unit.get("side") not in routed or important
            routed.add(unit.get("side"))
        elif event["kind"] == "death":
            key = important
        event["key"] = key


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


def step_text(order: dict, origin, labels: dict) -> str:
    """One order in plain words; moves as distance and compass point (x east, z north)."""
    kind, target = order.get("type"), labels.get(order.get("target"), order.get("target"))
    if kind == "move":
        if origin is None:
            return f"move to ({order['x']:.0f}, {order['z']:.0f})"
        dx, dz = order["x"] - origin[0], order["z"] - origin[1]
        verb, metres = "run" if order.get("run") else "walk", round(math.hypot(dx, dz) / 10) * 10
        if not metres:
            return f"{verb} less than 10 m"
        return f"{verb} {metres} m {COMPASS[round(math.degrees(math.atan2(dx, dz)) / 45) % 8]}"
    if kind == "attack":
        mode = order.get("mode")
        return (f"attack {target} in melee" if mode == "melee"
                else f"shoot at {target}" if mode == "ranged" else f"attack {target}")
    if kind == "behaviour":
        behaviour = str(order.get("behaviour")).removeprefix("change_").replace("_", " ")
        return f"turn {behaviour} {'on' if order.get('enabled') else 'off'}"
    if kind == "ability":
        text = f"use {ability_name(order.get('ability'))}"
        if target:
            return f"{text} on {target}"
        return text + (f" at ({order['x']:.0f}, {order['z']:.0f})"
                       if order.get("x") is not None and order.get("z") is not None else "")
    if kind == "flight":
        return "take off" if order.get("flying") else "land"
    if kind == "build":
        # tower_magic_3 on s1 -> magic tower 3 on slot 1
        option = re.fullmatch(r"([a-z]+)_([a-z_]+?)(?:_(\d+))?", str(order.get("option")))
        name = (f"{option[2].replace('_', ' ')} {option[1]}{' ' + option[3] if option[3] else ''}"
                if option else str(order.get("option")))
        return f"build {name} on slot {str(order.get('slot')).lstrip('s')}"
    if kind == "reinforce":
        return (f"bring in {unit_name({'type': order.get('reinforcement')})} "
                f"at zone {order.get('zone')}")
    return str(kind)


def order_steps(decision: dict, basis: dict | None, labels: dict) -> list[dict]:
    start = {u["id"]: (u["x"], u["z"]) for u in (basis or {}).get("friendly", [])
             if u.get("x") is not None and u.get("z") is not None}
    waypoint, steps = {}, []
    for item in decision["orders"]:
        order, unit = item["order"], item["order"].get("unit")
        kind, queued = order.get("type"), bool(order.get("queue"))
        step = {"unit": unit, "kind": "army" if unit == "army" else kind, "queued": queued,
                "status": item["status"],
                "error_text": (error_text(item["ack"].get("error"))
                               if item["status"] == "rejected" else None),
                "text": step_text(order, waypoint.get(unit) if queued else start.get(unit),
                                  labels)}
        if kind == "move":
            step.update(x=order.get("x"), z=order.get("z"))
        elif kind == "attack":
            step.update(target=order.get("target"), mode=order.get("mode"))
        elif kind == "ability":
            step.update(ability=order.get("ability"), target=order.get("target"))
        # A queued move starts at the previous waypoint; after an attack it is unknown.
        if kind in ("move", "attack", "halt"):
            waypoint[unit] = (order["x"], order["z"]) if kind == "move" else None
        steps.append(step)
    return steps


def summary_lines(steps: list[dict], labels: dict) -> list[dict]:
    """One line per unit in order of first appearance, the army's orders last."""
    units = sorted(dict.fromkeys(step["unit"] for step in steps), key=lambda unit: unit == "army")
    lines = []
    for unit in units:
        own = [step for step in steps if step["unit"] == unit]
        text = ""
        for step in own:
            if text:
                text += ", then " if step["queued"] else ", "
            text += step["text"] + (f" (rejected: {step['error_text']})"
                                    if step["status"] == "rejected" else "")
        rejected = sum(step["status"] == "rejected" for step in own)
        status = ("rejected" if rejected == len(own) else "partly_rejected" if rejected
                  else "ok" if all(step["status"] in ACCEPTED for step in own)
                  else "unacknowledged")
        lines.append({"unit": None if unit == "army" else unit, "status": status,
                      "text": f"{'Army' if unit == 'army' else labels.get(unit, unit)}: {text}"})
    return lines


MELEE_M = 50  # unit centres at most this far apart can be fighting each other


def engaged(unit: dict | None, attack: dict, frame: dict) -> bool:
    """The unit is recorded attacking the step's target; for a melee order, in melee with
    the target recorded close by, since a unit in melee may be fighting another one."""
    if not unit or unit.get("target") != attack["target"]:
        return False
    return attack["mode"] != "melee" or fighting(unit, attack["target"], frame)


def fighting(unit: dict, target_id: str, frame: dict) -> bool:
    target = find(frame, target_id)
    return ("melee" in (unit.get("state") or []) and target is not None
            and None not in (unit.get("x"), unit.get("z"), target.get("x"), target.get("z"))
            and math.dist((unit["x"], unit["z"]), (target["x"], target["z"])) <= MELEE_M)


def onset(frames: list[dict], uid: str, applied: int, end: int, test,
          already: bool = True) -> tuple[dict | None, bool]:
    """The first frame in (applied, end] where ``test`` holds for the unit, or, when
    ``already``, its last observation at or before ``applied`` if it held there; the bool
    says which. The frame taken at ``applied_ms`` shows the battle just before the orders
    took effect, so it never shows their effect."""
    before = next((frame for frame in reversed(frames)
                   if frame["time_ms"] <= applied and find(frame, uid)), None)
    if already and before and test(find(before, uid), before):
        return before, True
    return next((frame for frame in frames if applied < frame["time_ms"] <= end
                 and test(find(frame, uid), frame)), None), False


def next_facts(index: int, decisions: list[dict], frames: list[dict], labels: dict,
               transitions: list[dict]) -> list[dict]:
    """What the recorded frames show after a decision's orders applied, per ordered unit.
    Target routs and deaths are the observed ``state_events`` transitions."""
    decision = decisions[index]
    applied = decision.get("applied_ms")
    if applied is None or not frames:
        return []
    rejections, facts, targets = [], [], {}
    for unit in dict.fromkeys(step["unit"] for step in decision["steps"]):
        own = [step for step in decision["steps"] if step["unit"] == unit]
        name = labels.get(unit, "Army" if unit == "army" else unit)
        errors = dict.fromkeys(step["error_text"] for step in own if step["status"] == "rejected")
        if errors:
            rejections.append({"unit": unit, "time_ms": applied,
                               "text": f"{name}: rejected by the game ({'; '.join(errors)})"})
        accepted = [step for step in own if step["status"] in ACCEPTED]
        if not accepted or unit == "army":
            continue
        later = next((other["applied_ms"] for other in decisions[index + 1:]
                      if other.get("applied_ms") is not None and any(
                          step["unit"] == unit and step["status"] in ACCEPTED
                          for step in other["steps"])), None)
        limits = [(applied + FACT_WINDOW_MS, "30 s later"),
                  (frames[-1]["time_ms"], "the battle ended")]
        if later is not None:
            limits.insert(0, (later, f"its next order at {clock(later)}"))
        end, reason = min(limits, key=lambda limit: limit[0])
        window = [frame for frame in frames if applied <= frame["time_ms"] <= end]
        if not window or window[-1]["time_ms"] == applied:
            continue  # nothing recorded after the orders took effect
        moves = [step for step in accepted if step["kind"] == "move"]
        attack = next((step for step in accepted if step["kind"] == "attack"), None)
        if moves:
            # Also for an attack queued behind the route: the route is what the window shows.
            points = [(frame["time_ms"], (u["x"], u["z"])) for frame in window
                      if (u := find(frame, unit)) and u.get("x") is not None
                      and u.get("z") is not None]
            if len(points) > 1:
                metres = sum(math.dist(a[1], b[1]) for a, b in zip(points, points[1:]))
                text = (f"{name} moved " + (f"about {round(metres / 10) * 10} m" if metres >= 10
                                            else "less than 10 m")
                        + f" in {(points[-1][0] - points[0][0]) / 1000:.0f} s")
                final = (moves[-1]["x"], moves[-1]["z"])
                closest = min(points, key=lambda point: math.dist(point[1], final))
                text += (f"; closest to the final waypoint: {math.dist(closest[1], final):.0f} m "
                         f"at {clock(closest[0])}")
                facts.append({"unit": unit, "time_ms": points[0][0], "text": text})
        if attack:
            target = labels.get(attack["target"], attack["target"])
            # A queued attack starts after its route: what the unit did before is no answer.
            hit, already = onset(frames, unit, applied, end, lambda u, f: engaged(u, attack, f),
                                 not attack["queued"])
            if hit:
                doing = (f"in melee with {target}" if attack["mode"] != "ranged"
                         and fighting(find(hit, unit), attack["target"], hit)
                         else f"targeting {target}")
                # A jump point never precedes the orders.
                facts.append({"unit": unit, "time_ms": max(hit["time_ms"], applied), "text": (
                    f"{name} already {doing} at {clock(hit['time_ms'])}" if already
                    else f"{name} {doing} from {clock(hit['time_ms'])}")})
            elif not attack["queued"]:  # a queued attack waits for its route
                facts.append({"unit": unit, "time_ms": applied, "text": (
                    f"No melee between {name} and {target} recorded before {reason}"
                    if attack["mode"] == "melee"
                    else f"{name} not recorded targeting {target} before {reason}")})
            # The target's window is the longest of the windows of the units attacking it.
            targets[attack["target"]] = max(end, targets.get(attack["target"], end))
        for step in accepted:
            if step["kind"] == "ability":
                ability = ability_name(step["ability"])
                hit, already = onset(frames, unit, applied, end, lambda u, _: any(
                    item.get("key") == step["ability"] and item.get("active")
                    for item in (u or {}).get("abilities") or []))
                text = (f"{name}: {ability} {'already active at' if already else 'active from'} "
                        f"{clock(hit['time_ms'])}" if hit else
                        f"{name}: {ability} acknowledged; no active flag recorded in the window")
                facts.append({"unit": unit, "text": text,
                              "time_ms": max(hit["time_ms"], applied) if hit else applied})
    for target, end in targets.items():
        event = next((event for event in transitions if event.get("unit") == target
                      and event["kind"] in ("rout", "death")
                      and applied < event["time_ms"] <= end), None)
        if event:
            facts.append({"unit": target, "time_ms": event["time_ms"], "text": (
                f"{labels.get(target, target)} "
                f"{'began fleeing' if event['kind'] == 'rout' else 'destroyed'} "
                f"at {clock(event['time_ms'])}")})
    return rejections + sorted(facts, key=lambda fact: fact["time_ms"])


def build(episode: Path, manifest: dict | None = None, notes: dict | None = None) -> dict:
    manifest = manifest or json.loads((episode.parent / "manifest.json").read_text())
    result_path = episode / "result.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    frames, decisions, warnings, terrain, armies = {}, [], [], None, None
    by_request, notes_text, pending_invalid, battle, job = {}, None, None, None, None
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
            new_notes = behavior.get("notes", notes_text)
            decision = {key: record[key] for key in ("request", "seq", "time_ms",
                                                     "decision_time_ms") if key in record}
            decision.update(
                source=source, reason=behavior.get("reason"), notes=new_notes,
                notes_before=notes_text, notes_changed=new_notes != notes_text,
                prompt=behavior.get("prompt"), attempts=behavior.get("attempts", []),
                plan=behavior.get("plan"), plan_age_s=behavior.get("plan_age_s"),
                orders=[{"order": o, "status": "issued; acknowledgement missing"}
                        for o in record.get("orders", [])],
                invalid=pending_invalid)
            notes_text, pending_invalid = new_notes, None
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
    roster = {}
    for frame in ordered:
        for side in ("friendly", "enemy", "enemy_roster"):
            for unit in frame[side]:
                roster[unit["id"]] = {
                    **roster.get(unit["id"], {}),
                    **{k: unit[k] for k in ("id", "type", "class", "commander", "men0",
                                            "name_source") if k in unit},
                    "side": "enemy" if side.startswith("enemy") else side,
                    # A nameless roster entry never replaces a recorded name.
                    "name": (unit.get("name") or roster.get(unit["id"], {}).get("name")
                             or unit_name(unit)),
                    "protected": unit.get("type") in scenario.get("protected", [])}
    roster = sorted(roster.values(), key=lambda entry: (
        entry["side"] != "friendly", int(re.sub(r"\D", "", entry["id"]) or 0), entry["id"]))
    identify(roster, (notes or {}).get("units") or {},
             base_stats((result.get("setup") or {}).get("unit_base_stats")))
    labels = {entry["id"]: entry["display"] for entry in roster}
    for decision in decisions:
        basis = next((i for i, f in enumerate(ordered) if f.get("seq") == decision.get("seq")
                      and f["time_ms"] == decision["time_ms"]), None)
        applied = decision.get("applied_ms")
        after = next((i for i, f in enumerate(ordered)
                      if applied is not None and f["time_ms"] >= applied), None)
        steps = order_steps(decision, ordered[basis] if basis is not None else None, labels)
        decision.update(basis_frame=basis, after_frame=after,
                        latency_parts=latency_parts(decision),
                        age_s=(applied - decision["time_ms"]) / 1000 if applied is not None
                        else None,
                        reply_s=(decision.get("latency") or {}).get("think_s"),
                        steps=steps, summary=summary_lines(steps, labels))
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
    events = state_events(ordered, scenario.get("protected", []), labels)
    for index, decision in enumerate(decisions):
        facts = next_facts(index, decisions, ordered, labels, events)
        decision.update(next=facts[:MAX_FACTS], next_truncated=max(0, len(facts) - MAX_FACTS))
    events += order_events(decisions, ordered, labels)
    if ordered and result.get("status"):
        ended_by = result.get("ended_by")
        events.append({"kind": "end", "time_ms": ordered[-1]["time_ms"],
                       "source": {"file": "result.json"},
                       "caption": f"Battle ended: {result['status']}"
                                  + (" at the time limit" if ended_by == "time_limit"
                                     else f" ({ended_by.replace('_', ' ')})"
                                     if ended_by and ended_by != "engine_result" else "")})
    events.sort(key=lambda e: e["time_ms"])
    mark_key_events(events, roster)
    if recorded:
        interval = (manifest.get("recorder") or {}).get("interval_ms") or 1000
    else:  # the controller's observations are the only frames: use their own spacing
        observed = [f["time_ms"] for f in ordered if f["friendly"] or f["enemy"]]
        spacing = [b - a for a, b in zip(observed, observed[1:]) if b > a]
        least = (manifest.get("config") or {}).get("observe_ms") or 1000
        interval = (max(least, round(statistics.median(spacing) / 100) * 100) if spacing
                    else least)
    for event in events:
        event["frame"] = next((i for i, f in enumerate(ordered)
                               if f["time_ms"] >= event["time_ms"]), len(ordered) - 1)
    return {
        "schema": SCHEMA, "evidence_kind": "recorded", "episode": episode.name,
        "created_at": manifest.get("created_at", ""), "finished_at": result.get("finished_at"),
        "frames": ordered, "decisions": decisions, "events": events,
        "roster": roster, "terrain": terrain, "armies": armies,
        "warnings": warnings,
        "frame_source": ("1 Hz recorder plus decision-basis observations; no interpolation"
                         if recorded else
                         "Decision-basis observations from trace.jsonl; no interpolation"),
        "recorder_version": RECORDER_VERSION if recorded else None,
        "sample_interval_ms": interval,
        "summary": {
            "decisions": len(decisions),
            "orders": sum(len(d["orders"]) for d in decisions),
            "acknowledged_orders": sum("ack" in o for d in decisions for o in d["orders"]),
            "unacknowledged_orders": sum("ack" not in o for d in decisions for o in d["orders"]),
            "rejections": sum(o["status"] == "rejected" for d in decisions for o in d["orders"]),
            "orders_batches": sum(bool(d["orders"]) for d in decisions),
            "empty_decisions": sum(not d["orders"] for d in decisions),
            "notes_changes": sum(d["notes_changed"] for d in decisions),
        },
    }
