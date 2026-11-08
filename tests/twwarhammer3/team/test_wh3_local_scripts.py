"""Stage 2 witnesses and foils (local_scripts.py) on inputs shaped as the v2 contract says.

The witnesses get fake v2 member observations (runs/comm-build-20261108/contract.md), and each
witness file also runs through the real v2 LocalTeam; the foils run through the real v1
LocalTeam and their JSON files. None of this shows a live delivery, a timing or a win.
"""

import sys
from copy import deepcopy
from itertools import count
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wh3_team_fixtures import Workers, ack

from twwarhammer3.battle import controllers, local_scripts, local_team, setup
from twwarhammer3.battle import local_command as local
from twwarhammer3.battle.local_scripts import (
    CONTACT_MS,
    REFRESH_MS,
    CentralConcentration,
    FixedSchedule,
    OverviewWitnessCaptain,
    OverviewWitnessCommander,
    PeerWitness,
    RelayWitnessCommander,
    ThinkingRush,
)
from twwarhammer3.battle.scripted import RushNearest
from twwarhammer3.protocol import validate_orders

DECLARED_THINK_S = (local_scripts.THINK_S, local_scripts.COMMANDER_THINK_S)

PLACEMENTS = setup.scenarios()["emp-envelopment-c-silent-v2"]["deployment"]["friendly"]
CLASSES = {"wh_main_emp_inf_swordsmen": "infantry", "wh_main_emp_inf_greatswords": "infantry",
           "wh_main_emp_cav_empire_knights": "cavalry"}
GROUPS = {name: [f"f{i + 1}" for i in slots] for name, slots in local.GROUP_SLOTS.items()}
START = {name: {"x": PLACEMENTS[slots[0]]["x"], "z": PLACEMENTS[slots[0]]["z"]}
         for name, slots in local.GROUP_SLOTS.items()}
CONTROLLERS = setup.SCENARIOS_PATH.parent / "controllers"


@pytest.fixture(autouse=True)
def no_think_time(monkeypatch):
    """The witnesses' think time is 0 here, so the suite stays fast."""
    monkeypatch.setattr(local_scripts, "THINK_S", 0)
    monkeypatch.setattr(local_scripts, "COMMANDER_THINK_S", 0)


def regiment(index, **changes):
    row = PLACEMENTS[index]
    return {"id": f"f{index + 1}", "type": row["type"], "class": CLASSES[row["type"]],
            "x": row["x"], "z": row["z"], "men": 90, "men0": 90, "state": ["idle"], **changes}


def foe(identity, kind, x, z, **changes):
    return {"id": identity, "class": kind, "x": x, "z": z, "men": 90, "men0": 90, "state": [],
            **changes}


def record(sender, body, sent_ms):
    return {"sender": sender, "channel": "text", "send": 1, "sent_ms": sent_ms,
            "source_ms": sent_ms, "arrived_ms": sent_ms + 300, "text": body,
            "origin": {"sender": sender, "send": 1, "source_ms": sent_ms, "sent_ms": sent_ms}}


def member_view(member, *, arm="peer", time_ms=30000, enemy=(), received=()):
    """A v2 member observation as contract.md describes it; the overview commander sees all."""
    captain = member != "commander"
    if arm == "peer":
        recipients = [name for name in local.GROUP_SLOTS if name != member]
    else:
        recipients = ["commander"] if captain else list(local.GROUP_SLOTS)
    every = [regiment(i) for i in range(9)]
    own = set(GROUPS[member]) if captain else set()
    return {"schema": 1, "battle": "b1", "seq": time_ms // 100, "phase": "Deployed",
            "time_ms": time_ms, "input_version": "local-command-v2",
            "friendly": [u for u in every if u["id"] in own],
            "allies": [] if captain else every, "enemy": deepcopy(list(enemy)),
            "enemy_roster": [{"id": e["id"], "type": "unknown"} for e in enemy],
            "mode": {"type": "land_normal", "role": "defender"},
            "terrain": {"bounds": {"min_x": -600, "max_x": 600, "min_z": -800, "max_z": 400}},
            "command": {"member": member, "arm": arm,
                        "topology": "mesh" if arm == "peer" else "star",
                        "groups": deepcopy(GROUPS), "start_points": deepcopy(START),
                        "plan": "plan", "received": list(received), "send_feedback": [],
                        "rules": {"channel_mode": "text", "text_bytes": 240, "slots": 64,
                                  "min_messages": 1 if captain else 0,
                                  "max_messages": 2 if captain else 5,
                                  "recipients": recipients}}}


