"""Offline coordinator/specialist graph authoring and revision after whole battles.

Reference: graph-robots/graph-as-policy gap/cli/generate.py and gap/agent at
71549e1; MORSL skill descriptions at 752dfbd. No donor code. Authors produce
JSON data, never Python, and cannot change skills, ownership or an evaluator.
"""

import hashlib
import json
from copy import deepcopy
from functools import partial
from pathlib import Path

from gameai.llm import Model, api_key, check_fields, post
from gameai.provenance import git, sha256, write_json
from twwarhammer3.battle import configured, graph, skills, team
from twwarhammer3.battle import skill_contracts as catalog
from twwarhammer3.battle.llm import MAX_OUTPUT_TOKENS

ARTIFACT_TYPE = "wh3-graph-author"
VERSION = f"{ARTIFACT_TYPE}-v2"
# JUDGEMENT: Author limits — Codex, 2026-11-01: one repair, latest 12 views/orders/acks
# per member and 2000 characters per coordinator task. More history or attempts changes
# what authors can learn and spend; this is a bounded baseline, not a learning study.
RETRIES = 1
FEEDBACK_LIMIT = 12
TASK_LIMIT = 2000

DESCRIPTIONS = {
    "owned": "Select currently active owned unit IDs; destroyed/routing/shattered units excluded.",
    "select_target": "Nearest visible active enemy to selected units; mode engaged requires melee.",
    "contact": "Branch yes if any visible friend, ally or enemy is in melee, else no.",
    "move": "Move selected units to a world point; success requires public arrival, not an ack.",
    "hold": "Hold a supplied world point; allow melee. Complete at post after the retry interval.",
    "engage": "Attack only the chosen visible enemy; success is own melee with that target.",
    "charge": "Chosen enemy must already be in melee; success is own melee with it, not a bonus.",
    "shoot": "Visible target and ammo required; ammo decreases between readings of that target.",
    "end": "End graph orders; leaves existing engine orders active. Does not mean a battle win.",
}
INSTRUCTIONS = """Build a WH3 policy from the supplied frozen skill library and public task.
The coordinator assigns tasks to the declared members; ownership cannot change.
unit_types null means every friendly unit type not claimed by another member.
Specialists return a JSON object with graph_json, a string containing the graph JSON.
Use only the listed operations. Graphs have version, entry, and a nodes object.
Set the graph's version to library.graph_version.
Each node has op, inputs and next, covering every named exit; end has empty inputs/next.
Inputs are typed literals or {"ref":"producer.field"}; every path must run that producer
successfully before consuming it. Repeated consumers need a new producer run, so recovery
loops should return through owned and select_target. Target modes are nearest or engaged.
Put select_target's mode at the node, alongside op/inputs/next, never inside inputs.
Points are literal objects with numeric x and z. There is no named current_post or
unit-position lookup. If no point is supplied, wait through observation branches
without move/hold orders; do not invent a post. See library.types and node_options.
Optional node fields are timeout_ms and max_visits, both positive integers. No scripts,
imports, expressions, arbitrary tools, unit reassignment, scorer edits or live graph edits.
One transition advances per new observation. Attack targets can hide, die or rout; failures
must recover explicitly. Prefer owned and select_target over fixed unit or enemy IDs.
An acknowledgement is not an effect. Success or local cancellation does not halt a unit.
Produce a small graph for the task. Use only supplied public evidence when revising;
do not invent unseen state, claim a win, or infer that a change improved performance.
"""
GRAPH_REPLY = {"type": "object", "properties": {"graph_json": {"type": "string"}},
               "required": ["graph_json"], "additionalProperties": False}
ORDER_FIELDS = ("unit", "type", "target", "x", "z", "mode", "run", "queue", "facing", "width")
ACK_FIELDS = ("request", "based_on", "applied_ms", "accepted", "validation_error")


