"""Five Cannae command groups using the existing asynchronous team/mailbox loop.

Reference: SMAC smac/env/starcraft2/starcraft2.py get_obs_agent separates local sensing
from shared state. Scheduling remains TeamPolicy's real-time independent worker model.
"""

import hashlib
import json
from collections import deque
from copy import deepcopy

from gameai.llm import InvalidReply, check_fields
from gameai.provenance import REPO_ROOT, sha256
from twwarhammer3.battle import llm
from twwarhammer3.battle import local_command as local
from twwarhammer3.battle.scripted import RushNearest
from twwarhammer3.battle.team import TeamHarnessError, TeamPolicy
from twwarhammer3.protocol import validate_orders

PROMPT_PATH = REPO_ROOT / "configs/twwarhammer3/local_command_prompt.md"
PLAN_PATH = PROMPT_PATH.with_name("cannae_shared_plan.md")
INPUT_VERSION = "local-command-v1"
ARMS = {"bounded": ("local", "bounded"), "silent": ("local", "none"),
        "fast": ("local", "fast"), "global": ("global", "none")}
# JUDGEMENT: Member message batch — Codex, 2026-11-05: at most two sends per reply,
# without tactical interpretation or automatic retries. Larger batches alter effective
# communication capacity and preparation cost; C's comparisons rest on this bound.
MAX_MESSAGES = 2


def declaration(scenario):
    profile = scenario.get("communication") or {}
    if profile.get("version") != 1 or profile.get("arm") not in ARMS:
        raise ValueError("local team requires a declared C communication arm")
    if scenario.get("reserve") or scenario.get("custom"):
        raise ValueError("C uses native AI without a custom objective or reserve intervention")
    return profile["arm"]


def validate_config(scenario, config):
    """A C declaration cannot silently use a global single-controller interface."""
    if not scenario.get("communication"):
        return
    declaration(scenario)
    from twwarhammer3.battle import controllers

    for name in config["policy"].split(","):
        base = controllers.policy_parts(name, config)[0]
        if base == "configured":
            from twwarhammer3.battle.configured import load

            node = load(config["controller_config"], config)[0]
            if node["type"] == "local_team":
                continue
        elif base not in controllers.MODEL_POLICIES:
            if issubclass(controllers.controller_class(name), LocalTeam):
                continue
        raise ValueError("C requires a local_team composition or LocalTeam adapter")


