"""Communication declaration version 2 on battle C: the peer, relay and overview arms and the
muted, muted_overview and unlinked controls.

Reference: docs/twwarhammer3/communication-structure.md ("What forced means", "The arms", "Code
changes" and "Proposed checks"; none of those checks is agreed). Real LocalTeam, Router and
LocalModel code with fake workers and transports; no game and no paid call. Each test names the
plausible wrong version it must catch.
"""

import hashlib
import json
import sys
from copy import deepcopy
from itertools import count
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wh3_fixtures import FakeSend
from wh3_team_fixtures import Workers, ack

from gameai.ledger import Ledger
from gameai.providers import get_provider
from twwarhammer3.battle import configured, controllers, llm, local_team, setup
from twwarhammer3.battle import local_command as local
from twwarhammer3.battle.team import TeamHarnessError
from twwarhammer3.protocol import PolicyFailure

ARMS = ("peer", "relay", "overview")
V1_ARMS = ("bounded", "silent", "fast", "global")
CAPTAINS = list(local.GROUP_SLOTS)
CONTROLLERS = setup.SCENARIOS_PATH.parent / "controllers"


def scenario(arm):
    return setup.scenarios()[f"emp-envelopment-c-{arm.replace('_', '-')}-v2"]


def state(seq=1, time_ms=5200):
    placements = scenario("peer")["deployment"]["friendly"]
    return {"schema": 1, "battle": "b1", "seq": seq, "time_ms": time_ms, "phase": "Deployed",
            "speed": 1, "remaining_ms": 1200000 - time_ms,
            "friendly": [dict(p, id=f"f{i+1}", men=90, men0=90, state=[], hp=1)
                         for i, p in enumerate(placements)],
            "enemy_roster": [{"id": "e1", "type": "sword"}, {"id": "e2", "type": "horse"},
                             {"id": "e3", "type": "horse"}],
            "enemy": [{"id": "e1", "type": "sword", "x": 170, "z": -175, "men": 90},
                      {"id": "e2", "type": "horse", "x": 400, "z": -465, "men": 45}],
            "mode": {"type": "land_normal", "role": "defender"}}


def text(to, words="status"):
    return {"channel": "text", "to": to, "text": words}


class Member:
    """Gives `orders` and, per reply, the next of `batches`; after them one status to its first
    recipient (a captain) or nothing (the commander)."""

    def __init__(self, *batches, orders=None):
        self.batches, self.orders = list(batches), orders or []
        self.inputs, self.feedback, self.messages = [], [], []

    def decide(self, observation):
        self.inputs.append(deepcopy(observation))
        rules, name = observation["command"]["rules"], observation["command"]["member"]
        default = ([text(rules["recipients"][0], f"{name} {len(self.inputs)}")]
                   if rules["min_messages"] else [])
        self.messages = self.batches.pop(0) if self.batches else default
        return deepcopy(self.orders)

    def drain_messages(self):
        messages, self.messages = self.messages, []
        return messages

    def acknowledge(self, ack, latency):
        self.feedback.append(ack)

    def metadata(self):
        return {"type": "test_member"}


def team(arm, **members):
    policies = {name: members.get(name) or Member() for name in local_team.member_names(arm)}
    workers = Workers()
    policy = local_team.LocalTeam(policies, scenario=scenario(arm), executor=workers,
                                  clock=count().__next__)
    return policy, workers, policies


def play(policy, workers, frames):
    """Per observation: one decide, the selected batch acknowledged, every waiting call run."""
    for seq in range(1, frames + 1):
        time_ms = 5200 + 300 * (seq - 1)
        policy.decide(state(seq, time_ms))
        if policy.selected is not None:
            ack(policy, applied=time_ms + 100)
        for index, (future, _, _) in enumerate(list(workers.tasks)):
            if not future.done():
                workers.finish(index)


def finish(policy, workers, name):
    workers.finish(next(i for i, (future, _, args) in enumerate(workers.tasks)
                        if args[0] is policy.members[name] and not future.done()))


def router(arm):
    names = local_team.member_names(arm)
    return (local.Router({name: {"x": 0, "z": 0} for name in names}, mode="text",
                         links=local_team.links(arm), profile=local.TEXT_PROFILE),
            {name: {"x": 0, "z": 0} for name in names})


@pytest.mark.parametrize("arm", (*ARMS, "muted", "muted_overview", "unlinked"))
def test_a_v2_declaration_builds_the_captains_and_a_commander_only_on_a_star(arm):
    """Wrong versions: a commander accepted on peer, muted or unlinked, or a star arm (relay,
    overview, muted_overview) built without one."""
    policy, _, _ = team(arm)
    try:
        star = arm in ("relay", "overview", "muted_overview")
        assert set(policy.members) == set(CAPTAINS) | ({"commander"} if star else set())
        assert policy.army_owner == ("commander" if star else None)
        assert policy.card["input_version"] == "local-command-v2"
    finally:
        policy.close()
    wrong = set(CAPTAINS) if star else {*CAPTAINS, "commander"}
    with pytest.raises(TeamHarnessError, match="command groups"):
        local_team.LocalTeam({name: Member() for name in wrong}, scenario=scenario(arm),
                             executor=Workers())


