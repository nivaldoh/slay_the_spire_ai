"""C's local sensing and messages, independent of the asynchronous dispatcher.

Reference: SMAC smac/env/starcraft2/starcraft2.py get_obs_agent separates local
observations from global state. This keeps WH3 running at 1x, rather than joint steps.
These are trusted adapters, not a sandbox for arbitrary Python/tool submissions.
"""

from copy import deepcopy
from math import hypot

from twwarhammer3.battle.team import ALLY_FIELDS, UNIT_FIELDS, TeamHarnessError

# JUDGEMENT: Local command development profile — Codex, 2026-11-05: local view 160 m,
# signal 220 m/2 s/5 s cooldown; courier 20 m/s + 2 s dispatch, two slots, 120 s lifetime,
# 30 m rendezvous and 240 UTF-8 bytes. Other limits change coordination; no readiness claim.
PROFILE = {"view_m": 160, "signal_m": 220, "signal_delay_ms": 2000,
           "signal_cooldown_ms": 5000, "courier_m_s": 20, "dispatch_ms": 2000,
           "courier_slots": 2, "lifetime_ms": 120000, "rendezvous_m": 30, "text_bytes": 240}
# JUDGEMENT: Fast text control — Codex, 2026-11-05: fast arm adds zero-delay addressed
# text (1024 UTF-8 bytes, 64 in-flight slots) to the bounded channels. Lower capacity or
# physical rendezvous changes the control; inference and observation scheduling still apply.
FAST_PROFILE = {"fast_delay_ms": 0, "fast_text_bytes": 1024, "fast_slots": 64}
# Version 2's only channel: addressed text on declared links, delivered at the next observation.
# Rests on JUDGEMENT `docs/twwarhammer3/communication-structure.md` Text channel (240 bytes from
# PROFILE, 64 slots from FAST_PROFILE, no added delay; signals and couriers off).
TEXT_PROFILE = {"text_bytes": PROFILE["text_bytes"], "slots": FAST_PROFILE["fast_slots"]}
CODES = ("READY", "HOLD", "COMMIT", "HELP", "ABORT")
# The order is also each commander's declared anchor-replacement priority.
GROUP_SLOTS = {"centre": (0, 1, 2, 3), "left_infantry": (4,), "right_infantry": (5,),
               "decisive_cavalry": (6, 7), "containing_cavalry": (8,)}
OUT = {"routing", "shattered", "leaving", "not_deployed", "deploying"}


def able(unit):
    return (unit.get("men", 0) > 0 and not unit.get("error")
            and not OUT.intersection(unit.get("state", [])))


def distance(a, b):
    if any(row.get(key) is None for row in (a, b) for key in ("x", "z")):
        return float("inf")
    return hypot(a["x"] - b["x"], a["z"] - b["z"])


def bind(placements, friendly):
    """Bind once at the authored start, rejecting missing/ambiguous identical types.

    The 25 m tolerance is the existing setup contract (setup.DEPLOYMENT_TOLERANCE_M).
    No tactical regrouping from changing positions or later roster ordering is allowed.
    """
    from twwarhammer3.battle.setup import DEPLOYMENT_TOLERANCE_M

    if len(placements) != 9:
        raise TeamHarnessError("local command requires the declared nine-regiment army")
    used, slots = set(), []
    for placement in placements:
        matches = [u["id"] for u in friendly if u.get("type") == placement["type"]
                   and u.get("id") not in used
                   and distance(u, placement) <= DEPLOYMENT_TOLERANCE_M]
        if len(matches) != 1:
            raise TeamHarnessError("local command requires one identity per authored slot")
        used.add(matches[0])
        slots.append(matches[0])
    if len(used) != len(friendly) or len({u["id"] for u in friendly}) != len(friendly):
        raise TeamHarnessError("local command leaves a duplicate or unowned regiment")
    return {name: tuple(slots[i] for i in indices) for name, indices in GROUP_SLOTS.items()}


def anchors(observation, groups):
    units = {u["id"]: u for u in observation["friendly"]}
    return {name: next((units[identity] for identity in identities
                        if identity in units and able(units[identity])), None)
            for name, identities in groups.items()}


def fields(row, allowed):
    return {key: deepcopy(row[key]) for key in allowed if key in row}


