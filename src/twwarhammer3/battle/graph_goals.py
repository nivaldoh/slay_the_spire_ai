"""A background target preference over an independently running frozen graph.

Worker/caller separation follows WH3's CommanderPolicy; scoped producer identities
follow graph-as-policy gap/runtime/executor.py at 71549e1. No donor code. A goal
request is its own live run, separate from the graph's advancing action node.
"""

import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Event
from uuid import uuid4

from gameai.ledger import BudgetExhausted
from gameai.llm import APIError, InvalidReply, check_fields
from gameai.provenance import REPO_ROOT
from twwarhammer3.battle import graph
from twwarhammer3.battle import skill_contracts as catalog
from twwarhammer3.battle.llm import invalid_reply

VERSION = "wh3-graph-goals-v1"
PROMPT_PATH = REPO_ROOT / "configs/twwarhammer3/graph_goal_prompt.md"
# JUDGEMENT: G4 Goal limits — Codex, 2026-11-01, delegated starting values: query every
# 30 battle seconds, reuse eligible hints for 60 s, one request/member, 30 s per read,
# no parse repairs. Different cadence/lifetimes/retries or preemption changes tactics/cost.
QUERY_MS = 30000
HINT_MS = 60000
READ_TIMEOUT_S = 30
MAX_OUTPUT_TOKENS = 2048
REASON_LIMIT = 200
SOURCE_FIELDS = ("producer", "controller", "battle", "graph_sha256", "seq", "time_ms", "owned")


def validate_graph(spec):
    spec = graph.validate(spec)
    if not any(node["op"] == "select_target" for node in spec["nodes"].values()):
        raise ValueError("graph_llm needs a select_target node")
    return spec