@pytest.mark.parametrize("arm", V1_ARMS)
def test_every_v1_arm_refuses_a_commander_and_versions_do_not_mix(arm):
    """Wrong versions: a sixth member accepted on a v1 arm, or a v2 arm name read as v1."""
    suffix = "" if arm == "bounded" else f"-{arm}"
    with pytest.raises(TeamHarnessError):
        local_team.LocalTeam({name: Member() for name in [*CAPTAINS, "commander"]},
                             scenario=setup.scenarios()[f"emp-envelopment-c{suffix}-v2"],
                             executor=Workers())
    for version, name in ((1, "relay"), (2, arm)):
        with pytest.raises(ValueError, match="declared C communication arm"):
            local_team.declaration({"communication": {"version": version, "arm": name}})


def test_text_on_a_declared_link_arrives_at_the_next_observation_with_no_added_delay():
    """Wrong versions: an added delay, delivery at a later send of the same observation (so
    send order changes who reads what), delivery to someone else, or no origin."""
    channel, current = router("relay")
    ack = channel.send("centre", text("commander", "Enemy at 245 -175"), 5200, current,
                       source_ms=5000)
    assert ack == {"send": 1, "channel": "text", "accepted": True, "time_ms": 5200,
                   "reason": None}
    channel.send("right_infantry", text("commander", "Holding"), 5200, current)
    assert channel.inbox("commander") == []  # a later send in the same observation delivers nothing
    channel.advance(5200, current)
    assert channel.inbox("commander") == [{
        "sender": "centre", "channel": "text", "send": 1, "sent_ms": 5200, "source_ms": 5000,
        "arrived_ms": 5200, "text": "Enemy at 245 -175",
        "origin": {"sender": "centre", "send": 1, "source_ms": 5000, "sent_ms": 5200}},
        {"sender": "right_infantry", "channel": "text", "send": 1, "sent_ms": 5200,
         "source_ms": 5200, "arrived_ms": 5200, "text": "Holding",
         "origin": {"sender": "right_infantry", "send": 1, "source_ms": 5200, "sent_ms": 5200}}]
    assert not any(channel.inbox(name) for name in CAPTAINS)


@pytest.mark.parametrize("sender, message, reason", [
    ("centre", {"channel": "signal", "code": "HELP"}, "channel"),
    ("centre", {"channel": "courier", "to": "commander", "text": "Report"}, "channel"),
    ("commander", {"channel": "courier", "to": "left_infantry",
                   "relay": {"sender": "centre", "send": 1}}, "channel"),
    ("centre", text("left_infantry"), "link"),  # captain to captain in a star
    ("centre", text("centre"), "link"),
    ("commander", text("commander"), "link"),
    ("centre", text("nobody"), "link"),
    ("centre", text("commander", "x" * 241), "size"),
    ("centre", text("commander", "é" * 121), "size"),  # 121 characters, 242 bytes
    ("centre", text("commander", ""), "size"),
    ("centre", {**text("commander"), "relay": None}, "form"),
    ("centre", {"channel": "text", "to": "commander"}, "form"),
    ("centre", {"channel": "text", "to": ["commander"], "text": "x"}, "form"),
    ("centre", {"channel": "text", "to": "commander", "text": 5}, "form"),
    ("centre", text("commander", "\ud800"), "form"),
    ("centre", {"to": "commander", "text": "x"}, "form"),
    ("centre", ["text", "commander", "x"], "form"),
], ids=lambda value: value if isinstance(value, str) and len(value) < 20 else None)
def test_a_v2_send_off_its_text_links_is_refused_with_its_reason_and_never_delivered(
        sender, message, reason):
    """Wrong versions: signals, couriers or relays left open, a filter that checks only that the
    sender has some link (MARBLE's gap), bytes counted as characters, or no reason recorded."""
    channel, current = router("relay")
    ack = channel.send(sender, message, 0, current)
    assert ack["accepted"] is False and ack["reason"] == reason
    assert channel.events[-1]["ack"] == ack
    channel.advance(0, current)
    assert not channel.pending and not any(channel.inboxes.values())


def test_a_sender_without_an_anchor_and_a_sender_with_64_pending_are_refused():
    """Wrong versions: a captain whose regiments are all out still sends, the slot limit counts
    every sender together, or exactly 240 bytes is refused."""
    channel, current = router("peer")
    current["centre"] = None
    assert channel.send("centre", text("left_infantry"), 0, current)["reason"] == "anchor"
    current["centre"] = {"x": 0, "z": 0}
    for _ in range(local.TEXT_PROFILE["slots"]):
        assert channel.send("centre", text("left_infantry"), 0, current)["accepted"] is True
    assert channel.send("centre", text("left_infantry"), 0, current)["reason"] == "slots"
    assert channel.send("right_infantry", text("left_infantry"), 0, current)["accepted"] is True
    channel.advance(1, current)
    assert len(channel.inbox("left_infantry")) == 65
    exact = text("left_infantry", "é" * 120)
    assert channel.send("centre", exact, 1, current)["accepted"] is True


