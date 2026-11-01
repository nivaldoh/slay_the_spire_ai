"""A resumable, declarative WH3 graph controller; one active node per member.

Reference: graph-robots/graph-as-policy gap/runtime/{workflow,validate,executor}.py
at 71549e1. Typed references and named exits follow that design; WH3 advances
independently on observations rather than waiting for super-steps. No donor code.
Graphs contain data only: no imports, scripts, expressions or arbitrary tools.
"""

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from gameai.provenance import sha256
from twwarhammer3.battle import skill_contracts as catalog
from twwarhammer3.battle import skills, team
from twwarhammer3.protocol import IllegalActionError, PolicyFailure

VERSION = "wh3-graph-v1"
# JUDGEMENT: G4 Graph limits — Codex, 2026-10-31, delegated baseline: one transition per
# observation, 10000 visits/node and 5 s order age; exhaustion sends nothing. More work,
# older orders or longer loops change reaction time and the duration of repeated tactics.
MAX_VISITS = 10000
MAX_AGE_MS = 5000


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _walk(nodes, start, blocked=None):
    seen, pending = set(), [start]
    while pending:
        name = pending.pop()
        if name in seen or name == blocked:
            continue
        seen.add(name)
        pending.extend(nodes[name]["next"].values())
    return seen


def validate(spec):
    """Reject unknown operations, exits, types and references lacking a producer path."""
    def require(ok, message):
        if not ok:
            raise ValueError(f"graph: {message}")

    require(isinstance(spec, dict) and set(spec) == {"version", "entry", "nodes"},
            "expected version, entry and nodes")
    require(spec["version"] == VERSION, "unsupported version")
    nodes = spec["nodes"]
    require(isinstance(nodes, dict) and 0 < len(nodes) <= 100, "expected 1–100 nodes")
    require(isinstance(spec["entry"], str) and spec["entry"] in nodes, "missing entry node")
    for name, node in nodes.items():
        require(isinstance(name, str) and name and "." not in name, "invalid node name")
        require(isinstance(node, dict) and set(node) <= {
            "op", "inputs", "next", "mode", "timeout_ms", "max_visits"}, f"{name}: unknown fields")
        op = node.get("op")
        require(isinstance(op, str) and op in catalog.CONTRACTS, f"{name}: unknown operation")
        contract = catalog.CONTRACTS[op]
        require(isinstance(node.get("inputs"), dict)
                and set(node["inputs"]) == set(contract["inputs"]), f"{name}: input fields")
        require(isinstance(node.get("next"), dict)
                and set(node["next"]) == set(contract["exits"]), f"{name}: exit fields")
        require(all(isinstance(n, str) and n in nodes for n in node["next"].values()),
                f"{name}: missing successor")
        require("mode" not in node or (op == "select_target"
                and node["mode"] in ("nearest", "engaged")), f"{name}: target mode")
        for key in ("timeout_ms", "max_visits"):
            require(key not in node or (type(node[key]) is int and node[key] > 0),
                    f"{name}: {key} must be a positive integer")
        require("timeout_ms" not in node or op in skills.RULES, f"{name}: timeout on non-skill")
    require(_walk(nodes, spec["entry"]) == set(nodes), "unreachable nodes")
    for name, node in nodes.items():
        for key, value in node["inputs"].items():
            kind = catalog.CONTRACTS[node["op"]]["inputs"][key]
            if isinstance(value, dict) and set(value) == {"ref"}:
                require(isinstance(value["ref"], str) and value["ref"].count(".") == 1,
                        f"{name}: invalid reference")
                producer, field = value["ref"].split(".")
                require(producer in nodes and producer != name, f"{name}: unknown producer")
                outputs = catalog.CONTRACTS[nodes[producer]["op"]]["outputs"]
                require(outputs.get(field) == kind, f"{name}: reference type mismatch")
                require(name not in _walk(nodes, spec["entry"], blocked=producer),
                        f"{name}: producer is not on every input path")
                # Only successful selector exits publish values. A failed selection must
                # pass through that producer again before a consumer can use its output.
                empty = nodes[producer]["next"].get("empty")
                require(empty is None or name not in _walk(nodes, empty, blocked=producer),
                        f"{name}: input may be absent after empty selection")
            else:
                require(catalog.valid_value(value, kind), f"{name}: invalid {kind} literal")
    return deepcopy(spec)


def public_view(observation):
    """Allowlist projection, including allies when already running as a member."""
    owned = {u["id"] for u in observation.get("friendly", [])}
    combined = {**observation, "friendly": observation.get("friendly", [])
                + observation.get("allies", [])}
    return team.project(combined, owned)