class LocalTeam(TeamPolicy):
    """Exclusive regiment ownership, local sensing and copied messages; no team barrier."""

    def __init__(self, policies, *, scenario, **options):
        if set(policies) != set(local.GROUP_SLOTS):
            raise TeamHarnessError("C requires its five fixed command groups")
        self.arm = declaration(scenario)
        self.placements = deepcopy(scenario["deployment"]["friendly"])
        self.plan = PLAN_PATH.read_text()
        self.groups = None
        self.types = None
        self.roster = None
        self.router = None
        self.current = {}
        self.now = None
        self.acceptances = {name: [] for name in policies}
        self.last_mail = {name: {"received": [], "send_feedback": []} for name in policies}
        # Empty type declarations deliberately defer binding to this subclass's authored
        # identity partition; optional permits five workers, not runtime group removal.
        super().__init__({name: ((), policy) for name, policy in policies.items()},
                         optional=True, army_owner=None,
                         max_age_ms=options.pop("max_age_ms", None), **options)
        self.card.update(input_version=INPUT_VERSION, partition="fixed authored regiment slots",
                         group_slots=local.GROUP_SLOTS, communication_arm=self.arm,
                         sensing="anchor radius" if self.arm != "global" else "alliance contacts",
                         plan_sha256=sha256(PLAN_PATH),
                         profile={**local.PROFILE, **local.FAST_PROFILE},
                         max_messages=MAX_MESSAGES, army_owner=None)

    def _partition(self, observation):
        roster = observation.get("friendly")
        if (not isinstance(roster, list) or any(not isinstance(u, dict) or not u.get("id")
                                               or u.get("error") for u in roster)):
            self._fault("local command received an incomplete friendly roster")
        if self.battle is None:
            self.groups = local.bind(self.placements, roster)
            self.types = {u["id"]: u["type"] for u in roster}
            self.battle = observation["battle"]
            self.roster = [local.fields(u, ("id", "type", "alliance"))
                           for u in observation.get("enemy_roster", [])]
            for name, identities in self.groups.items():
                self.members[name].units = frozenset(identities)
            rendezvous = {name: {key: self.placements[local.GROUP_SLOTS[name][0]][key]
                                  for key in ("x", "z")} for name in self.groups}
            self.router = local.Router(rendezvous, mode=ARMS[self.arm][1])
            self._event("partition", battle=self.battle, ownership=deepcopy(self.groups),
                        input_version=INPUT_VERSION, communication_arm=self.arm)
        expected = {identity for identities in self.groups.values() for identity in identities}
        if (observation["battle"] != self.battle or len(roster) != len(expected)
                or {u["id"]: u.get("type") for u in roster} != self.types):
            self._fault("local command battle or regiment identity changed")
        self.now = observation["time_ms"]
        self.current = local.anchors(observation, self.groups)
        self.router.advance(self.now, self.current)
        self._mail_events()

    def _mail_events(self):
        for record in self.router.drain_events():
            self._event("communication", record=record, time_ms=self.now)

    def _view(self, observation, member, *, army=False, for_input=False):
        name = next(name for name, row in self.members.items() if row is member)
        view = local.project(observation, member.units, self.current[name], self.roster,
                             global_view=self.arm == "global")
        if for_input and any(u.get("men", 0) > 0 for u in view["friendly"]):
            self.last_mail[name] = {"received": self.router.inbox(name),
                                    "send_feedback": deepcopy(self.acceptances[name])}
            self.router.inboxes[name].clear()
            self.acceptances[name].clear()
        view["command"] = {"member": name, "groups": deepcopy(self.groups),
                           "plan": self.plan, "arm": self.arm,
                           "rendezvous": deepcopy(self.router.rendezvous),
                           "rules": {**self.router.profile, "codes": local.CODES,
                                     "max_messages": MAX_MESSAGES,
                                     "channel_mode": ARMS[self.arm][1]},
                           **deepcopy(self.last_mail[name])}
        return view

    def _work(self, member, observation):
        result = super()._work(member, observation)
        drain = getattr(member.policy, "drain_messages", None)
        messages = drain() if drain else []
        if (not isinstance(messages, list) or len(messages) > MAX_MESSAGES
                or any(not isinstance(message, dict) for message in messages)):
            raise ValueError("member messages must be a bounded list of objects")
        result["messages"] = deepcopy(messages)
        return result

    def _validate(self, member, observation):
        super()._validate(member, observation)
        # JUDGEMENT: Local target authority — Codex, 2026-11-05: new orders must be legal
        # in both source and latest local views; existing engine orders persist normally.
        # Alliance-wide stale-id probes differ and can disclose distant condition via errors.
        validate_orders(member.ready["orders"], self._view(observation, member))

    def _collect(self, name, member):
        super()._collect(name, member)
        if member.ready is None:
            return
        for message in member.ready.get("messages", []):
            if self.closed:
                self._event("message_discarded", name, reason="episode_closed", message=message)
                continue
            ack = self.router.send(name, message, self.now, self.current,
                                   source_ms=member.call["source_ms"])
            self.acceptances[name].append(ack)
        self._mail_events()


def reply_schema(provider="openai"):
    def message(**properties):
        return {"type": "object", "properties": properties, "required": list(properties),
                "additionalProperties": False}

    schema = deepcopy(llm.REPLY_SCHEMA)
    schema["properties"]["messages"] = {"type": "array", "maxItems": MAX_MESSAGES,
        "items": {"anyOf": [
            message(channel={"type": "string", "enum": ["signal"]},
                    code={"type": "string", "enum": list(local.CODES)}),
            message(channel={"type": "string", "enum": ["courier", "text"]},
                    to={"type": "string"}, text={"type": "string"}),
            message(channel={"type": "string", "enum": ["courier"]}, to={"type": "string"},
                    relay=message(sender={"type": "string"}, send={"type": "integer"})),
        ]}}
    schema["required"].append("messages")
    if provider == "anthropic":
        # Claude's structured-output subset rejects maxItems. The parser and dispatcher
        # still enforce MAX_MESSAGES; this changes only the accepted wire schema.
        # https://platform.claude.com/docs/en/build-with-claude/structured-outputs
        schema["properties"]["messages"].pop("maxItems")
    return schema


