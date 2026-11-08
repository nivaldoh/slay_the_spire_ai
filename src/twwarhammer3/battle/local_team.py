"""Five Cannae command groups using the existing asynchronous team/mailbox loop.

Reference: SMAC smac/env/starcraft2/starcraft2.py get_obs_agent separates local sensing
from shared state. Scheduling remains TeamPolicy's real-time independent worker model.
Communication declaration version 2 (docs/twwarhammer3/communication-structure.md) has one
text channel on fixed links: captains message each other (peer) or only a sixth member, the
commander, who owns no regiments (relay, overview). Three controls: muted and muted_overview
are peer and overview with every accepted text dropped before delivery, and unlinked has no
links and no messages.
"""

import hashlib
import json
from collections import deque
from copy import deepcopy
from time import sleep

from gameai.llm import InvalidReply, check_fields
from gameai.provenance import REPO_ROOT, sha256
from twwarhammer3.battle import llm
from twwarhammer3.battle import local_command as local
from twwarhammer3.battle.scripted import RushNearest
from twwarhammer3.battle.team import TeamHarnessError, TeamPolicy
from twwarhammer3.protocol import PolicyFailure, validate_orders

PROMPT_PATH = REPO_ROOT / "configs/twwarhammer3/local_command_prompt.md"
PLAN_PATH = PROMPT_PATH.with_name("cannae_shared_plan.md")
INPUT_VERSION = "local-command-v1"
ARMS = {"bounded": ("local", "bounded"), "silent": ("local", "none"),
        "fast": ("local", "fast"), "global": ("global", "none")}
# Version 2: the arm's links, its plan, member prompts and rules sections.
TOPOLOGIES = {"peer": "mesh", "relay": "star", "overview": "star", "muted": "mesh",
              "muted_overview": "star", "unlinked": "none"}
# The muted arms and the arm each plays and shows its members: that arm's members, links,
# limits, views, command block and prompt, so neither an input nor an acknowledgement shows that
# their texts are dropped; only the router differs.
SHOWN_ARM = {"muted": "peer", "muted_overview": "overview"}
TOPOLOGY_INPUT = "local-command-v2"
COMMANDER = "commander"
PLAN_V2_PATH = PROMPT_PATH.with_name("cannae_shared_plan_v2.md")
CAPTAIN_PROMPT_PATH = PROMPT_PATH.with_name("local_captain_prompt.md")
COMMANDER_PROMPT_PATH = PROMPT_PATH.with_name("local_commander_prompt.md")
TOPOLOGY_RULES_PATH = PROMPT_PATH.with_name("local_topology_rules.json")
# Messages per completed decision, (min, max). Rests on JUDGEMENT
# `docs/twwarhammer3/communication-structure.md` Forcing rule.
MESSAGE_LIMITS = {"captain": (1, 2), "commander": (0, 5)}
# JUDGEMENT: Member message batch — Codex, 2026-11-05: at most two sends per reply,
# without tactical interpretation or automatic retries. Larger batches alter effective
# communication capacity and preparation cost; C's comparisons rest on this bound.
MAX_MESSAGES = 2


def declaration(scenario):
    profile = scenario.get("communication") or {}
    version = profile.get("version")
    if profile.get("arm") not in (ARMS if version == 1 else TOPOLOGIES if version == 2 else ()):
        raise ValueError("local team requires a declared C communication arm")
    if scenario.get("reserve") or scenario.get("custom"):
        raise ValueError("C uses native AI without a custom objective or reserve intervention")
    return profile["arm"]


def member_names(arm):
    """The members an arm needs: the five groups, plus the commander in a star."""
    return set(local.GROUP_SLOTS) | ({COMMANDER} if TOPOLOGIES.get(arm) == "star" else set())


def role(member):
    return "commander" if member == COMMANDER else "captain"


def links(arm):
    """A version 2 arm's directed (sender, recipient) links, in GROUP_SLOTS order."""
    captains = list(local.GROUP_SLOTS)
    if TOPOLOGIES[arm] == "none":
        return ()
    if TOPOLOGIES[arm] == "mesh":
        return tuple((a, b) for a in captains for b in captains if a != b)
    return tuple(link for name in captains for link in ((name, COMMANDER), (COMMANDER, name)))


def message_limits(arm, kind):
    """A version 2 role's (min, max) messages per completed decision; none when unlinked."""
    return (0, 0) if TOPOLOGIES[arm] == "none" else MESSAGE_LIMITS[kind]