@pytest.mark.parametrize("arm", ARMS)
def test_every_member_reaches_exactly_its_declared_recipients(arm):
    """Wrong version: a filter that checks only that the sender has some link (MARBLE's gap) lets
    a star captain reach another captain."""
    channel, current = router(arm)
    names = local_team.member_names(arm)
    for sender in names:
        for recipient in [*names, "nobody"]:
            channel.send(sender, text(recipient), 0, current)
    channel.advance(0, current)
    delivered = {(m["sender"], name) for name in names for m in channel.inbox(name)}
    expected = {(a, b) for a in names for b in names
                if a != b and (arm == "peer" or "commander" in (a, b))}
    assert delivered == set(local_team.links(arm)) == expected
    assert len(expected) == (20 if arm == "peer" else 10)


@pytest.mark.parametrize("arm", ("relay", "overview"))
def test_the_commander_is_asked_without_regiments_and_reads_its_inbox_at_every_input(arm):
    """Wrong versions: TeamPolicy's skip for members without living men, or the living-men inbox
    gate, still applies to the commander; or an inbox is read twice."""
    centre = Member([text("commander", "first")], [text("commander", "second")])
    policy, workers, members = team(arm, centre=centre)
    try:
        play(policy, workers, 30)
    finally:
        policy.close()
    inputs = members["commander"].inputs
    assert len(inputs) >= 3 and all(view["friendly"] == [] for view in inputs)
    received = [(m["sender"], m["send"]) for view in inputs for m in view["command"]["received"]]
    assert len(received) == len(set(received))
    texts = [m["text"] for view in inputs for m in view["command"]["received"]
             if m["sender"] == "centre"]
    assert texts[:2] == ["first", "second"]


def test_the_relay_commander_sees_no_contacts_and_nothing_it_cannot_know():
    """Wrong version: R's commander gets a 160 m view around its endpoint (the centre's start
    point, 110 m from e1), or its input changes with units it cannot know about."""
    policy, _, _ = team("relay")
    try:
        policy._partition(state())
        commander = policy.members["commander"]
        view = policy._view(state(), commander, for_input=True)
        view.pop("command")
        assert view == local.project(state(), frozenset(), None, policy.roster,
                                     version="local-command-v2")
        assert view["friendly"] == view["allies"] == view["enemy"] == []
        changed = state(1, 5200)
        changed["enemy"][0].update(x=60, z=-180, men=3, state=["routing"])
        changed["friendly"][0].update(x=300, men=1, state=["routing"])
        changed["evaluation"] = {"enemy_hp": .2}
        again = policy._view(changed, commander)
        again.pop("command")
        assert again == view
    finally:
        policy.close()


def test_the_overview_commander_sees_the_alliance_view_and_no_hidden_field():
    """Wrong versions: O reads hidden state (evaluation, final, setup), an enemy only the roster
    lists, or owns regiments."""
    observation = state()
    observation.update(evaluation={"enemy_hp": .7}, final={"won": True}, setup={"seed": 1})
    policy, _, _ = team("overview")
    try:
        policy._partition(observation)
        view = policy._view(observation, policy.members["commander"], for_input=True)
    finally:
        policy.close()
    assert view["friendly"] == []
    assert [u["id"] for u in view["allies"]] == [f"f{i}" for i in range(1, 10)]
    assert [u["id"] for u in view["enemy"]] == ["e1", "e2"]
    assert not {"evaluation", "final", "setup"} & set(view)
    assert "enemy_hp" not in json.dumps(view) and "seed" not in json.dumps(view)


@pytest.mark.parametrize("arm", local_team.TOPOLOGIES)
def test_a_v2_captain_sees_an_enemy_150_m_from_its_anchor_and_not_one_170_m_away(arm):
    """Wrong version: captains get the global view (the overview commander's), so the 160 m
    boundary is gone."""
    policy, _, _ = team(arm)
    try:
        policy._partition(state())
        for name in CAPTAINS:
            anchor = policy.current[name]
            observation = state()
            observation["enemy"] = [
                {"id": "e1", "type": "sword", "x": anchor["x"] + 150, "z": anchor["z"], "men": 90},
                {"id": "e2", "type": "horse", "x": anchor["x"], "z": anchor["z"] - 170, "men": 45}]
            view = policy._view(observation, policy.members[name], for_input=True)
            assert [u["id"] for u in view["enemy"]] == ["e1"], name
    finally:
        policy.close()


@pytest.mark.parametrize("arm", local_team.TOPOLOGIES)
def test_a_v2_captain_reads_each_message_delivered_to_it_exactly_once(arm):
    """Wrong version: a captain's inbox is not cleared when it is read, so a captain rereads its
    mail at every input (the commander's own read-once test does not cover captains)."""
    star = local_team.TOPOLOGIES[arm] == "star"
    chief = Member(*[[text(name, f"to {name} {i}") for name in CAPTAINS] for i in range(8)])
    policy, workers, members = team(arm, **({"commander": chief} if star else {}))
    try:
        play(policy, workers, 30)
        _, arrivals = sends_and_arrivals(policy.drain_events())
    finally:
        policy.close()
    heard = 0
    for name in CAPTAINS:
        inputs = members[name].inputs
        read = [(m["sender"], m["send"]) for view in inputs for m in view["command"]["received"]]
        delivered = [(a["record"]["sender"], a["record"]["send"]) for a in arrivals
                     if a["recipient"] == name and a["delivered"]
                     and a["record"]["arrived_ms"] <= inputs[-1]["time_ms"]]
        assert len(inputs) >= 3 and sorted(read) == sorted(delivered), name
        heard += len(read)
    assert (heard > 0) == (arm not in ("muted", "muted_overview", "unlinked"))


