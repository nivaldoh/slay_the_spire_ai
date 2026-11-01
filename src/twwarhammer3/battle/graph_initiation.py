"""Temporary pre-contact attack-path check for explicitly declared graph initiators.

Reference: graph-robots/graph-as-policy gap/runtime/validate.py at 71549e1
(control-flow validation), plus the owner's 2026-11-01 infantry/cavalry contract.
This is an optimistic path check, not a simulator or an engine-effect witness.
"""
import json
import math
from copy import deepcopy
from pathlib import Path

from gameai.provenance import sha256
from twwarhammer3.battle import graph, skills, team
from twwarhammer3.battle import skill_contracts as catalog

VERSION = "wh3-graph-initiation-v1"


def valid_units(observation):
    """Only the public fields used by projection and frozen tactics, before API calls."""
    if not isinstance(observation, dict):
        return False
    sides = [observation.get(side, []) for side in ("friendly", "allies", "enemy")]
    if any(not isinstance(side, list) for side in sides):
        return False
    units = [unit for side in sides for unit in side]
    if any(not isinstance(unit, dict) for unit in units):
        return False
    ids = [unit.get("id") for unit in units]
    if not all(isinstance(uid, str) and uid for uid in ids) or len(ids) != len(set(ids)):
        return False
    try:
        return all(
            all(unit.get(key) is None or isinstance(unit[key], str)
                for key in ("type", "class", "target"))
            and isinstance(unit.get("state", []), list)
            and all(isinstance(state, str) for state in unit.get("state", []))
            and type(unit.get("men", 0)) in (int, float)
            and math.isfinite(unit.get("men", 0))
            and all(unit.get(key) is None or (type(unit[key]) in (int, float)
                    and math.isfinite(unit[key])) for key in ("x", "z", "ammo", "range"))
            for unit in units)
    except (TypeError, OverflowError):
        return False


def prepare_view(observation):
    if not valid_units(observation):
        raise ValueError("invalid public starting unit data (IDs, state or numeric geometry)")
    view = graph.public_view(observation)
    if (not isinstance(view.get("battle"), str) or not view["battle"]
            or type(view.get("seq")) is not int or view["seq"] < 0
            or type(view.get("time_ms")) is not int or view["time_ms"] < 0):
        raise ValueError("initiation starting view needs battle identity, seq and time_ms")
    if view.get("phase") != "Deployed" or catalog.public_contact(view):
        raise ValueError("initiation check needs a deployed public starting view before melee")
    if not all(any(catalog.available(u) for u in view.get(side, []))
               for side in ("friendly", "enemy")):
        raise ValueError("initiation check needs active owned units and visible enemies")
    return view


def starting_views(episode, composition, initiators):
    """Read only first member inputs; the result/replay files are never consulted."""
    if (not initiators or len(set(initiators)) != len(initiators)
            or set(initiators) - composition["members"].keys()):
        raise ValueError("initiators must be distinct declared team members")
    trace = Path(episode) / "trace.jsonl"
    views, lines = {}, {}
    with trace.open() as stream:
        for number, line in enumerate(stream, 1):
            row = json.loads(line)
            name = row.get("member")
            if (row.get("kind") != "team" or row.get("event") != "input"
                    or name not in initiators or name in views):
                continue
            views[name] = member_view(row["observation"], composition, name)
            lines[name] = number
            if len(views) == len(initiators):
                break
    if set(views) != set(initiators):
        raise ValueError("starting episode is missing an initiator's first public input")
    if len({view["battle"] for view in views.values()}) != 1:
        raise ValueError("initiator starting views must belong to the same battle")
    return {"version": VERSION, "checker_sha256": sha256(Path(__file__)),
            "temporary": True, "initiators": list(initiators),
            "views": views, "source": {"episode": str(Path(episode).resolve()),
                "trace_sha256": sha256(trace), "lines": lines}}