def message_rules(arm, member):
    """A version 2 member's rules block: the text profile, its counts and recipients."""
    low, high = message_limits(arm, role(member))
    return {"channel_mode": "text", **local.TEXT_PROFILE, "min_messages": low,
            "max_messages": high, "recipients": [b for a, b in links(arm) if a == member]}


def member_prompt(arm, member):
    """What a LocalModel adds to its model's instructions: v1's prompt, or v2's role prompt
    and the arm's rules section for that role."""
    if arm not in TOPOLOGIES:
        return PROMPT_PATH.read_text()
    path = COMMANDER_PROMPT_PATH if member == COMMANDER else CAPTAIN_PROMPT_PATH
    rules = json.loads(TOPOLOGY_RULES_PATH.read_text())[SHOWN_ARM.get(arm, arm)]
    return path.read_text() + "\n" + rules[role(member)] + "\n"


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
        self.arm = declaration(scenario)
        self.shown = SHOWN_ARM.get(self.arm, self.arm)
        if set(policies) != member_names(self.arm):
            raise TeamHarnessError("C requires its five fixed command groups"
                                   + (" and the commander" if COMMANDER in member_names(self.arm)
                                      else ""))
        self.input_version = TOPOLOGY_INPUT if self.arm in TOPOLOGIES else INPUT_VERSION
        self.placements = deepcopy(scenario["deployment"]["friendly"])
        self.plan = (PLAN_V2_PATH if self.arm in TOPOLOGIES else PLAN_PATH).read_text()
        self.start_points = None
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
        # TeamPolicy skips a member with no living men unless it is the army owner, so the
        # commander, who owns no regiments, is named only so that it is asked.
        super().__init__({name: ((), policy) for name, policy in policies.items()},
                         optional=True, army_owner=COMMANDER if COMMANDER in policies else None,
                         max_age_ms=options.pop("max_age_ms", None), **options)
        self.card.update(input_version=INPUT_VERSION, partition="fixed authored regiment slots",
                         group_slots=local.GROUP_SLOTS, communication_arm=self.arm,
                         sensing="anchor radius" if self.arm != "global" else "alliance contacts",
                         plan_sha256=sha256(PLAN_PATH),
                         profile={**local.PROFILE, **local.FAST_PROFILE},
                         max_messages=MAX_MESSAGES, army_owner=None)
        if self.arm in TOPOLOGIES:
            roles = {key: message_limits(self.arm, key) for key in MESSAGE_LIMITS
                     if key == "captain" or COMMANDER in policies}
            self.card.update(
                input_version=TOPOLOGY_INPUT, topology=TOPOLOGIES[self.arm],
                links=[list(link) for link in links(self.arm)], plan_sha256=sha256(PLAN_V2_PATH),
                sensing={"peer": "anchor radius", "unlinked": "anchor radius",
                         "relay": "captains: anchor radius; commander: its inbox only",
                         "overview": "captains: anchor radius; commander: alliance contacts"
                         }[self.shown],
                profile=dict(local.TEXT_PROFILE),
                min_messages={key: low for key, (low, _) in roles.items()},
                max_messages={key: high for key, (_, high) in roles.items()},
                army_owner=self.army_owner)
            if COMMANDER in policies:
                self.card["army_owner_note"] = (
                    "names the commander only so that TeamPolicy asks it; C views carry no"
                    " army orders, and any commander order forfeits its reply")

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
            if self.arm in ARMS:
                self.router = local.Router(rendezvous, mode=ARMS[self.arm][1])
            else:
                self.start_points = deepcopy(rendezvous)
                if COMMANDER in self.members:
                    # A fixed endpoint, never an anchor for project; text needs no distance.
                    rendezvous[COMMANDER] = dict(rendezvous["centre"])
                self.router = local.Router(rendezvous, mode="text", links=links(self.arm),
                                           profile=local.TEXT_PROFILE,
                                           muted=self.arm in SHOWN_ARM)
            self._event("partition", battle=self.battle, ownership=deepcopy(self.groups),
                        input_version=self.input_version, communication_arm=self.arm)
        expected = {identity for identities in self.groups.values() for identity in identities}
        if (observation["battle"] != self.battle or len(roster) != len(expected)
                or {u["id"]: u.get("type") for u in roster} != self.types):
            self._fault("local command battle or regiment identity changed")
        self.now = observation["time_ms"]
        self.current = local.anchors(observation, self.groups)
        if COMMANDER in self.router.rendezvous:
            self.current[COMMANDER] = self.router.rendezvous[COMMANDER]
        self.router.advance(self.now, self.current)
        self._mail_events()

    def _mail_events(self):
        for record in self.router.drain_events():
            self._event("communication", record=record, time_ms=self.now)

    def _view(self, observation, member, *, army=False, for_input=False):
        name = next(name for name, row in self.members.items() if row is member)
        if self.arm in TOPOLOGIES:
            return self._topology_view(observation, name, for_input)
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

    def _topology_view(self, observation, name, for_input):
        """A version 2 input: a captain's local view, or the commander's with no units."""
        if name == COMMANDER:
            # Rests on JUDGEMENT `docs/twwarhammer3/communication-structure.md` Commander
            # information: no anchor, so relay sees no contacts; overview has the global view.
            view = local.project(observation, frozenset(), None, self.roster,
                                 global_view=self.shown == "overview", version=TOPOLOGY_INPUT)
        else:
            anchor = self.current[name]
            view = local.project(observation, self.members[name].units, anchor, self.roster,
                                 version=TOPOLOGY_INPUT)
        if for_input and (name == COMMANDER or any(u.get("men", 0) > 0 for u in view["friendly"])):
            self.last_mail[name] = {"received": self.router.inbox(name),
                                    "send_feedback": deepcopy(self.acceptances[name])}
            self.router.inboxes[name].clear()
            self.acceptances[name].clear()
        view["command"] = {"member": name, "arm": self.shown,
                           "topology": TOPOLOGIES[self.arm],
                           "groups": deepcopy(self.groups),
                           "start_points": deepcopy(self.start_points), "plan": self.plan,
                           "rules": message_rules(self.arm, name),
                           **deepcopy(self.last_mail[name])}
        return view

    def _work(self, member, observation):
        result = super()._work(member, observation)
        drain = getattr(member.policy, "drain_messages", None)
        messages = drain() if drain else []
        name = next(name for name, row in self.members.items() if row is member)
        if name == COMMANDER and result["orders"]:
            # A forfeit, as a model reply with an order is: neither orders nor messages are used.
            raise PolicyFailure("the commander owns no regiments; a reply with orders is void",
                                failure={"member": name, "kind": "commander_orders"})
        if self.arm in ARMS:
            low, high, error = 0, MAX_MESSAGES, "member messages must be a bounded list of objects"
        else:
            low, high = message_limits(self.arm, role(name))
            error = f"{name} must send {low} to {high} message objects per decision"
        if (not isinstance(messages, list) or not low <= len(messages) <= high
                or any(not isinstance(message, dict) for message in messages)):
            raise ValueError(error)
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
            if member.call is None and self.arm in TOPOLOGIES:
                # JUDGEMENT?: Forfeited mail — Claude, 2026-11-08, card D: a v2 forfeit returns
                # its input's mail and send feedback to the next input, oldest first; v1 drops them;
                # dropping hides reports a relay commander can get nowhere else; C v2 rests on it.
                self.router.inboxes[name][:0] = self.last_mail[name]["received"]
                self.acceptances[name][:0] = self.last_mail[name]["send_feedback"]
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