def check_messages(messages, observation):
    rules = observation["command"]["rules"]
    assert rules["min_messages"] <= len(messages) <= rules["max_messages"]
    for message in messages:
        assert set(message) == {"channel", "to", "text"} and message["channel"] == "text"
        assert message["to"] in rules["recipients"]
        assert 0 < len(message["text"].encode("utf-8")) <= rules["text_bytes"]


CROWD = [foe(f"regiment-{n:02d}", "infantry", 120, -175 - n) for n in range(1, 11)]
CROWD += [foe("regiment-11", "cavalry", 140, -100), foe("regiment-12", "cavalry", 140, -120)]


@pytest.mark.parametrize("kind,arm", ((PeerWitness, "peer"), (PeerWitness, "relay"),
                                       (OverviewWitnessCaptain, "overview")))
@pytest.mark.parametrize("member", local.GROUP_SLOTS)
def test_witness_captains_send_one_or_two_bounded_texts_to_allowed_recipients(kind, arm, member):
    """Wrong version caught: one text per contact, a report not cut at 240 bytes, or a text to
    the captain itself or to a peer in the star arm (the relay witness's captains included)."""
    policy = kind()
    for time_ms, enemy in ((5000, []), (6000, CROWD[:1]), (7000, CROWD), (8000, [])):
        view = member_view(member, arm=arm, time_ms=time_ms, enemy=enemy)
        policy.decide(view)
        messages = policy.drain_messages()
        check_messages(messages, view)
        if arm != "peer":
            assert [m["to"] for m in messages] == ["commander"]
        assert policy.drain_messages() == []


def test_peer_reports_lead_with_the_recipients_class_and_round_trip():
    """Wrong version caught: one contact order for every recipient (here by id), which cuts both
    horses from the cavalry groups' 240 bytes."""
    centre, texts, sent = PeerWitness(), {}, {}
    for time_ms in (30000, 30500):  # two peers per reply, so both replies reach all four
        centre.decide(member_view("centre", time_ms=time_ms, enemy=CROWD))
        for message in centre.drain_messages():
            texts[message["to"]], sent[message["to"]] = message["text"], time_ms
    assert set(texts) == set(local.GROUP_SLOTS) - {"centre"}
    for peer, body in texts.items():
        classes = [part.split(" ")[1] for part in body.split(";")[1:]]
        wanted = "cavalry" if peer.endswith("cavalry") else "infantry"
        assert classes[0] == wanted and classes.count("cavalry") == (2 if wanted == "cavalry"
                                                                     else 0)
    # A contact keeps the time its reporter saw it, not the time the text arrived.
    reader, seen_ms = PeerWitness(), sent["decisive_cavalry"]
    reader.decide(member_view("decisive_cavalry", time_ms=31000,
                              received=[record("centre", texts["decisive_cavalry"], seen_ms)]))
    assert {identity: (c["x"], c["z"], c["time_ms"]) for identity, c in reader.contacts.items()
            if c["class"] == "cavalry"} == {"regiment-11": (140, -100, seen_ms),
                                            "regiment-12": (140, -120, seen_ms)}


NORTH_HORSE = foe("horse-north", "cavalry", 150, -60)
INFANTRY = foe("e1", "infantry", 40, -100)  # 85 m from f7, inside decisive cavalry's view


@pytest.mark.parametrize("kind,arm,cue", (
    (PeerWitness, "peer", record("left_infantry", "seen 29000;horse-north cavalry 150 -60", 29000)),
    (PeerWitness, "relay", record("commander", "seen 29000;horse-north cavalry 150 -60", 29000)),
    (OverviewWitnessCaptain, "overview", record("commander", "target horse-north 150 -60 29000",
                                                29000)),
))
def test_captains_run_toward_a_reported_target_and_attack_it_only_in_their_own_view(kind, arm,
                                                                                     cue):
    """Wrong version caught: attacking the reported id while it is out of view (validate_orders
    refuses it), ignoring the message for the visible infantry, or (relay) reading only texts
    from peers, so the commander's forward is lost."""
    policy = kind()
    view = member_view("decisive_cavalry", arm=arm, enemy=[INFANTRY], received=[cue])
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert orders == [{"unit": unit, "type": "move", "x": 150.0, "z": -60.0, "facing": None,
                       "width": None, "run": True, "queue": False} for unit in ("f7", "f8")]
    seen = dict(NORTH_HORSE, x=100, z=-70)
    view = member_view("decisive_cavalry", arm=arm, time_ms=31000, enemy=[INFANTRY, seen])
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert [(o["unit"], o["type"], o["target"]) for o in orders] == [
        ("f7", "attack", "horse-north"), ("f8", "attack", "horse-north")]