def frozen_library():
    return {"version": catalog.VERSION, "graph_version": graph.VERSION,
            "contracts": deepcopy(catalog.CONTRACTS),
            "types": {
                "units": {"type": "array", "items": {"type": "string"},
                          "minItems": 1, "uniqueItems": True},
                "target": {"type": "string", "minLength": 1,
                           "description": "Currently visible enemy ID"},
                "point": {"type": "object", "properties": {
                    "x": {"type": "number"}, "z": {"type": "number"}},
                    "required": ["x", "z"], "additionalProperties": False}},
            "node_options": {"mode": {"operation": "select_target",
                                     "values": ["nearest", "engaged"], "location": "node"}},
            "descriptions": dict(DESCRIPTIONS),
            "parameters": {"arrival_m": catalog.ARRIVAL_M, "timeout_ms": catalog.TIMEOUT_MS,
                           "retry_ms": catalog.REPEAT_MS, "hold_engage_m": skills.ENGAGE_M,
                           "max_visits": graph.MAX_VISITS, "max_age_ms": graph.MAX_AGE_MS},
            "sources": {name: sha256(Path(module.__file__)) for name, module in (
                ("catalog", catalog), ("tactics", skills),
                ("runtime", graph), ("projection", team))}}


def load_template(path):
    """The first authoring release handles two graph members; runtime composition stays general."""
    raw = json.loads(Path(path).read_text())
    if (not isinstance(raw, dict) or raw.get("type") != "team"
            or not isinstance(raw.get("members"), dict) or len(raw["members"]) != 2 or any(
        member.get("controller", {}).get("type") != "graph" for member in raw["members"].values()
    )):
        raise ValueError("authoring needs a two-graph team template")
    config = {}
    configured.factory(path, config)  # resolves/fixes data; no instances or model leaves
    return config["controller_spec"]


def authority(composition):
    value = deepcopy(composition)
    for member in value["members"].values():
        member["controller"] = {"type": "graph"}
    return value


def read_bytes(path):
    data = Path(path).read_bytes()
    return data, hashlib.sha256(data).hexdigest()


def load_artifact(directory, library=None):
    """Verify an artifact's bytes and library before preparation or a new model call."""
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    data, digest = read_bytes(directory / "controller.json")
    candidate = json.loads(data)
    if (manifest.get("artifact_type") != ARTIFACT_TYPE or manifest.get("version") != VERSION
            or manifest.get("status") != "ready"
            or manifest.get("controller_sha256") != digest):
        raise ValueError("previous candidate is incomplete or changed")
    if (manifest.get("library_sha256") != graph.digest(manifest.get("library"))
            or manifest["library_sha256"] != graph.digest(library or frozen_library())):
        raise ValueError("previous candidate used a different frozen skill library")
    if manifest.get("authority") != authority(candidate):
        raise ValueError("candidate authority differs from its frozen manifest")
    for member in candidate["members"].values():
        graph.validate(member["controller"]["graph"])
    return candidate, {"directory": str(directory.resolve()), "controller_sha256": digest,
                       "library_sha256": manifest["library_sha256"]}


def previous_artifact(directory, template, library):
    candidate, identity = load_artifact(directory, library)
    if authority(candidate) != authority(template):
        raise ValueError("previous candidate has different ownership or dispatcher settings")
    return candidate, identity


def scalars(value, keys):
    return {key: value[key] for key in keys if key in value
            and (value[key] is None or isinstance(value[key], (str, int, float, bool)))}