@pytest.mark.parametrize("arm", ARMS)
def test_the_v2_command_block_carries_the_contract_shape_and_plan_v2(arm):
    """Wrong versions: v1's rendezvous, signal codes or plan in a v2 block, or wrong limits."""
    policy, _, _ = team(arm)
    try:
        policy._partition(state())
        blocks = {name: policy._view(state(), member, for_input=True)
                  for name, member in policy.members.items()}
    finally:
        policy.close()
    plan = local_team.PLAN_V2_PATH.read_text()
    for name, view in blocks.items():
        command = view["command"]
        assert view["input_version"] == "local-command-v2"
        assert set(command) == {"member", "arm", "topology", "groups", "start_points", "plan",
                                "rules", "received", "send_feedback"}
        assert (command["member"], command["arm"], command["plan"]) == (name, arm, plan)
        assert command["topology"] == ("mesh" if arm == "peer" else "star")
        assert set(command["groups"]) == set(command["start_points"]) == set(CAPTAINS)
        assert command["start_points"]["left_infantry"] == {"x": 0, "z": -125}
        captain = name != "commander"
        recipients = ([c for c in CAPTAINS if c != name] if arm == "peer"
                      else ["commander"] if captain else CAPTAINS)
        assert command["rules"] == {"channel_mode": "text", "text_bytes": 240, "slots": 64,
                                    "min_messages": 1 if captain else 0,
                                    "max_messages": 2 if captain else 5,
                                    "recipients": recipients}


@pytest.mark.parametrize("arm, name, sent, fails", [
    ("peer", "centre", 0, True), ("peer", "centre", 2, False), ("peer", "centre", 3, True),
    ("relay", "right_infantry", 0, True), ("relay", "commander", 0, False),
    ("overview", "commander", 5, False), ("overview", "commander", 6, True),
    ("unlinked", "centre", 0, False), ("unlinked", "centre", 1, True),
])
def test_a_scripted_member_outside_its_message_count_ends_the_episode(arm, name, sent, fails):
    """Wrong versions: the dispatcher keeps v1's 0 to 2 bound, so a silent captain passes and a
    commander's fifth message ends the battle; or unlinked keeps the captains' forced message."""
    to = "left_infantry" if arm == "peer" else "centre" if name == "commander" else "commander"
    policy, workers, _ = team(arm, **{name: Member([text(to)] * sent)})
    try:
        policy.decide(state())
        finish(policy, workers, name)
        if fails:
            with pytest.raises(PolicyFailure, match="message"):
                policy.decide(state(2, 5500))
        else:
            policy.decide(state(2, 5500))
            assert len(policy.acceptances[name]) == sent
    finally:
        policy.close()


def test_a_commander_order_forfeits_its_whole_reply():
    """Wrong version: the commander's order reaches the engine, or its messages still go out."""
    chief = Member([text("centre", "advance")], orders=[{"unit": "f1", "type": "halt"}])
    policy, workers, _ = team("relay", commander=chief)
    try:
        policy.decide(state())
        finish(policy, workers, "commander")
        assert policy.decide(state(2, 5500)) == []
        failed = [e for e in policy.drain_events() if e["event"] == "failed"]
        assert [e["member"] for e in failed] == ["commander"]
        assert policy.router.counts["commander"] == 0 and not policy.router.pending
        assert policy.members["commander"].call is not None  # asked again
    finally:
        policy.close()


class Forfeits(Member):
    """Forfeits the first call whose input holds mail, as an invalid model reply does."""

    def __init__(self):
        super().__init__()
        self.forfeited = None

    def decide(self, observation):
        if self.forfeited is None and observation["command"]["received"]:
            self.inputs.append(deepcopy(observation))
            self.forfeited = len(self.inputs) - 1
            raise PolicyFailure("an invalid reply")
        return super().decide(observation)


def test_a_forfeited_captain_call_returns_its_mail_to_the_next_input_oldest_first():
    """Wrong version: a forfeit drops the mail and send feedback its input read, so a report
    is never seen by a call that completes."""
    left = Forfeits()
    policy, workers, _ = team("peer", left_infantry=left)  # the centre texts left infantry
    try:
        # Left infantry's second call reads "centre 1" and forfeits; "centre 2" arrives meanwhile.
        for seq, name in enumerate(("centre", "left_infantry", "centre", "left_infantry",
                                    "left_infantry"), 1):
            policy.decide(state(seq, 5200 + 300 * seq))
            if policy.selected is not None:
                ack(policy, applied=5300 + 300 * seq)
            finish(policy, workers, name)
        failed = [e for e in policy.drain_events() if e["event"] == "failed"]
    finally:
        policy.close()
    assert [e["member"] for e in failed] == ["left_infantry"] and left.forfeited == 1
    lost, after = (view["command"] for view in left.inputs[1:])
    assert [m["text"] for m in lost["received"]] == ["centre 1"]
    assert [m["text"] for m in after["received"]] == ["centre 1", "centre 2"]
    assert lost["send_feedback"] and after["send_feedback"] == lost["send_feedback"]