@pytest.mark.parametrize("age,moves", ((CONTACT_MS, True), (CONTACT_MS + 1, False)))
def test_peer_witness_ignores_a_report_older_than_the_contact_age(age, moves):
    """Wrong version caught: a contact table that never forgets, so the cavalry run to where a
    horse stood long ago."""
    cue = record("left_infantry", "seen 29000;horse-north cavalry 150 -60", 29000)
    orders = PeerWitness().decide(member_view("decisive_cavalry", time_ms=29000 + age,
                                              received=[cue]))
    assert bool(orders) is moves


def test_overview_commander_orders_nothing_and_texts_only_new_or_due_targets():
    """Wrong version caught: re-sending every assignment on each reply (the unchanged reply
    would carry four texts), or a target for a role WingSupport leaves without one."""
    north, south = foe("horse-north", "cavalry", 200, -95), foe("horse-south", "cavalry", 260, -415)
    sword = foe("e1", "infantry", 245, -175)  # 185 m from the centre: the centre gets nothing
    commander = OverviewWitnessCommander()

    def reply(time_ms, enemy):
        view = member_view("commander", arm="overview", time_ms=time_ms, enemy=enemy)
        assert commander.decide(view) == []
        messages = commander.drain_messages()
        check_messages(messages, view)
        return {m["to"]: m["text"] for m in messages}

    assert reply(1000, []) == {}
    assert reply(2000, [north, south, sword]) == {
        "left_infantry": "target horse-north 200 -95 2000",
        "decisive_cavalry": "target horse-north 200 -95 2000",
        "right_infantry": "target e1 245 -175 2000",
        "containing_cavalry": "target horse-south 260 -415 2000"}
    assert reply(2500, [north, south, sword]) == {}
    moved = dict(north, x=180)
    assert reply(2000 + REFRESH_MS, [moved, south, sword]) == {
        "left_infantry": f"target horse-north 180 -95 {2000 + REFRESH_MS}",
        "decisive_cavalry": f"target horse-north 180 -95 {2000 + REFRESH_MS}",
        "right_infantry": f"target e1 245 -175 {2000 + REFRESH_MS}",
        "containing_cavalry": f"target horse-south 260 -415 {2000 + REFRESH_MS}"}
    routed = dict(moved, state=["routing"])
    assert reply(5500, [routed, south, sword]) == {
        "left_infantry": "target e1 245 -175 5500",
        "decisive_cavalry": "target horse-south 260 -415 5500"}


def v1_state(time_ms):
    return {"schema": 1, "battle": "b1", "seq": 1, "time_ms": time_ms, "phase": "Deployed",
            "speed": 1, "remaining_ms": 1200000 - time_ms,
            "friendly": [regiment(i, state=[]) for i in range(9)],
            "enemy_roster": [{"id": "e1", "type": "sword"}],
            "enemy": [foe("e1", "infantry", 170, -175)],  # in the centre's view only
            "mode": {"type": "land_normal", "role": "defender"}}


def move(unit, x, z):
    return {"unit": unit, "type": "move", "x": x, "z": z, "facing": None, "width": None,
            "run": True, "queue": False}