def public_feedback(episode, composition, library_sha256):
    """Only per-member public views, ordinary own orders and own feedback reach authors.

    Completed engine results and file hashes gate/identify evidence but never enter
    prompts. The coordinator receives no battle evidence; each specialist gets its view.
    """
    episode = Path(episode)
    result_data, result_hash = read_bytes(episode / "result.json")
    trace_data, trace_hash = read_bytes(episode / "trace.jsonl")
    result = json.loads(result_data)
    ending = result.get("engine_ending") or {}
    if ending.get("result") not in ("won", "lost", "draw"):
        raise ValueError("revision evidence must be a completed whole battle")
    disclosure = (result.get("card") or {}).get("disclosure") or {}
    if disclosure.get("configuration_sha256") != graph.digest(composition):
        raise ValueError("evidence did not run the previous candidate")
    if (disclosure.get("artifact") or {}).get("library_sha256") != library_sha256:
        raise ValueError("evidence did not run the frozen library artifact")
    members = composition["members"]
    declared = {kind for member in members.values() for kind in member["unit_types"] or []}
    histories = {name: {"views": [], "orders": [], "feedback": []} for name in members}
    views = {}
    for line in trace_data.splitlines():
        event = json.loads(line)
        if (event.get("kind") == "team" and event.get("event") == "input"
                and event.get("member") in members):
            name = event["member"]
            raw = event["observation"]
            roster = raw.get("friendly", []) + raw.get("allies", [])
            kinds = members[name]["unit_types"]
            owned = {u["id"] for u in roster if (u.get("type") in kinds if kinds is not None
                                                 else u.get("type") not in declared)}
            view = team.project({**raw, "friendly": roster}, owned,
                                army=name == composition["army_owner"])
            histories[name]["views"].append(view)
            views[name, view["seq"]] = view
        elif event.get("kind") == "decision":
            name = (event.get("behavior") or {}).get("member")
            if name in histories and event.get("orders"):
                seq = event["behavior"].get("source_seq", event["seq"])
                source = views.get((name, seq))
                if source is None:
                    raise ValueError("member decision has no public source view")
                owned = {u["id"] for u in source["friendly"]}
                histories[name]["orders"].append({"seq": seq,
                    "orders": [scalars(order, ORDER_FIELDS) for order in event["orders"]
                               if order.get("unit") in owned]})
        elif event.get("kind") == "team" and event.get("event") == "feedback":
            name = event.get("member")
            if name in histories:
                ack = event["ack"]
                if not histories[name]["views"]:
                    raise ValueError("member feedback has no public ownership context")
                owned = {u["id"] for u in histories[name]["views"][-1]["friendly"]}
                if any(row.get("unit") not in owned for row in ack.get("results", [])):
                    raise ValueError("member feedback includes a unit it does not own")
                histories[name]["feedback"].append({**scalars(ack, ACK_FIELDS), "results": [
                    scalars(row, ("index", "unit", "ok", "queued", "error"))
                    for row in ack.get("results", [])]})
    feedback = {name: {key: rows[-FEEDBACK_LIMIT:] for key, rows in history.items()}
                for name, history in histories.items()}
    counts = {name: {key: len(rows) for key, rows in history.items()}
              for name, history in histories.items()}
    if any(not value["views"] for value in feedback.values()):
        raise ValueError("completed battle has no usable public observations")
    return feedback, {"episode": str(episode.resolve()), "counts": counts,
                      "files": {"result.json": result_hash, "trace.jsonl": trace_hash}}


def coordinator_schema(names):
    item = {"type": "object", "properties": {
        "member": {"type": "string", "enum": list(names)}, "task": {"type": "string"}},
        "required": ["member", "task"], "additionalProperties": False}
    return {"type": "object", "properties": {"tasks": {"type": "array", "items": item}},
            "required": ["tasks"], "additionalProperties": False}