class LocalModel:
    """One model member with bounded private memory; no global tactical executor."""

    def __init__(self, policy):
        self.api = policy.api
        self.api.instructions += "\n\n" + PROMPT_PATH.read_text()
        self.totals = self.api.totals
        self.notes, self.messages = "", []
        self.history = deque(maxlen=llm.HISTORY_LENGTH)
        self.feedback = None
        self.behavior = {}

    def decide(self, observation):
        prompt = json.dumps({"observation": observation, "notes": self.notes,
                             "history": list(self.history), "order_feedback": self.feedback},
                            sort_keys=True, ensure_ascii=True)
        self.behavior = {"type": "local_model", "prompt": prompt,
                         "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                         "model": self.api.name, "effort": self.api.effort}

        schema = reply_schema(self.api.provider)

        def parse(text):
            value = check_fields(json.loads(text), schema)
            messages = value.pop("messages")
            if (not isinstance(messages, list) or len(messages) > MAX_MESSAGES
                    or any(not isinstance(m, dict) for m in messages)):
                raise ValueError("messages must be a bounded list of objects")
            reply = llm.parse_reply(json.dumps(value), observation)
            return {**reply, "messages": messages}

        try:
            # No partial-order salvage: the local decision and its messages form one reply.
            reply, attempts = self.api.ask(prompt, schema, parse, 0)
        except InvalidReply as error:
            raise llm.invalid_reply(error) from None
        self.messages = deepcopy(reply["messages"])
        if reply["notes"] is not None:
            self.notes = reply["notes"][:llm.NOTES_LIMIT]
        self.history.append({"time_ms": observation["time_ms"], "orders": reply["orders"],
                             "messages": reply["messages"],
                             "reason": reply["reason"][:llm.REASON_LIMIT]})
        self.behavior.update(reason=reply["reason"], attempts=attempts, notes=self.notes)
        return reply["orders"]

    def drain_messages(self):
        messages, self.messages = self.messages, []
        return messages

    def acknowledge(self, ack, latency):
        self.feedback = {"ack": deepcopy(ack), "latency": dict(latency)}

    def metadata(self):
        return deepcopy(self.behavior)


class ProbeMember(RushNearest):
    """Channel probe; one courier releases left infantry into a diagnostic move."""

    def __init__(self):
        super().__init__()
        self.sent = False
        self.messages = []
        self.probe_cue = None
        self.probe_destination = None

    def decide(self, observation):
        name = observation["command"]["member"]
        if not self.sent:
            peer = "left_infantry" if name == "centre" else "centre"
            self.messages = [{"channel": "signal", "code": "READY"},
                             {"channel": "courier", "to": peer, "text": "At initial position."}]
            self.sent = True
            return []
        if name == "left_infantry":
            if self.probe_cue is None:
                courier = next((m for m in observation["command"]["received"]
                                if m["sender"] == "centre" and m["channel"] == "courier"), None)
                if courier is None:
                    return []
                self.probe_cue = deepcopy(courier)
                home = observation["command"]["rendezvous"][name]
                # JUDGEMENT: Message effect probe — Codex, 2026-11-05: receipt releases
                # one 40 m eastward move from the known home. Another distance or trigger
                # changes this diagnostic; it supports no tactical-benefit comparison.
                self.probe_destination = {"x": home["x"] + 40, "z": home["z"]}
                return [{"unit": observation["friendly"][0]["id"], "type": "move",
                         **self.probe_destination, "run": True}]
            if local.distance(observation["friendly"][0], self.probe_destination) > llm.ARRIVED_M:
                return []
        return super().decide(observation)

    def drain_messages(self):
        messages, self.messages = self.messages, []
        return messages

    def metadata(self):
        return {"type": "local_channel_probe", "cue": deepcopy(self.probe_cue),
                "probe_destination": deepcopy(self.probe_destination)}


class ProbeTeam(LocalTeam):
    """Free C interface probe; local nearest attacks, without a communication-benefit claim."""

    def __init__(self, *, scenario, **options):
        super().__init__({name: ProbeMember() for name in local.GROUP_SLOTS},
                         scenario=scenario, **options)