class GraphGoals:
    """Keep graph actions running while a model proposes a target for future selection."""

    timing = "asynchronous"

    def __init__(self, spec, api, *, task="", stop=None, max_requests=None):
        spec = validate_graph(spec)
        if max_requests is not None and (type(max_requests) is not int or max_requests <= 0):
            raise ValueError("max_requests must be positive or null")
        if not isinstance(task, str):
            raise ValueError("goal task must be text")
        self.api, self.task, self.max_requests = api, task, max_requests
        self.controller = uuid4().hex
        self.graph = graph.GraphPolicy(spec, target_preference=self.preference)
        self.parent_stop, self.stopped = stop or Event(), Event()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.pending = self.live_run = self.hint = self.latest = self.last_query_ms = None
        self.counter, self.shutdown = 0, False
        self.events, self.counts = [], Counter()
        send = api.send

        def guarded(body):
            if self.stopped.is_set() or self.parent_stop.is_set() or self.live_run is None:
                raise APIError("graph goal controller closed; request not sent")
            return send(body)

        api.send = guarded
        self.card = {**self.graph.card, "goal_version": VERSION,
                     "goal_controller": self.controller, "paid_calls": True,
                     "planner": {"model": api.name, "effort": api.effort,
                                 "provider": api.provider, "task": task,
                                 "ledger": str(api.ledger.path.resolve()),
                                 "max_requests": max_requests, "query_ms": QUERY_MS,
                                 "hint_ms": HINT_MS, "read_timeout_s": READ_TIMEOUT_S}}

    @property
    def totals(self):
        return {**self.api.totals, **self.counts}

    def _event(self, event, request=None, **fields):
        self.events.extend(self.graph.drain_events())
        source = deepcopy(request or self._source(self.latest))
        self.events.append({"event": event, "graph_sha256": self.graph.revision,
                            "node": "goal_request", "node_run": source.get("node_run"),
                            "source": source, **fields})

    def _source(self, view):
        if view is None:
            return {"producer": "goal_request", "controller": self.controller,
                    "graph_sha256": self.graph.revision}
        return {"producer": "goal_request", "controller": self.controller,
                "graph_sha256": self.graph.revision,
                "battle": view["battle"], "seq": view["seq"], "time_ms": view["time_ms"],
                "owned": sorted(u["id"] for u in view["friendly"])}

    def candidates(self, view):
        if not any(catalog.available(u) for u in view["friendly"]):
            return []
        engaged_only = all(node.get("mode") == "engaged" for node in self.graph.spec[
            "nodes"].values() if node["op"] == "select_target")
        return sorted(u["id"] for u in view["enemy"] if catalog.available(u)
                      and (not engaged_only or "melee" in u.get("state", [])))

    def _scope_error(self, source, view):
        if self.stopped.is_set() or self.parent_stop.is_set() or self.graph.closed:
            return "controller closed"
        if source.get("controller") != self.controller or source.get(
                "graph_sha256") != self.graph.revision:
            return "different controller or graph"
        if source.get("battle") != view["battle"]:
            return "different battle"
        if source.get("owned") != sorted(u["id"] for u in view["friendly"]):
            return "ownership context changed"
        if (view["seq"] < source["seq"] or view["time_ms"] < source["time_ms"]
                or view["time_ms"] - source["time_ms"] >= HINT_MS):
            return "goal source expired or is newer than the view"
        return None

    def preference(self, view):
        if self.hint is None:
            return None
        reason = self._scope_error(self.hint["source"], view)
        if not reason and self.hint["target"] not in self.candidates(view):
            reason = "preferred target is no longer eligible"
        if reason:
            self._event("goal_expired", self.hint["source"], reason=reason)
            self.hint = None
        return deepcopy(self.hint)

    def _ask(self, prompt, candidates):
        schema = {"type": "object", "properties": {
            "target": {"type": "string", "enum": ["none", *candidates]},
            "reason": {"type": "string"}},
            "required": ["target", "reason"],
            "additionalProperties": False}

        def parse(text):
            reply = check_fields(json.loads(text), schema)
            if (reply["target"] not in ("none", *candidates)
                    or len(reply["reason"]) > REASON_LIMIT):
                raise ValueError("choose a supplied target or none, with a short reason")
            return reply

        return self.api.ask(prompt, schema, parse, retries=0)

    def _read_reply(self, future):
        try:
            return future.result()
        except InvalidReply as exc:
            raise invalid_reply(exc) from None

    def _collect(self, view, *, closing=False):
        if self.pending is None or not self.pending[1].done():
            return
        from twwarhammer3.battle.play import is_forfeit, policy_call

        request, future = self.pending
        self.pending = None
        scope_error = self._scope_error(request, view)
        if not scope_error and request["node_run"] != self.live_run:
            scope_error = "goal request was cancelled or superseded"
        self.live_run = None
        if future.cancelled():
            self._event("goal_discarded", request, reason="cancelled before execution")
            return
        try:
            reply, _ = policy_call(self, "_read_reply", future)
        except Exception as exc:
            self._event("goal_failed", request, error_type=type(exc).__name__, error=str(exc))
            self.counts["goal_failures"] += 1
            if ((closing or scope_error) and not isinstance(exc, BudgetExhausted)
                    and is_forfeit(exc)):
                return
            raise
        reason = scope_error
        if (not reason and reply["target"] != "none"
                and reply["target"] not in self.candidates(view)):
            reason = "reply target is no longer eligible"
        if reason:
            self._event("goal_discarded", request, reason=reason)
            self.counts["goals_discarded"] += 1
            return
        self.hint = ({"target": reply["target"], "reason": reply["reason"],
                      "source": {key: request[key] for key in (*SOURCE_FIELDS, "node_run")}}
                     if reply["target"] != "none" else None)
        self._event("goal_adopted", request, target=reply["target"], reason=reply["reason"])
        self.counts["goals_adopted"] += 1

    def decide(self, observation):
        if self.latest is not None and observation["battle"] != self.latest["battle"]:
            self.stopped.set()
            self.live_run = None
            return self.graph.decide(observation)  # existing fresh-episode refusal
        if self.latest is not None and observation["seq"] <= self.latest["seq"]:
            return []
        self.latest = graph.public_view(observation)
        if observation.get("phase") != "Deployed" or observation.get("result"):
            self.stopped.set()
            self.live_run = None
        self.preference(self.latest)
        if self.pending is not None and self.live_run is not None:
            if reason := self._scope_error(self.pending[0], self.latest):
                self.live_run = None
                self._event("goal_cancelled", self.pending[0], reason=reason)
        self._collect(self.latest, closing=self.stopped.is_set())
        candidates = self.candidates(self.latest)
        if (not self.stopped.is_set() and not self.parent_stop.is_set() and not self.graph.closed
                and self.pending is None and candidates
                and (self.max_requests is None or self.counter < self.max_requests)
                and (self.last_query_ms is None
                     or self.latest["time_ms"] - self.last_query_ms >= QUERY_MS)):
            self.counter += 1
            self.live_run = self.counter
            request = {**self._source(self.latest), "node_run": self.counter}
            prompt = json.dumps({"task": self.task, "goal_source": request,
                                 "reason_limit": REASON_LIMIT,
                                 "candidates": candidates, "observation": self.latest,
                                 "graph": self.graph.spec}, sort_keys=True, allow_nan=False)
            self._event("goal_requested", request, candidates=candidates)
            self.last_query_ms = self.latest["time_ms"]
            self.pending = (request, self.pool.submit(self._ask, prompt, candidates))
        orders = self.graph.decide(observation)
        if self.graph.closed:
            self.stopped.set()
            self.live_run = None
        return orders

    def dispatch_guard(self, orders, observation):
        return self.graph.dispatch_guard(orders, observation)

    def acknowledge(self, ack, latency):
        self.graph.acknowledge(ack, latency)

    def metadata(self):
        return {**self.graph.metadata(), "type": "graph_llm", "model": self.api.name,
                "effort": self.api.effort, "target_preference": deepcopy(self.hint)}

    def drain_events(self):
        self.events.extend(self.graph.drain_events())
        events, self.events = self.events, []
        return events

    def close(self):
        if self.shutdown:
            return
        self.stopped.set()
        self.live_run = None
        self.graph.close()
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.shutdown = True
        if self.latest is not None:
            self._collect(self.latest, closing=True)
        self._event("goal_controller_closed")