def model(tmp_path, arm, name, reply, provider="anthropic"):
    send = FakeSend(json.dumps(reply))
    policy = llm.LLMPolicy(next(iter(get_provider(provider).prices)), "low",
                           Ledger(tmp_path / f"{name}.jsonl", 1), send=send, provider=provider)
    return local_team.LocalModel(policy, arm=arm, member=name), send


def member_view(arm, name):
    policy, _, _ = team(arm)
    try:
        policy._partition(state())
        return policy._view(state(), policy.members[name], for_input=True)
    finally:
        policy.close()


@pytest.mark.parametrize("arm, name, messages, orders", [
    ("peer", "centre", [], True),
    ("peer", "centre", [text("left_infantry")] * 3, True),
    ("relay", "centre", [text("left_infantry")], True),  # captain to captain in a star
    ("peer", "centre", [text("commander")], True),
    ("relay", "commander", [text("Centre")], False),  # enum values can change case
    ("peer", "centre", [{"channel": "signal", "code": "HELP"}], True),
    ("peer", "centre", [{"channel": "courier", "to": "left_infantry", "text": "hi"}], True),
    ("overview", "commander", [text("centre")] * 6, False),
    ("overview", "commander", [], True),  # any commander order
    ("unlinked", "centre", [text("left_infantry")], True),
], ids=["none", "three", "off-link", "no-commander", "case", "signal", "courier", "six", "order",
        "unlinked"])
def test_a_model_reply_off_its_rules_forfeits_with_no_partial_orders(
        tmp_path, arm, name, messages, orders):
    """Wrong versions: the parser accepts empty lists or trusts the schema's enum, so the minimum,
    the recipients or the text channel (a courier to a linked captain) is enforced only on the
    wire."""
    reply = {"orders": [{"unit": "f1", "type": "halt"}] if orders else [], "reason": "r",
             "notes": None, "messages": messages}
    member, send = model(tmp_path, arm, name, reply)
    with pytest.raises(PolicyFailure):
        member.decide(member_view(arm, name))
    assert len(send.bodies) == 1 and member.drain_messages() == []


@pytest.mark.parametrize("provider", ("anthropic", "openai"))
@pytest.mark.parametrize("arm, name, messages", [
    ("peer", "centre", [text("decisive_cavalry"), text("left_infantry")]),
    ("relay", "centre", [text("commander")]),
    ("overview", "commander", []),
])
def test_a_model_reply_within_its_rules_is_used_and_its_wire_schema_fits_the_provider(
        tmp_path, provider, arm, name, messages):
    """Wrong versions: Claude sent maxItems (which it rejects) or no minItems for a captain, other
    providers losing maxItems, or recipients left as free text."""
    orders = [{"unit": "f1", "type": "halt"}] if name == "centre" else []
    member, send = model(tmp_path, arm, name, {"orders": orders, "reason": "r", "notes": None,
                                               "messages": messages}, provider)
    assert member.decide(member_view(arm, name)) == orders
    assert member.drain_messages() == messages
    schema = send.bodies[0]["text"]["format"]["schema"]["properties"]["messages"]
    captain = name != "commander"
    assert schema.get("minItems") == (1 if captain else None)
    assert schema.get("maxItems") == (None if provider == "anthropic" else 2 if captain else 5)
    assert schema["items"]["properties"]["to"] == {
        "type": "string", "enum": member_view(arm, name)["command"]["rules"]["recipients"]}
    assert schema["items"]["properties"]["channel"]["enum"] == ["text"]


class RoleSend(FakeSend):
    """Each member's requests; a captain replies with one text to its first recipient."""

    def __init__(self):
        super().__init__()
        self.requests = {}

    def __call__(self, body):
        command = json.loads(body["input"][0]["content"])["observation"]["command"]
        self.requests.setdefault(command["member"], []).append(body)
        rules = command["rules"]
        mail = [text(rules["recipients"][0])] if rules["min_messages"] else []
        self.replies = [json.dumps({"orders": [], "reason": "r", "notes": None,
                                    "messages": mail})]
        return super().__call__(body)