@pytest.mark.parametrize("name,kind,expected", (
    ("cannae-local-schedule", FixedSchedule, {
        "left_infantry": [], "right_infantry": [],  # their time (20 s) has not come
        "decisive_cavalry": [move("f7", 175, -85), move("f8", 120, -85)],
        "containing_cavalry": [move("f9", 175, -425)]}),
    ("cannae-local-concentrate", CentralConcentration, {
        "left_infantry": [move("f5", 60, -175)], "right_infantry": [move("f6", 60, -175)],
        "decisive_cavalry": [move("f7", 60, -175), move("f8", 5, -175)],
        "containing_cavalry": [move("f9", 60, -175)]}),
))
def test_foils_send_nothing_and_follow_their_timetables_on_the_silent_arm(name, kind, expected):
    """Wrong version caught: moving before the marked time, sending a status text, or walking
    past an enemy in view (the centre sees e1)."""
    path = setup.SCENARIOS_PATH.parent / f"controllers/{name}.json"
    config = {"policy": "configured", "controller_config": str(path),
              "scenario": "emp-envelopment-c-silent-v2"}
    local_team.validate_config(setup.scenarios()[config["scenario"]], config)
    policy = controllers.factories(config)["configured"]()
    workers = policy.pool = Workers()
    try:
        assert all(type(member.policy) is kind for member in policy.members.values())
        policy.decide(v1_state(5200))
        for index in range(len(local.GROUP_SLOTS)):
            workers.finish(index)
        calls = {name: next(future.result() for future, _, args in workers.tasks
                            if args[0] is member) for name, member in policy.members.items()}
        assert all(call["messages"] == [] for call in calls.values())
        assert {name: call["orders"] for name, call in calls.items()} == {
            "centre": [{"unit": f"f{i}", "type": "attack", "target": "e1", "mode": "auto",
                        "run": True, "queue": False} for i in (1, 2, 3, 4)], **expected}
    finally:
        policy.close()


def test_the_relay_commander_forwards_new_contacts_with_their_sighting_times():
    """Wrong versions caught: a forward stamped with the commander's own time (the reader would
    keep an old position as fresh), a report sent back to the captain who made it, a text
    repeated with nothing new, the cavalry groups' horse queued behind infantry, or an order."""
    commander = RelayWitnessCommander()

    def reply(time_ms, *received):
        view = member_view("commander", arm="relay", time_ms=time_ms, received=received)
        assert commander.decide(view) == []
        messages = commander.drain_messages()
        check_messages(messages, view)
        return {m["to"]: m["text"] for m in messages}

    swords = "seen 29000;e1 infantry 120 -200;e2 infantry 125 -250"
    horse = "seen 29500;horse-north cavalry 150 -60"
    first = reply(30000, record("centre", swords, 29000), record("left_infantry", horse, 29500))
    assert first == {"centre": horse, "left_infantry": swords, "right_infantry": swords,
                     "decisive_cavalry": horse, "containing_cavalry": horse}
    assert reply(33000) == {"right_infantry": horse, "decisive_cavalry": swords,
                            "containing_cavalry": swords}
    assert reply(36000) == {}
    moved = "seen 36500;e1 infantry 110 -200"
    assert reply(37000, record("right_infantry", moved, 36500)) == {
        name: moved for name in local.GROUP_SLOTS if name != "right_infantry"}
    # The decisive cavalry's peer witness keeps the horse at the time left infantry saw it.
    reader = PeerWitness()
    reader.decide(member_view("decisive_cavalry", arm="relay", time_ms=31000,
                              received=[record("commander", first["decisive_cavalry"], 30000)]))
    assert reader.contacts["horse-north"]["time_ms"] == 29500


def test_each_scripted_member_sleeps_its_think_time_inside_decide(monkeypatch):
    """Wrong versions caught: no delay (a script answers at once while Haiku captains think about
    2 s), a commander given the captains' 2 s, or a member that skips the sleep."""
    assert DECLARED_THINK_S == (2.0, 3.0)
    monkeypatch.setattr(local_scripts, "THINK_S", DECLARED_THINK_S[0])
    monkeypatch.setattr(local_scripts, "COMMANDER_THINK_S", DECLARED_THINK_S[1])
    slept = []
    monkeypatch.setattr(local_scripts, "sleep", slept.append)
    foil = member_view("centre")
    foil["command"]["rendezvous"] = deepcopy(START)
    for kind, view, seconds in (
            (PeerWitness, member_view("centre"), 2.0),
            (PeerWitness, member_view("centre", arm="relay"), 2.0),
            (OverviewWitnessCaptain, member_view("centre", arm="overview"), 2.0),
            (FixedSchedule, foil, 2.0), (CentralConcentration, foil, 2.0),
            (ThinkingRush, member_view("centre"), 2.0),
            (OverviewWitnessCommander, member_view("commander", arm="overview"), 3.0),
            (RelayWitnessCommander, member_view("commander", arm="relay"), 3.0)):
        slept.clear()
        kind().decide(view)
        assert slept == [seconds], kind.__name__


