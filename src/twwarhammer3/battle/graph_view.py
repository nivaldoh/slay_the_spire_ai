"""Read-only graph execution views from recorded configuration and public trace rows.

Uses the source references of battle/replay.py. Test design follows GaP's
tests/runtime/test_executor.py at 71549e1: materialized graphs with explicit paths,
not snapshots of this collector's output. No donor code, game launch or model call.
"""

import json
from pathlib import Path

from gameai.provenance import sha256
from twwarhammer3.battle import graph, replay

ASSETS = Path(__file__).with_name("graph_view_assets")
NODE_EVENTS = frozenset(("started", "transition", "cancelled", "closed", "exhausted"))
EVENT_FIELDS = ("node", "node_run", "op", "status", "successor", "inputs", "outputs",
                "input_sources", "witness", "reason", "unsent_node")
SOURCE_FIELDS = ("battle", "seq", "time_ms")
ORDER_FIELDS = ("unit", "type", "target", "x", "z", "mode", "run", "queue", "facing", "width")


def fields(value, names):
    return {key: value[key] for key in names if key in value}


def collect_episode(episode):
    episode = Path(episode).resolve()
    result = json.loads((episode / "result.json").read_text())
    disclosure = (result.get("card") or {}).get("disclosure") or {}
    configuration = disclosure.get("configuration")
    if not configuration or graph.digest(configuration) != disclosure.get("configuration_sha256"):
        raise ValueError(f"{episode}: missing or mismatched recorded controller configuration")
    members = (configuration["members"] if configuration["type"] == "team"
               else {"army": {"controller": configuration}})
    graphs = {name: member["controller"]["graph"] for name, member in members.items()
              if member["controller"].get("type") == "graph"}
    for spec in graphs.values():
        graph.validate(spec)
    identities = {name: graph.digest(spec) for name, spec in graphs.items()}
    events, frames, runs, requests, published = [], [], {}, {}, {}
    battle, latest_ms = result.get("battle"), None
    rows = list(replay.records(episode / "trace.jsonl"))
    observations = {row["observation"]["seq"]: row["observation"] for _, row in rows
                    if row.get("kind") in ("observation", "result")
                    and isinstance(row.get("observation"), dict)}

    def fail(line, message):
        raise ValueError(f"{episode}/trace.jsonl:{line}: {message}")

    def add(line, kind, member, source, *, time_ms=None, **data):
        if source.get("battle") != battle:
            fail(line, "graph source belongs to a different battle")
        observation = observations.get(source.get("seq"))
        if not observation or observation["time_ms"] != source.get("time_ms"):
            fail(line, "event has no matching public source observation")
        at = max(source["time_ms"], latest_ms or source["time_ms"])
        events.append({"kind": kind, "member": member, "time_ms": at if time_ms is None
                       else max(at, time_ms), "source": fields(source, SOURCE_FIELDS),
                       "line": line, **data})

    for line, record in rows:
        kind = record.get("kind")
        if kind == "unreadable":
            fail(line, record["error"])
        if kind in ("observation", "result") and isinstance(record.get("observation"), dict):
            observation = record["observation"]
            if observation.get("battle") != battle:
                fail(line, "observation belongs to a different battle")
            latest_ms = observation["time_ms"]
            frame = replay.public_frame(graph.public_view(observation),
                                        {"file": "trace.jsonl", "line": line})
            for side in ("friendly", "enemy"):
                for unit in frame[side]:
                    unit.setdefault("name", replay.unit_name(unit))
            frames.append(frame)
        if kind == "team":
            member = record.get("member", "army")
            value = record.get("record") if record.get("event") == "member_event" else record
            if not isinstance(value, dict) or value.get("event") not in NODE_EVENTS:
                continue
            if member not in graphs or value.get("graph_sha256") != identities[member]:
                fail(line, "node event does not match its member's recorded graph")
            node = value.get("node")
            if node not in graphs[member]["nodes"]:
                fail(line, "unknown recorded graph node")
            source = value.get("source") or {}
            if "time_ms" not in source:
                # A graph can close before any deployed view; it has no battle-time event.
                if value["event"] != "closed":
                    fail(line, "node event has no public source observation")
                continue
            data = fields(value, EVENT_FIELDS)
            data["op"] = graphs[member]["nodes"][node]["op"]
            key = (member, node, value.get("node_run"))
            if value["event"] == "started":
                refs = {name: binding["ref"] for name, binding in graphs[member]["nodes"][
                    node]["inputs"].items() if isinstance(binding, dict) and "ref" in binding}
                proofs = value.get("input_sources") or {}
                if set(refs) != set(proofs):
                    fail(line, "input source fields do not match the graph bindings")
                checked = {}
                for name, ref in refs.items():
                    producer, field = ref.split(".")
                    proof = proofs[name]
                    if not isinstance(proof, dict):
                        fail(line, "input source is not a provenance record")
                    emitted = published.get((member, producer, proof.get("node_run")))
                    if (not emitted or proof.get("producer") != producer
                            or proof.get("graph_sha256") != identities[member]
                            or fields(proof, SOURCE_FIELDS) != emitted["source"]
                            or field not in emitted["outputs"]
                            or proof.get("value") != emitted["outputs"][field]
                            or value.get("inputs", {}).get(name) != proof.get("value")):
                        fail(line, "input source does not match its recorded producer")
                    checked[name] = fields(proof, (*SOURCE_FIELDS, "producer", "node_run",
                                                   "graph_sha256", "value"))
                data["input_sources"] = checked
                runs[key] = fields(data, ("inputs", "input_sources"))
            if value["event"] == "transition":
                expected = graphs[member]["nodes"][node]["next"].get(value.get("status"))
                if expected != value.get("successor") or expected is None:
                    fail(line, "transition does not match its recorded exit")
                if key not in runs:
                    fail(line, "transition has no matching member/node run start")
                data.update(runs[key])
                if value.get("status") == "succeeded":
                    published[key] = {"outputs": value.get("outputs", {}),
                                      "source": fields(source, SOURCE_FIELDS)}
            add(line, value["event"], member, source, **data)
        elif kind == "decision" and record.get("orders"):
            behavior = record.get("behavior") or {}
            member = behavior.get("member", "army")
            if member not in graphs:
                continue  # A mixed team's direct/script member has no graph to display.
            if behavior.get("graph_sha256") != identities[member]:
                fail(line, "order batch does not match its member's recorded graph")
            source = {"battle": battle, "seq": behavior.get("source_seq", record["seq"]),
                      "time_ms": behavior.get("source_ms", record["time_ms"])}
            data = {"node": behavior.get("node"), "request": record["request"],
                    "dispatch_seq": record["seq"],
                    "orders": [fields(order, ORDER_FIELDS) for order in record["orders"]]}
            if data["node"] not in graphs[member]["nodes"]:
                fail(line, "order batch has no recorded graph node")
            if record["request"] in requests:
                fail(line, "duplicate order request")
            add(line, "orders", member, source,
                time_ms=record.get("decision_time_ms", record["time_ms"]), **data)
            requests[record["request"]] = (member, source, data)
        elif kind == "ack" and record.get("request") in requests:
            member, source, data = requests[record["request"]]
            ack = record.get("ack") or {}
            indexes = [row.get("index") for row in ack.get("results", [])]
            if (ack.get("request") != record["request"]
                    or ack.get("based_on") != data["dispatch_seq"]
                    or len(set(indexes)) != len(indexes) or any(
                    not isinstance(row.get("index"), int) or row["index"] < 1
                    or row["index"] > len(data["orders"])
                    or row.get("unit") != data["orders"][row["index"] - 1].get("unit")
                    for row in ack.get("results", []))):
                fail(line, "acknowledgement does not match its recorded order batch")
            add(line, "ack", member, source, time_ms=ack.get("applied_ms"),
                node=data["node"], request=data["request"], orders_expected=len(data["orders"]),
                missing_result_indexes=[i for i in range(1, len(data["orders"]) + 1)
                                        if i not in indexes], ack={
                    **fields(ack, ("request", "based_on", "applied_ms", "accepted",
                                   "validation_error")),
                    "results": [fields(row, ("index", "unit", "ok", "queued", "error"))
                                for row in ack.get("results", [])]})
    if not frames or not any(event["kind"] == "started" for event in events):
        raise ValueError(f"{episode}: no recorded public frames or graph execution")
    events.sort(key=lambda e: (e["time_ms"], e["line"]))
    return {"episode": f"{episode.parent.name}/{episode.name}", "battle": battle,
            "graphs": graphs, "graph_sha256": identities, "events": events, "frames": frames,
            "ownership": {name: member.get("unit_types") for name, member in members.items()},
            "result": fields(result, ("status", "engine_ending")),
            "source_revision": result.get("card", {}).get("source_revision"),
            "evidence": {name: {"path": str(episode / name), "sha256": sha256(episode / name)}
                         for name in ("result.json", "trace.jsonl")}}


def collect(paths):
    episodes = []
    for path in map(Path, paths):
        episodes.extend([path] if (path / "trace.jsonl").is_file()
                        else sorted(path.glob("episode-*/")))
    if not episodes:
        raise ValueError("graph-view needs saved graph job or episode directories")
    if len({path.resolve() for path in episodes}) != len(episodes):
        raise ValueError("duplicate graph-view episode")
    return {"version": "wh3-graph-view-v1", "episodes": [collect_episode(p) for p in episodes]}


def render(data):
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    return (ASSETS / "index.html").read_text().replace("/* GRAPH_VIEW_CSS */", (
        ASSETS / "view.css").read_text()).replace("/* GRAPH_VIEW_JS */", (
            ASSETS / "view.js").read_text()).replace("/* GRAPH_VIEW_DATA */", payload)


def write(paths, output):
    output = Path(output)
    if output.suffix != ".html":
        raise ValueError("graph-view --output must end in .html")
    data = collect(paths)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(data))
    return output
