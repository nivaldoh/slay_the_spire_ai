"""C's information boundary and delayed immutable message contract, offline only."""

from copy import deepcopy

import pytest

from twwarhammer3.battle import local_command as local
from twwarhammer3.battle.setup import scenarios
from twwarhammer3.battle.team import TeamHarnessError


def test_repeated_types_bind_by_authored_identity_and_never_by_roster_order():
    placements = scenarios()["emp-envelopment-a-v1"]["deployment"]["friendly"]
    units = [dict(p, id=f"f{20 - i}", men=90) for i, p in enumerate(placements)]
    groups = local.bind(placements, list(reversed(units)))
    assert groups == {"centre": ("f20", "f19", "f18", "f17"),
                      "left_infantry": ("f16",), "right_infantry": ("f15",),
                      "decisive_cavalry": ("f14", "f13"), "containing_cavalry": ("f12",)}
    units[0]["x"] += 100
    with pytest.raises(TeamHarnessError, match="authored slot"):
        local.bind(placements, units)


def test_distant_state_and_nested_target_readbacks_do_not_change_complete_member_input():
    owned = {"id": "f1", "type": "sword", "men": 90, "x": 0, "z": 0,
             "target": "e2", "dest": {"x": 900, "z": 0},
             "navigation": {"target_position": {"x": 900}},
             "command_queue": [{"target": "e2", "x": 900}]}
    ally = {"id": "f2", "type": "sword", "men": 90, "x": 800, "z": 0}
    enemy = {"id": "e2", "type": "horse", "men": 45, "x": 900, "z": 0}
    obs = {"schema": 1, "battle": "b1", "seq": 1, "time_ms": 1000,
           "friendly": [owned, ally], "enemy": [enemy], "evaluation": {"enemy_hp": .7},
           "mode": {"type": "land_normal", "hidden_strength": .7},
           "magic": {"hidden_status": 123}}
    roster = [{"id": "e2", "type": "horse", "dead": False}]
    first = local.project(obs, {"f1"}, owned, roster)
    changed = deepcopy(obs)
    changed["friendly"][1].update(men=1, x=700, target="e2", state=["routing"])
    changed["enemy"][0].update(men=0, x=950, state=["routing"])
    changed["friendly"][0]["navigation"]["target_position"]["x"] = 950
    changed["mode"]["hidden_strength"] = 0
    changed["evaluation"]["enemy_hp"] = 0
    assert local.project(changed, {"f1"}, changed["friendly"][0], roster) == first
    assert first["enemy"] == first["allies"] == []
    assert all(k not in first["friendly"][0]
               for k in ("target", "navigation", "dest", "command_queue"))
    assert first["enemy_roster"] == [{"id": "e2", "type": "horse"}]
    # A locally visible cue must change the input and may make attack-by-id legal.
    changed["enemy"][0].update(x=50, men=45)
    assert local.project(changed, {"f1"}, changed["friendly"][0], roster) != first


def test_anchor_replacement_is_owned_priority_and_no_anchor_has_no_remote_view():
    groups = {"a": ("f1", "f2")}
    observation = {"friendly": [
        {"id": "f2", "men": 90, "x": 100, "z": 0},
        {"id": "f1", "men": 90, "x": 0, "z": 0}]}
    assert local.anchors(observation, groups)["a"]["id"] == "f1"
    observation["friendly"][1]["state"] = ["routing"]
    assert local.anchors(observation, groups)["a"]["id"] == "f2"
    observation["friendly"][0]["men"] = 0
    assert local.anchors(observation, groups)["a"] is None


def router(**kwargs):
    return local.Router({"a": {"x": 0, "z": 0}, "b": {"x": 200, "z": 0},
                         "c": {"x": 500, "z": 0}}, **kwargs)


def current():
    return {"a": {"x": 0, "z": 0}, "b": {"x": 200, "z": 0},
            "c": {"x": 500, "z": 0}}


def test_signal_range_is_frozen_at_send_delay_and_cooldown_use_battle_time():
    channel, positions = router(), current()
    ack = channel.send("a", {"channel": "signal", "code": "HELP"}, 0, positions)
    assert ack == {"send": 1, "channel": "signal", "accepted": True, "time_ms": 0}
    assert all(not channel.inbox(name) for name in positions)
    positions["c"]["x"] = 100  # moving into range after emission does not subscribe
    channel.advance(local.PROFILE["signal_delay_ms"] - 1, positions)
    assert channel.inbox("b") == []
    channel.advance(local.PROFILE["signal_delay_ms"], positions)
    assert channel.inbox("b")[0]["code"] == "HELP"
    assert channel.inbox("c") == []
    denied = channel.send("a", {"channel": "signal", "code": "READY"},
                          local.PROFILE["signal_cooldown_ms"] - 1, positions)
    assert denied["accepted"] is False
    assert channel.send("a", {"channel": "signal", "code": "READY"},
                        local.PROFILE["signal_cooldown_ms"], positions)["accepted"] is True