def generate(template_path, task, output, ledger, *, model, effort="low", provider="anthropic",
             previous=None, evidence=None, send=None):
    """A new immutable candidate; a caller explicitly chooses whether a later job runs it."""
    template, library = load_template(template_path), frozen_library()
    if not isinstance(task, str) or not task.strip():
        raise ValueError("a public task is required")
    if bool(previous) != bool(evidence):
        raise ValueError("revision requires both --previous and --evidence")
    parent, parent_record, feedback, evidence_record = None, None, {}, None
    if previous:
        parent, parent_record = previous_artifact(previous, template, library)
        feedback, evidence_record = public_feedback(
            evidence, parent, parent_record["library_sha256"])
    output = Path(output)
    output.mkdir(parents=True)
    manifest = {"artifact_type": ARTIFACT_TYPE, "version": VERSION,
                "status": "running", "task": task,
                "source_revision": git("rev-parse", "HEAD").strip(),
                "source_sha256": sha256(Path(__file__)), "library": library,
                "library_sha256": graph.digest(library), "authority": authority(template),
                "model": model, "effort": effort, "provider": provider,
                "ledger": str(ledger.path.resolve()), "budget_usd": ledger.budget,
                "feedback_limit": FEEDBACK_LIMIT, "retries": RETRIES,
                "instructions": INSTRUCTIONS, "parent": parent_record, "evidence": evidence_record}
    write_json(output / "manifest.json", manifest)
    api = None
    call_count = 0

    def ask(role, content, schema, parse):
        nonlocal call_count
        call_count += 1
        prompt = json.dumps(content, sort_keys=True, allow_nan=False)
        write_json(output / f"prompt-{call_count:02d}.json", {
            "role": role, "prompt": prompt, "schema": schema})
        try:
            reply, _ = api.ask(prompt, schema, parse, retries=RETRIES)
            return reply
        finally:
            with (output / "calls.jsonl").open("a") as stream:
                for exchange in api.drain_exchanges():
                    stream.write(json.dumps({"role": role, **exchange}, sort_keys=True) + "\n")
            manifest["totals"] = dict(api.totals)
            write_json(output / "manifest.json", manifest)

    try:
        if send is None:
            send = partial(post, api_key(provider), provider=provider, record_transport=True)
        api = Model(model, effort, ledger, provider=provider, send=send, instructions=INSTRUCTIONS,
                    max_output_tokens=MAX_OUTPUT_TOKENS, record_exchanges=True)
        names = list(template["members"])
        schema = coordinator_schema(names)

        def parse_tasks(text):
            value = check_fields(json.loads(text), schema)
            tasks = value["tasks"]
            if len(tasks) != len(names) or {t["member"] for t in tasks} != set(names):
                raise ValueError("coordinator must assign each frozen member exactly once")
            if any(not t["task"].strip() or len(t["task"]) > TASK_LIMIT for t in tasks):
                raise ValueError("coordinator task is empty or too long")
            return {t["member"]: t["task"] for t in tasks}

        tasks = ask("coordinator", {"role": "coordinator", "task": task,
                    "members": authority(template)["members"], "skills": DESCRIPTIONS,
                    "previous_graphs": {n: m["controller"]["graph"]
                                        for n, m in parent["members"].items()} if parent else None,
                    "reply": "Assign exactly one short task per member; return tasks."},
                    schema, parse_tasks)
        candidate = deepcopy(template)

        def parse_graph(text):
            value = check_fields(json.loads(text), GRAPH_REPLY)
            return graph.validate(json.loads(value["graph_json"]))

        for name in names:
            spec = ask(name, {"role": "specialist", "member": name, "task": tasks[name],
                       "library": library, "ownership": authority(template)["members"][name],
                       "previous_graph": parent["members"][name]["controller"]["graph"]
                       if parent else None, "public_feedback": feedback.get(name),
                       "reply": "Return graph_json containing the complete graph JSON."},
                       GRAPH_REPLY, parse_graph)
            candidate["members"][name]["controller"] = {"type": "graph", "graph": spec}
        write_json(output / "controller.json", candidate)
        manifest.update(status="ready", controller_sha256=sha256(output / "controller.json"),
                        graphs={n: graph.digest(m["controller"]["graph"])
                                for n, m in candidate["members"].items()})
        return manifest
    except Exception as exc:
        manifest.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        manifest["totals"] = dict(api.totals) if api is not None else {}
        write_json(output / "manifest.json", manifest)