def finish_waiting(workers):
    for index, (future, _, _) in enumerate(list(workers.tasks)):
        if not future.done():
            workers.finish(index)


def test_the_thinking_rush_file_is_the_silent_local_rush():
    """Wrong version caught: a file naming another foil, or orders other than rush_nearest's on
    the same view (the stage 2 rush must differ from cannae-local-rush.json only in timing)."""
    config = {"policy": "configured", "scenario": "emp-envelopment-c-silent-v2",
              "controller_config": str(CONTROLLERS / "cannae-local-rush-think.json")}
    local_team.validate_config(setup.scenarios()[config["scenario"]], config)
    policy = controllers.factories(config)["configured"]()
    workers = policy.pool = Workers()
    try:
        assert all(type(member.policy) is ThinkingRush for member in policy.members.values())
        policy.decide(v1_state(5200))
        finish_waiting(workers)
        calls = [future.result() for future, _, _ in workers.tasks]
    finally:
        policy.close()
    assert len(calls) == 5 and any(call["orders"] for call in calls)
    for call in calls:
        assert call["messages"] == [] and call["orders"] == RushNearest().decide(call["view"])


# e1 is within 90 m of the centre and in left infantry's view; the south horse e10 is in right
# infantry's and the containing cavalry's views; the decisive cavalry sees neither.
FIELD = [foe("e1", "infantry", 120, -200), foe("e10", "cavalry", 100, -420)]


def v2_state(seq, time_ms):
    return {"schema": 1, "battle": "b1", "seq": seq, "time_ms": time_ms, "phase": "Deployed",
            "speed": 1, "remaining_ms": 1200000 - time_ms,
            "friendly": [regiment(i, state=[]) for i in range(9)],
            "enemy_roster": [{"id": e["id"], "type": "unknown"} for e in FIELD],
            "enemy": deepcopy(FIELD), "mode": {"type": "land_normal", "role": "defender"}}


@pytest.mark.parametrize("arm", ("peer", "muted", "relay", "overview"))
def test_each_witness_file_plays_the_real_v2_team_within_its_rules(arm):
    """Wrong versions caught: a witness outside its message count (the episode would end), an
    order the team refuses, a relay or overview commander whose texts never arrive, or a muted
    router that delivers anyway."""
    name = f"emp-envelopment-c-{arm}-v2"
    config = {"policy": "configured", "scenario": name,
              "controller_config": str(CONTROLLERS / f"cannae-{arm}-witness.json")}
    local_team.validate_config(setup.scenarios()[name], config)
    policy = controllers.factories(config)["configured"]()
    workers = policy.pool = Workers()
    policy.clock = count().__next__
    dispatched = []
    try:
        for seq in range(1, 41):
            dispatched.append(policy.decide(v2_state(seq, 5200 + 1000 * seq)))
            if policy.selected is not None:
                ack(policy, applied=5300 + 1000 * seq)
            finish_waiting(workers)
        events = policy.drain_events()
        refusals = policy.records()["local_refusals"]
    finally:
        policy.close()
    calls = [(args[1], future.result()) for future, _, args in workers.tasks if future.done()]
    assert not [e for e in events if e["event"] == "failed"] and refusals == 0
    assert {view["command"]["member"] for view, _ in calls} == local_team.member_names(arm)
    for view, result in calls:
        rules = view["command"]["rules"]
        assert rules["min_messages"] <= len(result["messages"]) <= rules["max_messages"]
    assert any(dispatched)
    arrivals = [e["record"] for e in events if e["event"] == "communication"
                and e["record"]["event"] == "arrival"]
    delivered = [(a["record"]["sender"], a["recipient"]) for a in arrivals if a["delivered"]]
    if arm == "muted":
        assert arrivals and not delivered and {a["reason"] for a in arrivals} == {"muted"}
        assert all(view["command"]["received"] == [] for view, _ in calls)
        return
    assert delivered and set(delivered) <= set(local_team.links(arm))
    if arm != "peer":
        assert any(sender == "commander" for sender, _ in delivered)