def test_courier_uses_known_rendezvous_not_secret_tracking_and_payload_is_immutable():
    channel, positions = router(), current()
    message = {"channel": "courier", "to": "b", "text": "Enemy cavalry is engaged."}
    ack = channel.send("a", message, 0, positions)
    message["text"] = "Mutated after acceptance"
    assert set(ack) == {"send", "channel", "accepted", "time_ms"}
    due = local.PROFILE["dispatch_ms"] + 200 / local.PROFILE["courier_m_s"] * 1000
    positions["b"]["x"] = 400
    channel.advance(due, positions)
    assert channel.inbox("b") == []
    assert channel.events[-1]["delivered"] is False
    # No remote failure or coordinates are sent back to the sender.
    assert channel.inbox("a") == []
    other = router()
    other.send("a", {"channel": "courier", "to": "b", "text": "Original"}, 0, current())
    other.advance(due, current())
    inbox = other.inbox("b")
    assert inbox[0]["text"] == "Original" and inbox[0]["arrived_ms"] == due
    inbox[0]["text"] = "Changed by recipient"
    assert other.inbox("b")[0]["text"] == "Original"


def test_capacity_expiry_payload_and_reset():
    channel, positions = router(), current()
    text = {"channel": "courier", "to": "b", "text": "x" * local.PROFILE["text_bytes"]}
    for _ in range(local.PROFILE["courier_slots"]):
        assert channel.send("a", text, 0, positions)["accepted"] is True
    assert channel.send("a", text, 0, positions)["accepted"] is False
    oversized = channel.send("a", {**text, "text": text["text"] + "é"}, 0, positions)
    assert oversized["accepted"] is False
    channel.advance(local.PROFILE["lifetime_ms"] + 1, positions)
    assert channel.inbox("b") == []
    assert not channel.pending
    assert router().inbox("b") == []
    with pytest.raises(TeamHarnessError, match="clock moved backwards"):
        channel.advance(0, positions)


@pytest.mark.parametrize("change", ({"to": []}, {"to": {}}, {"text": "\ud800"},
                                   {"text": 123}, {"to": "unknown"}))
def test_malformed_couriers_are_local_rejections(change):
    channel = router()
    message = {"channel": "courier", "to": "b", "text": "hello", **change}
    assert channel.send("a", message, 0, current())["accepted"] is False
    assert not channel.pending


def test_messages_ready_together_keep_acceptance_order_and_delivery_wins_expiry_tie():
    channel = router(profile={"dispatch_ms": 0, "courier_m_s": 200,
                              "signal_delay_ms": 500, "lifetime_ms": 1000})
    channel.send("a", {"channel": "courier", "to": "b", "text": "First accepted"},
                 0, current())
    channel.send("a", {"channel": "signal", "code": "HELP"}, 0, current())
    channel.advance(1000, current())
    messages = channel.inbox("b")
    assert [(m["send"], m["channel"]) for m in messages] == [(1, "courier"), (2, "signal")]
    assert all(m["arrived_ms"] == 1000 for m in messages)


def test_courier_relay_preserves_original_content_and_age_and_requires_local_receipt():
    channel, positions = router(), current()
    channel.send("a", {"channel": "courier", "to": "b", "text": "Old report"},
                 0, positions, source_ms=0)
    relay = {"channel": "courier", "to": "c", "relay": {"sender": "a", "send": 1}}
    assert channel.send("b", relay, 0, positions)["accepted"] is False
    channel.advance(12000, positions)
    assert channel.inbox("b")[0]["text"] == "Old report"
    channel.inboxes["b"].clear()  # already read by the member; it may remember this report
    assert channel.send("b", relay, 12000, positions, source_ms=12000)["accepted"] is True
    channel.advance(29000, positions)
    received = channel.inbox("c")[0]
    assert received["text"] == "Old report" and received["sender"] == "b"
    assert received["source_ms"] == 12000 and received["arrived_ms"] == 29000
    assert received["origin"] == {"sender": "a", "send": 1, "source_ms": 0, "sent_ms": 0}