@pytest.mark.parametrize("arm", (*ARMS, "unlinked"))
def test_configured_model_arms_give_each_role_its_own_prompt(tmp_path, monkeypatch, arm):
    """Wrong versions: the commander gets the captains' prompt (one prompt per leaf type), a v2
    member gets v1's local_command_prompt.md, or the card records other prompts than were sent."""
    send = RoleSend()
    monkeypatch.setattr(controllers, "api_key", lambda *a: "unused")
    monkeypatch.setattr(controllers, "post", lambda key, body, **kwargs: send(body))
    config = {"policy": "configured", "scenario": f"emp-envelopment-c-{arm}-v2",
              "controller_config": str(CONTROLLERS / f"cannae-{arm}-model.json"),
              "provider": "anthropic", "model": "claude-haiku-5-5", "effort": "low",
              "ledger": str(tmp_path / "spend.jsonl"), "budget_usd": 1}
    Path(config["ledger"]).touch()
    policy = controllers.factories(config)["configured"]()
    try:
        policy._partition(state())
        for name, member in policy.members.items():
            member.policy.decide(policy._view(state(), member, for_input=True))
    finally:
        policy.close()
    rules = json.loads(local_team.TOPOLOGY_RULES_PATH.read_text())[arm]
    base = llm.RULES_PROMPT_PATH.read_text()
    captain_prompt = local_team.CAPTAIN_PROMPT_PATH.read_text()
    commander_prompt = local_team.COMMANDER_PROMPT_PATH.read_text()
    sent = {}
    for name, (body,) in send.requests.items():
        role = "commander" if name == "commander" else "captain"
        prompt = body["instructions"]
        own, other = ((commander_prompt, captain_prompt) if role == "commander"
                      else (captain_prompt, commander_prompt))
        assert prompt.startswith(base) and own in prompt and rules[role] in prompt
        assert other not in prompt and local_team.PROMPT_PATH.read_text() not in prompt
        observation = json.loads(body["input"][0]["content"])["observation"]
        assert observation["input_version"] == "local-command-v2"
        assert observation["command"]["plan"] == local_team.PLAN_V2_PATH.read_text()
        sent.setdefault(f"llm_rules {role}", set()).add(prompt)
    assert set(send.requests) == local_team.member_names(arm)
    assert {key: {value} for key, value in policy.card["model_prompts"].items()} == sent
    assert {m["version"] for m in policy.card["member_controllers"].values()} == {
        "local-command-v2"}


@pytest.mark.parametrize("arm, path, accepted", [
    ("relay", "cannae-relay-model", True), ("overview", "cannae-overview-probe", True),
    ("peer", "cannae-peer-probe", True), ("peer", "cannae-relay-model", False),
    ("relay", "cannae-peer-model", False), ("v2", "cannae-relay-probe", False),
    ("relay", "cannae-relay-witness", True), ("muted", "cannae-muted-witness", True),
    ("muted", "cannae-relay-witness", False), ("unlinked", "cannae-unlinked-model", True),
    ("unlinked", "cannae-relay-model", False),
    ("muted_overview", "cannae-muted-overview-witness", True),
    ("muted_overview", "cannae-muted-witness", False),
])
def test_configured_load_takes_the_commander_only_on_a_star_arm(arm, path, accepted):
    """Wrong versions: the loader keeps demanding exactly the five groups, or accepts a commander
    on peer, muted, unlinked or a v1 arm (`emp-envelopment-c-v2` is v1's bounded arm)."""
    name = ("emp-envelopment-c-v2" if arm == "v2"
            else f"emp-envelopment-c-{arm.replace('_', '-')}-v2")
    config = {"policy": "configured", "controller_config": str(CONTROLLERS / f"{path}.json"),
              "scenario": name, "provider": "anthropic", "model": "claude-haiku-5-5",
              "effort": "low"}
    if not accepted:
        with pytest.raises(ValueError, match="command groups"):
            configured.load(config["controller_config"], config)
        return
    frozen = configured.load(config["controller_config"], config)[0]
    assert set(frozen["members"]) == local_team.member_names(arm)


@pytest.mark.parametrize("arm", ARMS)
def test_probe_left_infantry_moves_east_only_after_a_centre_message_reaches_it(arm):
    """Wrong versions: left infantry moves before its cue, a star cue that skips the commander,
    a move not 40 m east of its start point, a captain-to-captain delivery in a star, or a star
    probe that never tries one (so the live link check could not fail)."""
    config = {"policy": "configured", "scenario": f"emp-envelopment-c-{arm}-v2",
              "controller_config": str(CONTROLLERS / f"cannae-{arm}-probe.json")}
    local_team.validate_config(scenario(arm), config)
    policy = controllers.factories(config)["configured"]()
    workers = policy.pool = Workers()
    policy.clock = count().__next__
    try:
        play(policy, workers, 40)
        events = policy.drain_events()
    finally:
        policy.close()
    left = policy.members["left_infantry"]
    calls = [(args[1], future.result()) for future, _, args in workers.tasks
             if args[0] is left and future.done()]
    moved = next(i for i, (_, result) in enumerate(calls) if result["orders"])
    assert all(not result["orders"] for _, result in calls[:moved])
    assert calls[moved][1]["orders"] == [{"unit": "f5", "type": "move", "x": 40, "z": -125,
                                          "run": True}]
    cue = left.policy.probe_cue
    assert cue in calls[moved][0]["command"]["received"]
    assert not any(cue in view["command"]["received"] for view, _ in calls[:moved])
    assert cue["text"].startswith("centre:")
    assert cue["sender"] == ("centre" if arm == "peer" else "commander")
    arrivals = [e["record"] for e in events if e["event"] == "communication"
                and e["record"]["event"] == "arrival" and e["record"]["delivered"]]
    pairs = {(r["record"]["sender"], r["recipient"]) for r in arrivals}
    assert pairs and pairs <= set(local_team.links(arm))
    if arm != "peer":
        assert policy.members["commander"].policy.forwarded["sender"] == "centre"
    sends = [e["record"] for e in events if e["event"] == "communication"
             and e["record"]["event"] == "send"]
    refused = [(r["sender"], r["message"]["to"], r["ack"]["send"], r["ack"]["reason"])
               for r in sends if not r["ack"]["accepted"]]
    # In a star, right infantry's first reply (sends 1 and 2) tries left infantry once.
    assert refused == ([] if arm == "peer" else [("right_infantry", "left_infantry", 2, "link")])