def member_view(raw, composition, name):
    if not valid_units(raw):
        raise ValueError("invalid public starting unit data (IDs, state or numeric geometry)")
    roster = raw.get("friendly", []) + raw.get("allies", [])
    declared = {kind for m in composition["members"].values() for kind in m["unit_types"] or []}
    kinds = composition["members"][name]["unit_types"]
    owned = {u["id"] for u in roster if (u.get("type") in kinds if kinds is not None
                                         else u.get("type") not in declared)}
    return prepare_view(team.project({**raw, "friendly": roster}, owned))


def check(spec, observation):
    """Find a legal attack route with no contact; raise if every route waits or ends.

    JUDGEMENT: Temporary initiation semantics — Codex, 2026-11-01, implementing the
    owner's temporary approval: valid move/hold exits are possible, not guaranteed.
    Requiring effects would reject more plans; this checks a pre-contact route only.
    """
    spec, view = graph.validate(spec), prepare_view(observation)
    nodes = spec["nodes"]
    owned = [u for u in view["friendly"] if catalog.available(u)]

    def value(item):
        if not isinstance(item, dict) or "ref" not in item:
            return deepcopy(item)
        producer, field = item["ref"].split(".")
        node = nodes[producer]
        if field == "units":
            return [u["id"] for u in owned]
        units = [u for u in owned if u["id"] in value(node["inputs"]["units"])]
        enemies = [u for u in view["enemy"] if catalog.available(u)
                   and (node.get("mode") != "engaged" or "melee" in u.get("state", []))]
        target = min(enemies, key=lambda e: (min(skills.distance(u, e) for u in units), e["id"]),
                     default=None) if units else None
        return target["id"] if target else None

    pending, seen = [(spec["entry"], [])], set()
    while pending:
        name, path = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        node = nodes[name]
        op = node["op"]
        inputs = {key: value(item) for key, item in node["inputs"].items()}
        if op == "end":
            continue
        if op == "owned":
            exits = ["succeeded" if owned else "empty"]
        elif op == "contact":
            exits = ["no"]
        elif op == "select_target":
            target = value({"ref": f"{name}.target"})
            exits = ["succeeded" if target else "empty"]
        elif catalog.preconditions(op, inputs, view):
            exits = ["failed"]
        else:
            status, orders, _ = catalog.SkillRun(op, inputs, view["time_ms"]).tick(view)
            attacks = [order for order in orders if order["type"] == "attack"]
            if attacks:
                return {"version": VERSION, "graph_sha256": graph.digest(spec),
                        "view_sha256": graph.digest(view), "path": path + [{"node": name}],
                        "attack": {"op": op, "inputs": inputs},
                        "initial_orders": orders, "attack_orders": attacks}
            # Future skill exits are possibilities, not fabricated completion witnesses.
            exits = ([status] if status != "running" else list(node["next"])
                     if op in ("move", "hold") else ["failed", "cancelled"])
        pending.extend((node["next"][status], path + [{"node": name, "exit": status}])
                       for status in exits)
    raise ValueError("initiator has no attack route before contact: allow a visible target "
                     "without requiring existing melee; waiting roles need not initiate")


def reports(composition, record):
    """Recompute the optional embedded proof when loading an authored artifact."""
    if (record.get("version") != VERSION or record.get("temporary") is not True
            or record.get("checker_sha256") != sha256(Path(__file__))):
        raise ValueError("unknown initiation check record")
    names = record["initiators"]
    if (not names or len(set(names)) != len(names) or set(names) != set(record["views"])
            or set(names) - composition["members"].keys()):
        raise ValueError("initiation proof has missing or repeated members")
    if len({view["battle"] for view in record["views"].values()}) != 1 or any(
        record["views"][name] != member_view(record["views"][name], composition, name)
        for name in names
    ):
        raise ValueError("initiation proof has nonpublic, misowned or mixed-battle starting views")
    return {name: {**check(composition["members"][name]["controller"]["graph"],
                           record["views"][name]),
                   "source_sha256": graph.digest(record.get("source"))} for name in names}