def text_schema(provider, rules):
    """Version 2's reply: text messages only, the member's recipients as an enum."""
    schema = deepcopy(llm.REPLY_SCHEMA)
    # No recipients (unlinked) leaves "to" free text, since an empty enum is no valid schema;
    # maxItems 0 (not on Anthropic) and the parser still refuse any message.
    to = ({"type": "string", "enum": rules["recipients"]} if rules["recipients"]
          else {"type": "string"})
    messages = {"type": "array", "items": {
        "type": "object", "properties": {"channel": {"type": "string", "enum": ["text"]},
                                         "to": to, "text": {"type": "string"}},
        "required": ["channel", "to", "text"], "additionalProperties": False}}
    if rules["min_messages"]:
        messages["minItems"] = rules["min_messages"]  # Anthropic accepts only 0 or 1
    if provider != "anthropic":  # Claude rejects maxItems; the parser checks it there
        messages["maxItems"] = rules["max_messages"]
    schema["properties"]["messages"] = messages
    schema["required"].append("messages")
    return schema


class LocalModel:
    """One model member with bounded private memory; no global tactical executor."""

    def __init__(self, policy, *, arm=None, member=None):
        self.api = policy.api
        self.api.instructions += "\n\n" + member_prompt(arm, member)
        self.member = member
        self.rules = message_rules(arm, member) if arm in TOPOLOGIES else None
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

        rules = self.rules
        schema = (reply_schema(self.api.provider) if rules is None
                  else text_schema(self.api.provider, rules))
        high = MAX_MESSAGES if rules is None else rules["max_messages"]

        def parse(text):
            value = check_fields(json.loads(text), schema)
            messages = value.pop("messages")
            if (not isinstance(messages, list) or len(messages) > high
                    or any(not isinstance(m, dict) for m in messages)):
                raise ValueError("messages must be a bounded list of objects")
            if rules is not None:
                if len(messages) < rules["min_messages"]:
                    raise ValueError(f"send at least {rules['min_messages']} message(s)")
                if any(m.get("channel") != "text" for m in messages):
                    raise ValueError("every message uses the text channel")
                if any(m.get("to") not in rules["recipients"] for m in messages):
                    raise ValueError("a message names a recipient outside your rules")
                if self.member == COMMANDER and value["orders"]:
                    raise ValueError("the commander owns no regiments; orders must be empty")
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