def sends_and_arrivals(events):
    records = [e["record"] for e in events if e["event"] == "communication"]
    return ([r["ack"] for r in records if r["event"] == "send"],
            [r for r in records if r["event"] == "arrival"])


@pytest.mark.parametrize("arm, shown, first", [
    ("muted", "peer", {"centre": [text("decisive_cavalry", "seen")]}),
    ("muted_overview", "overview", {"centre": [text("commander", "seen")],
                                    "commander": [text("left_infantry", "target")]}),
])
def test_a_muted_arm_is_the_arm_it_shows_to_its_members_and_delivers_nothing(arm, shown, first):
    """Wrong versions: a muted arm delivers anyway, refuses its texts (an ack the sender can
    read), stops asking the overview commander or gives it another view, or shows its members
    another arm name, rules, links or prompt than the arm it plays."""
    runs = {}
    for name in (shown, arm):
        policy, workers, members = team(name, **{key: Member(batch)
                                                 for key, batch in first.items()})
        try:
            play(policy, workers, 12)
            runs[name] = (policy.card, members, sends_and_arrivals(policy.drain_events()))
        finally:
            policy.close()
    (shown_card, shown_members, (shown_acks, shown_arrivals)) = runs[shown]
    (card, members, (acks, arrivals)) = runs[arm]
    assert acks == shown_acks and acks and all(a["accepted"] and a["reason"] is None
                                               for a in acks)
    assert all(a["delivered"] for a in shown_arrivals)
    assert len(arrivals) == len(shown_arrivals) > 0
    assert not any(a["delivered"] for a in arrivals)
    assert {a["reason"] for a in arrivals} == {"muted"}
    assert set(members) == set(shown_members) == local_team.member_names(shown)
    heard = 0
    for name in members:
        # Asked again after its first reply, the overview commander included (2 or 3 inputs in
        # 12 frames, by the hash seed's member order).
        assert len(members[name].inputs) >= 2, name
        for view in shown_members[name].inputs:
            heard += len(view["command"].pop("received"))
        assert all(view["command"].pop("received") == [] for view in members[name].inputs)
        # The shown arm's name, rules, views and the commander's alliance view included.
        assert members[name].inputs == shown_members[name].inputs, name
        assert {view["command"]["arm"] for view in members[name].inputs} == {shown}
        assert local_team.member_prompt(arm, name) == local_team.member_prompt(shown, name)
    assert heard > 0
    assert card["communication_arm"] == arm
    keys = ("topology", "links", "min_messages", "max_messages", "sensing", "army_owner")
    assert {key: card[key] for key in keys} == {key: shown_card[key] for key in keys}


def claude_schema_problems(schema):
    """What breaks the structured-output limits local_team.py cites (docs/references.md, checked
    2026-11-05): maxItems is unsupported, minItems only 0 or 1; an enum needs a value and an
    object is closed (additionalProperties false)."""
    problems = []

    def walk(node, path):
        if isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}/{index}")
            return
        if not isinstance(node, dict):
            return
        if "maxItems" in node or node.get("minItems", 0) not in (0, 1):
            problems.append(f"{path}: array bound")
        if "enum" in node and not node["enum"]:
            problems.append(f"{path}: empty enum")
        if node.get("type") == "object" and node.get("additionalProperties") is not False:
            problems.append(f"{path}: open object")
        for key, value in node.items():
            walk(value, f"{path}/{key}")

    walk(schema, "")
    return problems


@pytest.mark.parametrize("provider", ("anthropic", "openai"))
def test_the_unlinked_arm_has_no_links_and_its_model_reply_carries_no_message(tmp_path,
                                                                               provider):
    """Wrong versions: unlinked keeps peer's links or forced message, its Claude schema carries an
    empty recipient enum (what text_schema built from an empty list) or a keyword Claude rejects,
    or the parser lets a message through."""
    policy, _, _ = team("unlinked")
    try:
        assert set(policy.members) == set(CAPTAINS) and policy.card["links"] == []
        assert policy.card["min_messages"] == policy.card["max_messages"] == {"captain": 0}
    finally:
        policy.close()
    view = member_view("unlinked", "centre")
    assert view["command"]["rules"] == {"channel_mode": "text", "text_bytes": 240, "slots": 64,
                                        "min_messages": 0, "max_messages": 0, "recipients": []}
    halt = [{"unit": "f1", "type": "halt"}]
    member, send = model(tmp_path, "unlinked", "centre", {"orders": halt, "reason": "r",
                                                          "notes": None, "messages": []}, provider)
    assert member.decide(view) == halt and member.drain_messages() == []
    body = send.bodies[0]
    rules = json.loads(local_team.TOPOLOGY_RULES_PATH.read_text())["unlinked"]["captain"]
    assert rules in body["instructions"] and "cannot be sent" in rules and "empty" in rules
    schema = body["text"]["format"]["schema"]
    messages = schema["properties"]["messages"]
    assert "minItems" not in messages
    if provider == "anthropic":
        assert claude_schema_problems(schema) == [] and "maxItems" not in messages
    else:
        assert messages["maxItems"] == 0
    member, send = model(tmp_path, "unlinked", "centre", {
        "orders": halt, "reason": "r", "notes": None, "messages": [text("left_infantry")]},
        provider)
    with pytest.raises(PolicyFailure):
        member.decide(view)
    assert len(send.bodies) == 1 and member.drain_messages() == []