def test_fast_text_ignores_remote_rendezvous_and_silent_arm_has_no_explicit_channel():
    positions = current()
    positions["b"]["x"] = 400
    message = {"channel": "text", "to": "b", "text": "Far from rendezvous"}
    fast = router(mode="fast")
    assert fast.send("a", message, 0, positions)["accepted"] is True
    fast.advance(0, positions)
    assert fast.inbox("b")[0]["text"] == message["text"]
    assert router().send("a", message, 0, positions)["accepted"] is False
    silent = router(mode="none")
    ack = silent.send("a", {"channel": "signal", "code": "HELP"}, 0, positions)
    assert ack["accepted"] is False
    assert silent.send("a", {"channel": "courier", "to": "b", "text": "help"},
                       0, positions)["accepted"] is False
    assert not silent.pending


def courier_due(metres):
    return local.PROFILE["dispatch_ms"] + metres / local.PROFILE["courier_m_s"] * 1000


def test_courier_time_comes_from_the_published_rendezvous_and_it_is_never_a_tick_early():
    channel, positions = router(), current()
    positions["b"]["x"] = 400  # elsewhere at send; the sender cannot know that
    channel.send("a", {"channel": "courier", "to": "b", "text": "Report"}, 0, positions)
    positions["b"]["x"] = 200
    due = courier_due(200)
    channel.advance(due - 1, positions)
    assert channel.inbox("b") == []
    channel.advance(due, positions)
    assert [m["arrived_ms"] for m in channel.inbox("b")] == [due]


def test_courier_travel_starts_from_the_senders_anchor_frozen_at_send():
    channel, positions = router(), current()
    positions["a"]["x"] = -100  # off its rendezvous at send, back on it by delivery
    channel.send("a", {"channel": "courier", "to": "b", "text": "Report"}, 0, positions)
    positions["a"]["x"] = 0
    due = courier_due(300)
    channel.advance(due - 1, positions)
    assert channel.inbox("b") == []
    channel.advance(due, positions)
    assert [m["arrived_ms"] for m in channel.inbox("b")] == [due]


def test_a_courier_delivers_the_accepted_text_not_a_later_edit_of_the_message():
    channel, positions = router(), current()
    message = {"channel": "courier", "to": "b", "text": "Original"}
    assert channel.send("a", message, 0, positions)["accepted"] is True
    message["text"] = "Edited in flight"
    channel.advance(courier_due(200), positions)
    assert [m["text"] for m in channel.inbox("b")] == ["Original"]


def test_a_relay_needs_the_senders_own_receipt_and_a_free_courier_slot():
    channel, positions = router(), current()
    channel.send("a", {"channel": "courier", "to": "b", "text": "Report"}, 0, positions)
    now = courier_due(200)
    channel.advance(now, positions)
    assert channel.inbox("b")[0]["text"] == "Report"
    relay = {"channel": "courier", "to": "a", "relay": {"sender": "a", "send": 1}}
    assert channel.send("c", relay, now, positions)["accepted"] is False  # only b holds it
    for _ in range(local.PROFILE["courier_slots"]):
        own = {"channel": "courier", "to": "c", "text": "Own report"}
        assert channel.send("b", own, now, positions)["accepted"] is True
    assert channel.send("b", relay, now, positions)["accepted"] is False
    now += courier_due(300)  # its own couriers arrive at c and free the slots
    channel.advance(now, positions)
    assert channel.send("b", relay, now, positions)["accepted"] is True


def test_a_signal_never_reaches_its_sender():
    channel, positions = router(), current()
    channel.send("a", {"channel": "signal", "code": "HELP"}, 0, positions)
    channel.advance(local.PROFILE["signal_delay_ms"], positions)
    assert channel.inbox("a") == []
    assert [m["code"] for m in channel.inbox("b")] == ["HELP"]


# JUDGEMENT?: Closed channel bounds — Claude, 2026-11-05: exactly at signal_m or rendezvous_m is
# in range, as local_command.py's <= has it; the page says only "within". An open bound differs
# only at exact equality. These two tests and their open-boundary plants rest on it.
@pytest.mark.parametrize("beyond, heard", ((0, True), (1, False)))
def test_a_signal_reaches_exactly_its_published_range(beyond, heard):
    channel, positions = router(), current()
    positions["b"]["x"] = local.PROFILE["signal_m"] + beyond
    channel.send("a", {"channel": "signal", "code": "HELP"}, 0, positions)
    channel.advance(local.PROFILE["signal_delay_ms"], positions)
    assert bool(channel.inbox("b")) is heard


@pytest.mark.parametrize("beyond, delivered", ((0, True), (1, False)))
def test_a_courier_reaches_exactly_the_published_rendezvous_radius(beyond, delivered):
    channel, positions = router(), current()
    channel.send("a", {"channel": "courier", "to": "b", "text": "Report"}, 0, positions)
    positions["b"]["x"] += local.PROFILE["rendezvous_m"] + beyond
    channel.advance(courier_due(200), positions)
    assert bool(channel.inbox("b")) is delivered