class TextProbeMember(RushNearest):
    """Version 2 channel probe for every captain: each reply sends one short status to an
    allowed recipient, the centre's to left infantry where it may. In a star, right infantry's
    first reply adds a text to left infantry, off its links, which the router must refuse.
    Left infantry holds until a message written by the centre reaches it (directly in peer, as
    the commander's forward in relay and overview), makes one 40 m east move from its start
    point, then rushes."""

    def __init__(self):
        super().__init__()
        self.messages = []
        self.probe_cue = None
        self.probe_destination = None
        self.replied = False

    def decide(self, observation):
        command = observation["command"]
        name, recipients = command["member"], command["rules"]["recipients"]
        to = ("left_infantry" if name == "centre" and "left_infantry" in recipients
              else recipients[0])
        self.messages = [{"channel": "text", "to": to,
                          "text": f"{name}: {len(observation['friendly'])} regiments,"
                                  f" {len(observation['enemy'])} enemies in view at"
                                  f" {observation['time_ms']} ms"}]
        if name == "right_infantry" and command["topology"] == "star" and not self.replied:
            self.messages.append({"channel": "text", "to": "left_infantry",
                                  "text": "right_infantry: off-link test"})
        self.replied = True
        if name != "left_infantry":
            return super().decide(observation)
        if self.probe_cue is None:
            cue = next((m for m in command["received"] if m["sender"] == "centre"
                        or m["sender"] == COMMANDER and m["text"].startswith("centre:")), None)
            if cue is None:
                return []
            self.probe_cue = deepcopy(cue)
            start = command["start_points"][name]
            # Rests on JUDGEMENT `src/twwarhammer3/battle/local_team.py` Message effect probe.
            self.probe_destination = {"x": start["x"] + 40, "z": start["z"]}
            return [{"unit": observation["friendly"][0]["id"], "type": "move",
                     **self.probe_destination, "run": True}]
        if local.distance(observation["friendly"][0], self.probe_destination) > llm.ARRIVED_M:
            return []
        return super().decide(observation)

    def drain_messages(self):
        messages, self.messages = self.messages, []
        return messages

    def metadata(self):
        return {"type": "local_text_probe", "cue": deepcopy(self.probe_cue),
                "probe_destination": deepcopy(self.probe_destination)}


class ProbeCommander:
    """Version 2 probe commander: forwards the centre's first message to left infantry
    unchanged and otherwise sends nothing; it never orders."""

    def __init__(self):
        self.messages = []
        self.forwarded = None

    def decide(self, observation):
        if self.forwarded is None:
            first = next((m for m in observation["command"]["received"]
                          if m["sender"] == "centre"), None)
            if first is not None:
                self.forwarded = deepcopy(first)
                self.messages = [{"channel": "text", "to": "left_infantry",
                                  "text": first["text"]}]
        return []

    def drain_messages(self):
        messages, self.messages = self.messages, []
        return messages

    def acknowledge(self, ack, latency):
        pass

    def metadata(self):
        return {"type": "local_probe_commander", "forwarded": deepcopy(self.forwarded)}


class ProbeTeam(LocalTeam):
    """Free C interface probe; local nearest attacks, without a communication-benefit claim."""

    def __init__(self, *, scenario, **options):
        super().__init__({name: ProbeMember() for name in local.GROUP_SLOTS},
                         scenario=scenario, **options)


class SlowProbeMember(ProbeMember):
    """Delay this worker only; the live C diagnostic checks peers and arriving mail."""

    def decide(self, observation):
        # JUDGEMENT: Slow member diagnostic — Codex, 2026-11-05: three seconds in one
        # worker creates an arrival-during-decision case. Other delays change that overlap;
        # this is a scheduling probe, never a model-latency or tactical-strength estimate.
        sleep(3)
        return super().decide(observation)