def project(observation, owned, anchor, roster, *, radius=PROFILE["view_m"], global_view=False,
            version=None):
    """Complete member view: no global dynamic summaries or target/navigation backdoors.

    ``version`` names the input of a later declaration (``local-command-v2``)."""
    def local(unit):
        return global_view or anchor is not None and distance(unit, anchor) <= radius

    enemies = [u for u in observation.get("enemy", []) if local(u)]
    visible = {u["id"] for u in enemies}

    def unit(row, allowed):
        # Engine pursuit/queue readbacks can update an unseen target's position.
        result = fields(row, set(allowed) - {"dest", "navigation", "command_queue"})
        if row.get("target") in visible:
            result["target"] = row["target"]
        return result

    result = fields(observation, ("schema", "battle", "seq", "phase", "time_ms", "speed",
                                  "remaining_ms"))
    if observation.get("terrain"):
        terrain = observation["terrain"]
        result["terrain"] = fields(terrain, ("x0", "z0", "cell_m", "rows", "sample_width_m",
                                             "sampled_ms"))
        result["terrain"]["bounds"] = fields(terrain.get("bounds") or {},
                                              ("min_x", "max_x", "min_z", "max_z"))
    result["input_version"] = "local-command-v1"
    if version is not None:
        result["input_version"] = version
    result["friendly"] = [unit(u, UNIT_FIELDS) for u in observation["friendly"] if u["id"] in owned]
    result["allies"] = [unit(u, ALLY_FIELDS) for u in observation["friendly"]
                        if u["id"] not in owned and local(u)]
    result["enemy"] = [unit(u, ALLY_FIELDS) for u in enemies]
    result["enemy_roster"] = [fields(row, ("id", "type", "alliance")) for row in roster]
    result["mode"] = fields(observation.get("mode") or {},
                            ("type", "role", "objectives", "timeout_winner"))
    return result