# The v1 identity check: v1_digest, in a module of this name, ran on 220450c's src and configs
# (the revision before version 2) and printed these.
V1_DIGESTS = {
    "bounded": "583d636dd1147d76ffee8e4dbd5e8d1938d92e788ea66ef0b65797872930357d",
    "silent": "6553739cae7447f6512f4023f90dc19b2fa25b8063dc887f3a46b9864670070d",
    "fast": "9ab3daacd5617e814ac09b2f85b5b057a6cfe9a9bca34741648d17bcd1208d95",
    "global": "b68d8061681e74e0d61667bdb27b324887adb74bd0ab159c0cce6051378b9fb2",
}


class Talker:
    """A scripted member that sends its messages once and halts its first regiment."""

    def __init__(self, messages=()):
        self.messages = list(messages)

    def decide(self, observation):
        return [{"unit": observation["friendly"][0]["id"], "type": "halt"}]

    def drain_messages(self):
        messages, self.messages = self.messages, []
        return messages

    def acknowledge(self, ack, latency):
        pass

    def metadata(self):
        return {"type": "talker"}


def frame(scenario, seq, time_ms):
    placements = scenario["deployment"]["friendly"]
    return {"schema": 1, "battle": "b1", "seq": seq, "time_ms": time_ms, "phase": "Deployed",
            "speed": 1, "remaining_ms": 1200000 - time_ms,
            "friendly": [dict(p, id=f"f{i+1}", men=90, men0=90, state=[], hp=1)
                         for i, p in enumerate(placements)],
            "enemy_roster": [{"id": "e1", "type": "sword"}, {"id": "e2", "type": "horse"}],
            "enemy": [{"id": "e1", "type": "sword", "x": 170, "z": -175, "men": 90},
                      {"id": "e2", "type": "horse", "x": 400, "z": -465, "men": 45}],
            "mode": {"type": "land_normal", "role": "defender"},
            "evaluation": {"enemy_hp": .7}}


def v1_digest(arm, tmp):
    suffix = "" if arm == "bounded" else f"-{arm}"
    scenario = setup.scenarios()[f"emp-envelopment-c{suffix}-v1"]
    members = {name: Talker() for name in local.GROUP_SLOTS}
    members["centre"] = Talker([{"channel": "signal", "code": "HELP"},
                                {"channel": "courier", "to": "left_infantry", "text": "Report"}])
    members["left_infantry"] = Talker([{"channel": "text", "to": "centre", "text": "Fast"}])
    workers = Workers()
    policy = local_team.LocalTeam(members, scenario=scenario, executor=workers, clock=lambda: 0)
    try:
        for seq, time_ms in enumerate((5200, 5500, 12000, 12500, 13000, 30000), 1):
            policy.decide(frame(scenario, seq, time_ms))
            if policy.selected is not None:
                ack(policy, applied=time_ms + 100)
            for index, (future, _, _) in enumerate(list(workers.tasks)):
                if not future.done():
                    workers.finish(index)
        inputs = [args[1] for _, _, args in workers.tasks]
        events = policy.drain_events()
        card = policy.card
    finally:
        policy.close()
    bodies = []
    for provider in ("openai", "anthropic"):
        send = FakeSend(json.dumps({"orders": [], "reason": "wait", "notes": None,
                                    "messages": []}))
        model = local_team.LocalModel(llm.LLMPolicy(
            next(iter(get_provider(provider).prices)), "low",
            Ledger(Path(tmp) / f"{arm}-{provider}.jsonl", 1), send=send, provider=provider))
        model.decide(inputs[0])
        bodies.append(send.bodies[0])
    record = {"inputs": inputs, "events": events, "card": card, "bodies": bodies,
              "schemas": [local_team.reply_schema(p) for p in ("openai", "anthropic")]}
    return hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()


@pytest.mark.parametrize("arm", V1_ARMS)
def test_every_v1_arm_keeps_its_inputs_acks_events_card_and_wire_bytes(tmp_path, arm):
    """Wrong versions: the text profile or a rejection reason leaks into PROFILE, a v1 rules
    block or v1 acks; v1 gets the v2 plan, prompt or schema. Reference: the same function's
    output at 220450c, the revision before version 2."""
    assert v1_digest(arm, tmp_path) == V1_DIGESTS[arm]