class GraphPolicy:
    """A frozen graph with fresh node runs and effect witnesses for each episode."""

    timing = "asynchronous"

    def __init__(self, spec):
        self.spec = validate(spec)
        self.revision = digest(self.spec)
        self.card = {"graph": self.spec, "graph_sha256": self.revision,
                     "catalog": catalog.VERSION, "catalog_sha256": sha256(Path(catalog.__file__)),
                     "tactics_sha256": sha256(Path(skills.__file__)), "max_age_ms": MAX_AGE_MS}
        self.node = self.spec["entry"]
        self.battle = self.seq = None
        self.run = None
        self.visits = Counter()
        self.values, self.events = {}, []
        self.last_consumed = {}
        self.closed = False
        self.behavior = {"type": "graph", "graph_sha256": self.revision}
        self.source = None

    def _event(self, event, **fields):
        self.events.append({"event": event, "graph_sha256": self.revision,
                            "node": self.node, "node_run": self.visits[self.node],
                            "source": deepcopy(self.source), **fields})

    def drain_events(self):
        events, self.events = self.events, []
        return events

    def _inputs(self, node):
        result, sources = {}, {}
        for key, value in node["inputs"].items():
            if isinstance(value, dict) and set(value) == {"ref"}:
                ref = value["ref"]
                record = self.values.get(ref)
                consumed = self.last_consumed.get((self.node, ref), 0)
                if record is None or record["node_run"] <= consumed:
                    raise PolicyFailure(f"graph {self.node}: missing or stale input {ref}")
                result[key], sources[key] = deepcopy(record["value"]), deepcopy(record)
                self.last_consumed[self.node, ref] = record["node_run"]
            else:
                result[key] = deepcopy(value)
        return result, sources

    def _finish(self, status, outputs=None, witness=None):
        for key, value in (outputs or {}).items():
            self.values[f"{self.node}.{key}"] = {
                "value": deepcopy(value), "producer": self.node,
                "node_run": self.visits[self.node], "graph_sha256": self.revision,
                **self.source}
        self._event("transition", status=status, outputs=outputs or {}, witness=witness,
                    successor=self.spec["nodes"][self.node]["next"][status])
        self.behavior.update(status=status, witness=witness)
        self.node = self.spec["nodes"][self.node]["next"][status]
        self.run = None

    def decide(self, observation):
        if self.closed:
            return []
        if self.battle is not None and observation["battle"] != self.battle:
            raise PolicyFailure("graph received a different battle; construct a fresh controller")
        self.battle = observation["battle"]
        if observation.get("phase") != "Deployed" or observation.get("result"):
            self.close()
            return []
        if self.seq is not None and observation["seq"] <= self.seq:
            return []
        self.seq = observation["seq"]
        view = public_view(observation)
        self.source = {"battle": self.battle, "seq": self.seq, "time_ms": view["time_ms"]}
        node = self.spec["nodes"][self.node]
        op = node["op"]
        self.behavior = {"type": "graph", "graph_sha256": self.revision, "node": self.node,
                         "status": "running", "source_seq": self.seq,
                         "source_ms": view["time_ms"]}
        if self.run is None:
            self.visits[self.node] += 1
            if self.visits[self.node] > node.get("max_visits", MAX_VISITS):
                self._event("exhausted")
                self.close()
                return []
            # Re-entering a producer invalidates its previous output immediately.
            for field in catalog.CONTRACTS[op]["outputs"]:
                self.values.pop(f"{self.node}.{field}", None)
            inputs, sources = self._inputs(node)
            self._event("started", op=op, inputs=inputs, input_sources=sources)
            if op in skills.RULES:
                self.run = catalog.SkillRun(op, inputs, view["time_ms"],
                                            node.get("timeout_ms", catalog.TIMEOUT_MS))
            elif op == "end":
                self.close()
                return []
            elif op == "owned":
                units = [u["id"] for u in view["friendly"] if catalog.available(u)]
                self._finish("succeeded" if units else "empty", {"units": units} if units else {})
                return []
            elif op == "contact":
                self._finish("yes" if catalog.public_contact(view) else "no")
                return []
            elif op == "select_target":
                units = [u for u in view["friendly"] if u["id"] in inputs["units"]
                         and catalog.available(u)]
                enemies = [u for u in view["enemy"] if catalog.available(u)
                           and (node.get("mode") != "engaged" or "melee" in u.get("state", []))]
                # JUDGEMENT: G4 Target choice — Codex, 2026-10-31: nearest eligible visible
                # enemy, ties by ID; prioritizing lords or weak units changes the policy.
                # Initial graph behavior rests on this delegated baseline.
                target = min(enemies, key=lambda e: (min(skills.distance(u, e) for u in units),
                                                     e["id"]), default=None) if units else None
                self._finish("succeeded" if target else "empty",
                             {"target": target["id"]} if target else {})
                return []
        status, orders, witness = self.run.tick(view)
        if status != "running":
            self._finish(status, witness=witness)
        return orders

    def dispatch_guard(self, orders, observation):
        """Called only at team dispatch: preserve the decision's original identity and age."""
        if not orders:
            return
        if self.closed or observation["battle"] != self.battle:
            raise IllegalActionError("graph no longer owns this battle")
        if observation["time_ms"] - self.source["time_ms"] >= MAX_AGE_MS:
            raise IllegalActionError("graph orders expired")
        if self.run is None:
            raise IllegalActionError("graph node run already finished")
        self.run.guard(orders, public_view(observation))

    def acknowledge(self, ack, latency):
        if self.run is not None:
            self.run.acknowledge(ack)
        self._event("feedback", ack=deepcopy(ack), latency=dict(latency))

    def metadata(self):
        return deepcopy(self.behavior)

    def close(self):
        if not self.closed:
            if self.run is not None:
                self.run.cancel()
                self._event("cancelled", reason=self.run.reason)
            self._event("closed", unsent_node=self.node)
        self.closed = True