class Router:
    """No live shared memory: messages are copied at acceptance and again at delivery.

    The caller owns this object on the dispatcher thread. Members get only copied inboxes
    and their own acceptance feedback, never this router or its private event stream.
    Delivery is checked at the first dispatcher observation at/after the due time;
    its actual observation time is recorded, rather than backdating recipient knowledge.

    Mode ``text`` (communication declaration version 2) accepts only addressed text on the
    ``links`` it is given, (sender, recipient) pairs, and records why it refuses a send in the
    acknowledgement and so in its event. Followed: MAGIC magic.py (CORE-Robotics-Lab/MAGIC at
    0ad3a61), where messages pass only along an adjacency mask, and MARBLE
    marble/agent/base_agent.py (ulab-uiuc/MARBLE at 8d60fa1), which lists each agent's allowed
    recipients as an enum in its message tool. MARBLE's handler checks only that the sender has
    some link, so this checks every sender and recipient pair. A ``muted`` text router (the muted
    arm) accepts and acknowledges as usual but records every arrival as undelivered.
    """

    # JUDGEMENT: Local channel ordering — Codex, 2026-11-05: messages ready on the same
    # observation are processed in acceptance order; delivery wins an exact expiry tie.
    # Sorting by due time or expiring at equality differs; member inputs depend on this.

    def __init__(self, rendezvous, *, profile=None, enabled=True, mode="bounded", links=None,
                 muted=False):
        if mode not in {"bounded", "fast", "none", "text"} or (mode == "text") != (
                links is not None) or muted and mode != "text":
            raise ValueError("unknown local communication mode")
        self.links = None if links is None else frozenset(links)
        self.muted = muted
        self.profile = {**PROFILE, **FAST_PROFILE, **(profile or {})}
        self.rendezvous = deepcopy(rendezvous)
        self.enabled = enabled and mode != "none"
        self.mode = mode
        self.pending, self.events = [], []
        self.inboxes = {name: [] for name in rendezvous}
        self.known = {name: {} for name in rendezvous}
        self.cooldowns, self.counts = {}, {name: 0 for name in rendezvous}
        self.now = -1

    def send(self, sender, message, now, current, *, source_ms=None):
        """Return local acceptance only; receipt requires another message. Text mode delivers
        only at the dispatcher's next observation (``advance``), never at a later send."""
        if self.mode != "text":
            self.advance(now, current)
        elif now < self.now:
            raise TeamHarnessError("message clock moved backwards; use a fresh episode router")
        if sender not in self.counts:
            raise TeamHarnessError("unknown message sender")
        source_ms = now if source_ms is None else source_ms
        if not 0 <= source_ms <= now:
            raise TeamHarnessError("invalid message observation basis")
        channel = message.get("channel") if isinstance(message, dict) else None
        origin = current.get(sender)
        accepted = False
        if self.mode == "text":
            reason = self.refusal(sender, message, origin)
            if reason is None:
                recipients, payload, due = [message["to"]], {"text": message["text"]}, now
                accepted = True
        elif self.enabled and origin is not None and channel == "signal":
            if (set(message) == {"channel", "code"} and message["code"] in CODES
                    and now >= self.cooldowns.get(sender, 0)):
                recipients = [name for name, anchor in current.items() if name != sender
                              and anchor is not None
                              and distance(origin, anchor) <= self.profile["signal_m"]]
                payload = {"code": message["code"]}
                due = now + self.profile["signal_delay_ms"]
                self.cooldowns[sender] = now + self.profile["signal_cooldown_ms"]
                accepted = True
        elif self.enabled and origin is not None and channel in ("courier", "text"):
            recipient, text = message.get("to"), message.get("text")
            payload = None
            if set(message) == {"channel", "to", "relay"} and channel == "courier":
                relay = message["relay"]
                if (isinstance(relay, dict) and set(relay) == {"sender", "send"}
                        and isinstance(relay["sender"], str) and type(relay["send"]) is int):
                    previous = self.known[sender].get((relay["sender"], relay["send"]))
                    if previous:
                        payload = fields(previous, ("code", "text", "origin"))
                        text = payload.get("text", payload.get("code"))
            elif set(message) == {"channel", "to", "text"}:
                payload = {"text": text}
            try:
                size = len(text.encode("utf-8")) if isinstance(text, str) else 0
            except UnicodeError:
                size = 0
            fast = channel == "text" and self.mode == "fast"
            slots = self.profile["fast_slots" if fast else "courier_slots"]
            limit = self.profile["fast_text_bytes" if fast else "text_bytes"]
            active = sum(p["sender"] == sender and p["channel"] == channel
                         for p in self.pending)
            if (payload is not None and (channel == "courier" or fast)
                    and isinstance(recipient, str)
                    and recipient in self.rendezvous
                    and recipient != sender and isinstance(text, str)
                    and 0 < size <= limit and active < slots):
                recipients = [recipient]
                point = self.rendezvous[recipient]
                due = (now + self.profile["fast_delay_ms"] if fast else
                       now + self.profile["dispatch_ms"]
                       + distance(origin, point) / self.profile["courier_m_s"] * 1000)
                accepted = True
        self.counts[sender] += 1
        identity = self.counts[sender]
        ack = {"send": identity, "channel": channel, "accepted": accepted, "time_ms": now}
        if self.mode == "text":
            ack["reason"] = reason
        self.events.append({"event": "send", "sender": sender, "message": deepcopy(message),
                            "ack": deepcopy(ack)})
        if accepted:
            payload.setdefault("origin", {"sender": sender, "send": identity,
                                           "source_ms": source_ms, "sent_ms": now})
            self.pending.append({"sender": sender, "channel": channel, "send": identity,
                                 "sent_ms": now, "source_ms": source_ms, "due_ms": due,
                                 "expiry_ms": now + self.profile["lifetime_ms"],
                                 "recipients": recipients, "payload": deepcopy(payload)})
        return ack

    def refusal(self, sender, message, origin):
        """Why text mode refuses a send, or None: anchor, form, channel, link, size or slots."""
        if origin is None:
            return "anchor"
        if not isinstance(message, dict) or "channel" not in message:
            return "form"
        if message["channel"] != "text":
            return "channel"
        if (set(message) != {"channel", "to", "text"} or not isinstance(message["to"], str)
                or not isinstance(message["text"], str)):
            return "form"
        try:
            size = len(message["text"].encode("utf-8"))
        except UnicodeError:
            return "form"
        if (sender, message["to"]) not in self.links:
            return "link"
        if not 0 < size <= self.profile["text_bytes"]:
            return "size"
        if sum(p["sender"] == sender for p in self.pending) >= self.profile["slots"]:
            return "slots"
        return None

    def advance(self, now, current):
        if now < self.now:
            raise TeamHarnessError("message clock moved backwards; use a fresh episode router")
        self.now = now
        waiting = []
        for pending in self.pending:
            if now < min(pending["due_ms"], pending["expiry_ms"]):
                waiting.append(pending)
                continue
            for name in pending["recipients"]:
                anchor = current.get(name)
                valid = (anchor is not None and pending["due_ms"] <= pending["expiry_ms"]
                         and now <= pending["expiry_ms"])
                if pending["channel"] == "courier":
                    valid = (valid and distance(anchor or {}, self.rendezvous[name])
                             <= self.profile["rendezvous_m"])
                if self.muted:  # the sender saw an acceptance; nothing reaches an input
                    valid = False
                record = {"sender": pending["sender"], "channel": pending["channel"],
                          "send": pending["send"], "sent_ms": pending["sent_ms"],
                          "source_ms": pending["source_ms"],
                          "arrived_ms": now, **deepcopy(pending["payload"])}
                if valid:
                    self.inboxes[name].append(record)
                    self.known[name][(record["sender"], record["send"])] = deepcopy(record)
                self.events.append({"event": "arrival", "recipient": name,
                                    "delivered": valid, "record": deepcopy(record),
                                    **({"reason": "muted"} if self.muted else {})})
        self.pending = waiting

    def inbox(self, name):
        return deepcopy(self.inboxes[name])

    def drain_events(self):
        events, self.events = self.events, []
        return events
