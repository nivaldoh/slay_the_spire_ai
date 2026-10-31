"""Agreed scripted-team contract: hand-declared ownership and controlled worker order.

These checks exercise real Python components, not live movement or policy strength.
"""
import json
import sys
from copy import deepcopy
from pathlib import Path
from threading import Event

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_wh3_team import assess
from wh3_fixtures import CONFIG, FakeMailbox
from wh3_team_fixtures import Script, ack, make_team, move, state

from twwarhammer3.battle import digest, play, team


def test_partition_and_deep_public_inputs_use_types_not_positions():
    policy, workers, a, b = make_team()
    raw = state()
    raw.update(orders={"secret": "teammate feedback"}, evaluation={"hidden": 20}, setup={"x": 1})
    policy.decide(raw)
    workers.finish(0)
    workers.finish(1)
    assert policy.members["infantry"].unit == "f2"
    assert policy.members["cavalry"].unit == "f1"
    assert a.inputs[0]["friendly"][0]["id"] == "f2"
    assert a.inputs[0]["allies"][0]["id"] == "f1"
    assert "target" not in a.inputs[0]["friendly"][0]
    assert a.inputs[0]["allies"][0]["target"] == "e1"
    hidden = deepcopy(raw)
    hidden.update(job="different", orders={"other": 1}, evaluation={"hidden": 200}, final={"x": 1})
    hidden["friendly"][0].update(target="another_unseen", target_dead=False)
    hidden["terrain"]["bounds"]["private"] = 0
    assert team.project(hidden, {"f2"}) == a.inputs[0]
    assert team.project(hidden, {"f1"}) == b.inputs[0]  # nor an ally's hidden target
    original_b = deepcopy(b.inputs[0])
    a.inputs[0]["allies"][0]["state"].append("routed")
    a.inputs[0]["terrain"]["rows"][0] = "xxx"
    assert b.inputs[0] == original_b
    assert raw["friendly"][1]["state"] == ["idle"]
    assert raw["terrain"]["rows"] == ["...", "..."]
    event = next(e for e in policy.drain_events() if e["event"] == "input")
    assert event["observation"]["terrain"]["rows"] == ["...", "..."]


@pytest.mark.parametrize("roster", [[], [team.SWORD], [team.SWORD, team.SWORD],
                                    [team.SWORD, team.KNIGHT, team.SWORD],
                                    [team.SWORD, team.KNIGHT, "wh_main_emp_inf_spearmen_0"]])
def test_ambiguous_or_unexpected_rosters_refuse_before_workers(roster):
    policy, workers, _, _ = make_team()
    observation = state()
    observation["friendly"] = [{"id": f"f{i}", "type": kind} for i, kind in enumerate(roster)]
    with pytest.raises(team.TeamHarnessError):
        policy.decide(observation)
    assert not workers.tasks


@pytest.mark.parametrize("bad", [[move("f1")], [{**move("f2"), "queue": True}],
                                  [{"unit": "army", "type": "ability", "ability": "x"}]])
def test_local_refusal_does_not_suppress_peer_or_invent_engine_time(bad):
    policy, workers, a, b = make_team(Script(bad))
    policy.decide(state())
    workers.finish(0)
    workers.finish(1)
    assert policy.decide(state(2, 11000)) == [move("f1")]
    assert policy.metadata()["member"] == "cavalry"
    assert len(a.feedback) == 1
    refusal, timing = a.feedback[0]
    assert refusal["results"][0]["ok"] is False
    assert "applied_ms" not in refusal and "delay_ms" not in timing
    assert timing["source"] == "local" and not b.feedback
    ack(policy)
    assert b.feedback[0][0]["request"] == "r1"


def test_indices_recipient_original_age_and_transport_overage():
    now = [0.0]
    orders = [move("f2"), {"unit": "f2", "type": "attack", "target": "e1", "queue": True}]
    policy, workers, a, b = make_team(Script(orders), clock=lambda: now[0])
    policy.decide(state())
    now[0] = .2
    workers.finish(0)
    assert policy.decide(state(2, 13000)) == orders
    workers.finish(1)  # completes while A awaits feedback
    results = [{"index": 1, "unit": "f2", "ok": True},
               {"index": 2, "unit": "f2", "ok": False, "error": "blocked"}]
    now[0] = 3.5
    ack(policy, results=results)
    assert a.feedback[0][0]["results"] == results and not b.feedback
    assert a.feedback[0][1]["delay_ms"] == 3400  # not the dispatcher's 400
    assert a.feedback[0][1]["roundtrip_s"] == 3.5
    assert a.feedback[0][1]["transport_overage"] is False
    feedback = next(e for e in policy.drain_events() if e["event"] == "feedback")
    assert feedback["latency"]["delay_ms"] == 3400
    assert policy.decide(state(3, 14000)) == [move("f1")]
    ack(policy, applied=15000)
    assert b.feedback[0][1]["transport_overage"] is True


def test_the_oldest_completed_batch_goes_first():
    now = [1.0]
    policy, workers, a, b = make_team(clock=lambda: now[0])
    policy.decide(state())
    workers.finish(1)  # cavalry completes first, infantry 0.1 s later
    now[0] = 1.1
    workers.finish(0)
    policy.decide(state(2, 10100))
    assert policy.metadata()["member"] == "cavalry"
    ack(policy)  # while the infantry holds a batch too
    assert b.feedback and not a.feedback


def test_expiry_boundary():
    policy, workers, a, _ = make_team()
    policy.decide(state())
    workers.finish(0)
    assert policy.decide(state(2, 15000)) == []
    assert "expired" in a.feedback[0][0]["validation_error"]
    assert "applied_ms" not in a.feedback[0][0]


def test_idle_poll_and_member_noop_have_different_feedback():
    policy, workers, a, b = make_team(Script([]))
    assert policy.decide(state()) == []
    ack(policy)
    assert not a.feedback and not b.feedback
    workers.finish(0)
    assert policy.decide(state(2, 11000)) == []
    assert policy.metadata()["member"] == "infantry"
    assert len(workers.tasks) == 2
    with pytest.raises(team.TeamHarnessError, match="awaiting"):
        policy.decide(state(3, 12000))
    ack(policy)
    assert len(a.feedback) == 1 and not b.feedback


@pytest.mark.parametrize("change", ["battle", "id", "read_error"])
def test_partition_never_rebinds_or_accepts_incomplete_engine_units(change):
    policy, _, _, _ = make_team()
    policy.decide(state())
    observation = state(2, 11000)
    if change == "battle":
        observation["battle"] = "new_battle"
    elif change == "id":
        observation["friendly"][0]["id"] = "replacement"
    else:
        observation["friendly"][0] = {"id": "f2", "error": "read failed"}
    with pytest.raises(team.TeamHarnessError):
        play.policy_call(policy, "decide", observation)
    assert policy.members["infantry"].unit == "f2"


def test_equal_completion_times_do_not_keep_favoring_one_member():
    policy, workers, _, _ = make_team(clock=lambda: 1.0)
    policy.decide(state())
    workers.finish(0)
    workers.finish(1)
    policy.decide(state(2, 10100))
    assert policy.metadata()["member"] == "infantry"
    ack(policy)
    # B expires locally while A restarts; both receive the new snapshot.
    assert policy.decide(state(3, 15000)) == []
    workers.finish(2)
    workers.finish(3)
    policy.decide(state(4, 15100))
    assert policy.metadata()["member"] == "cavalry"


@pytest.mark.parametrize("slow_name", ["infantry", "cavalry"])
def test_real_workers_dispatch_and_ack_fast_member_before_slow_release(tmp_path, slow_name):
    stop, started = Event(), Event()
    fast = Script()

    class Slow(Script):
        def decide(self, observation):
            started.set()
            assert stop.wait(5), "test failed to clean up its worker"
            return super().decide(observation)

    slow = Slow()
    fast_name = "cavalry" if slow_name == "infantry" else "infantry"
    policy = team.TeamPolicy({"infantry": (team.SWORD, slow if slow_name == "infantry" else fast),
                              "cavalry": (team.KNIGHT, slow if slow_name == "cavalry" else fast)},
                             stop=stop)

    class Mailbox(FakeMailbox):
        def wait_observation(self, **kwargs):
            seq = self.queue[0]["seq"]
            if seq == 2:
                assert started.wait(2)
                policy.members[fast_name].future.result(timeout=2)
            if seq == 3:
                assert self.requests[-1][2] == [move("f1" if fast_name == "cavalry" else "f2")]
                assert not policy.members[slow_name].future.done()
            if seq == 4:
                assert fast.feedback and not stop.is_set()
                assert not slow.feedback
            return super().wait_observation(**kwargs)

    mailbox = Mailbox([state(0, 0), state(1, 1000), state(2, 2000, ack=True),
                       state(3, 3000, ack=True), state(4, 4000, result="won")])
    try:
        result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0},
                                   lambda: policy, mailbox, not_battle=None)
    finally:
        stop.set()
    assert result["status"] == "won", result
    assert fast.closed and slow.closed and policy.closed
    assert result["card"]["timing"] == "asynchronous"
    records = [json.loads(line) for line in (tmp_path / "e/trace.jsonl").read_text().splitlines()]
    dispatch = next(e for e in records if e["kind"] == "decision" and e["orders"])
    feedback = next(e for e in records if e["kind"] == "team" and e["event"] == "feedback")
    assert dispatch["behavior"]["decision"] == feedback["decision"]
    assert dispatch["request"] == feedback["ack"]["request"]
    assert any(e.get("event") == "discarded" and e["member"] == slow_name for e in records)
    assert "member age 1.5s" in digest.digest(tmp_path / "e")


@pytest.mark.parametrize("fault", ["member", "partition"])
def test_worker_exception_stops_once_and_harness_fault_is_distinct(tmp_path, fault):
    class Broken(Script):
        def decide(self, observation):
            self.inputs.append(observation)
            raise ValueError("broken member")

    policy, workers, a, _ = make_team(Broken())

    class Mailbox(FakeMailbox):
        def wait_observation(self, **kwargs):
            if self.queue[0]["seq"] == 2:
                workers.finish(0)
            return super().wait_observation(**kwargs)

    first = state(1, 1000)
    if fault == "partition":
        first["friendly"].pop()
    mailbox = Mailbox([state(0, 0), first, state(2, 2000, ack=True)])
    result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0},
                               lambda: policy, mailbox, not_battle=None)
    if fault == "member":
        assert result["status"] == "policy_failure" and len(a.inputs) == 1
        assert result["failure"]["member"] == "infantry"
        assert "broken member" in result["error"]
    else:
        assert result["status"] == "unsupported_or_invalid" and not a.inputs
    assert a.closed


@pytest.mark.parametrize("before_send", [True, False])
def test_terminal_disposes_unsent_or_unacknowledged_selection_and_closes_both(
        tmp_path, before_send):
    class BadClose(Script):
        def close(self):
            self.closed = True
            raise ValueError("close failed")

    policy, workers, a, b = make_team(BadClose())

    class Mailbox(FakeMailbox):
        def wait_observation(self, **kwargs):
            if self.queue[0]["seq"] == 2:
                workers.finish(0)
            return super().wait_observation(**kwargs)

        def read_observation(self):
            return {"result": "won"} if before_send and policy.selected else None

    mailbox = Mailbox([state(0, 0), state(1, 1000), state(2, 2000, ack=True),
                       state(3, 3000, result="won")])
    result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0},
                               lambda: policy, mailbox, not_battle=None)
    assert result["engine_ending"]["result"] == "won"
    assert result["status"] == "policy_failure" and a.closed and b.closed
    assert not a.feedback and not b.feedback
    assert len(mailbox.requests) == (1 if before_send else 2)
    events = [json.loads(line) for line in (tmp_path / "e/trace.jsonl").read_text().splitlines()]
    discarded = [e for e in events if e.get("event") == "discarded"]
    assert {e["member"] for e in discarded} == {"infantry", "cavalry"}
    assert any(e["selected"] for e in discarded)
    fresh, _, _, _ = make_team()
    assert fresh.battle is None and fresh.selected is None and not fresh.events


@pytest.mark.parametrize("motion,received,passed", [(["moving"], 12, True),
                                                    (["idle"], 12, False),
                                                    (["moving"], 13, False)])
def test_live_witness_rejects_formation_settling_and_late_motion(motion, received, passed):
    fast_ack = {"request": "r2", "applied_ms": 10500,
                "results": [{"index": 1, "unit": "f1", "ok": True}]}
    slow_ack = {"request": "r3", "applied_ms": 13500,
                "results": [{"index": 1, "unit": "f2", "ok": True}]}
    events = [
        {"kind": "team", "event": "partition", "ownership": {"infantry": "f2", "cavalry": "f1"}},
        {"kind": "team", "event": "completed", "decision": "infantry-1",
         "started": 10, "completed": 13},
        {"kind": "decision", "request": "r2", "orders": [move("f1")],
         "behavior": {"member": "cavalry", "decision": "cavalry-1", "source_seq": 0}},
        {"kind": "team", "event": "feedback", "decision": "cavalry-1", "source": "engine",
         "ack": fast_ack,
         "latency": {"delay_ms": 500}},
        {"kind": "decision", "request": "r3", "orders": [move("f2")],
         "behavior": {"member": "infantry", "decision": "infantry-1", "source_seq": 0}},
        {"kind": "team", "event": "feedback", "decision": "infantry-1", "source": "engine",
         "ack": slow_ack, "latency": {"delay_ms": 3500}},
    ]
    roster = [{"id": "f1", "type": team.KNIGHT, "x": 10, "z": 0, "state": ["idle"]},
              {"id": "f2", "type": team.SWORD, "x": 0, "z": 0, "state": ["idle"]}]
    samples = [
        {"received": 10, "observation": {"seq": 0, "friendly": roster}},  # both members' source
        {"received": 11, "observation": {"orders": fast_ack, "friendly": roster}},
        {"received": received, "observation": {
         "friendly": [{"id": "f1", "x": 10, "z": 1, "state": motion}]}},
        {"received": 30, "observation": {"orders": slow_ack,
         "friendly": [{"id": "f1", "x": 10, "z": 1, "state": ["idle"]}]}},
    ]
    for sample in samples:
        sample["observation"].update(phase="Deployed", time_ms=sample["received"] * 1000)
    assert assess(events, samples, "infantry")["passed"] is passed
    wrong_age = deepcopy(events)
    wrong_age[3]["latency"]["delay_ms"] = 600  # not the raw ack minus the raw source time
    with pytest.raises(AssertionError):
        assess(wrong_age, samples, "infantry")
    # A self-consistent swapped adapter partition must fail against raw unit types.
    events[0]["ownership"] = {"infantry": "f1", "cavalry": "f2"}
    with pytest.raises(AssertionError):
        assess(events, samples, "infantry")



@pytest.mark.parametrize("change", ["moves_away", "slow_clock"])
def test_live_witness_rejects_motion_away_from_the_waypoint_and_a_slow_battle_clock(change):
    # agreed-checks.md: the correct unit moves (toward its order's waypoint) after its
    # acknowledgement while its peer thinks, at 1x. The cavalry's waypoint is (10, 20).
    fast_ack = {"request": "r2", "applied_ms": 10500,
                "results": [{"index": 1, "unit": "f1", "ok": True}]}
    slow_ack = {"request": "r3", "applied_ms": 13500,
                "results": [{"index": 1, "unit": "f2", "ok": True}]}
    events = [
        {"kind": "team", "event": "partition", "ownership": {"infantry": "f2", "cavalry": "f1"}},
        {"kind": "team", "event": "completed", "decision": "infantry-1",
         "started": 10, "completed": 13},
        {"kind": "decision", "request": "r2", "orders": [move("f1")],
         "behavior": {"member": "cavalry", "decision": "cavalry-1", "source_seq": 0}},
        {"kind": "team", "event": "feedback", "decision": "cavalry-1", "source": "engine",
         "ack": fast_ack, "latency": {"delay_ms": 500}},
        {"kind": "decision", "request": "r3", "orders": [move("f2")],
         "behavior": {"member": "infantry", "decision": "infantry-1", "source_seq": 0}},
        {"kind": "team", "event": "feedback", "decision": "infantry-1", "source": "engine",
         "ack": slow_ack, "latency": {"delay_ms": 3500}},
    ]
    roster = [{"id": "f1", "type": team.KNIGHT, "x": 10, "z": 0, "state": ["idle"]},
              {"id": "f2", "type": team.SWORD, "x": 0, "z": 0, "state": ["idle"]}]
    z = -1 if change == "moves_away" else 1
    samples = [
        {"received": 10, "observation": {"seq": 0, "friendly": roster}},
        {"received": 11, "observation": {"orders": fast_ack, "friendly": roster}},
        {"received": 12, "observation": {
         "friendly": [{"id": "f1", "x": 10, "z": z, "state": ["moving"]}]}},
        {"received": 30, "observation": {"orders": slow_ack,
         "friendly": [{"id": "f1", "x": 10, "z": z, "state": ["idle"]}]}},
    ]
    rate = .8 if change == "slow_clock" else 1  # battle seconds per second from 10 s on
    for sample in samples:
        battle_ms = 10000 + (sample["received"] - 10) * 1000 * rate
        sample["observation"].update(phase="Deployed", time_ms=battle_ms)
    result = assess(events, samples, "infantry")
    assert not result["passed"] and result["reason"] == {
        "moves_away": "no qualifying movement observed; capability unverified",
        "slow_clock": "clock progress inconsistent with 1x"}[change]

def test_bad_team_configuration_is_a_harness_failure_before_game_wait(tmp_path):
    result = play.play_episode(tmp_path / "e", CONFIG, lambda: team.TeamPolicy({}),
                               FakeMailbox([]), not_battle=None)
    assert result["status"] == "unsupported_or_invalid"


@pytest.mark.parametrize("members,owner", [
    ({"infantry": (team.SWORD, None)}, None),
    ({"a": (team.SWORD, None), "b": (team.KNIGHT, None), "c": ("other", None)}, None),
    ({"a": (team.SWORD, None), "b": ((team.KNIGHT, team.SWORD), None)}, None),
    ({"a": (None, None), "b": (None, None)}, None),
    ({"a": (team.SWORD, None), "b": (team.KNIGHT, None)}, "c"),
])
def test_a_team_without_two_distinct_members_is_refused_at_construction(members, owner):
    with pytest.raises(team.TeamHarnessError, match="two members with distinct unit types"):
        team.TeamPolicy(members, army_owner=owner, executor=object())
    team.TeamPolicy({"a": (team.SWORD, None), "b": (None, None)}, army_owner="b",
                    executor=object())


def test_duplicate_friendly_unit_ids_are_refused_before_any_member_call():
    # Refusal-sweep review 2026-10-31: removing this refusal passed every team test.
    policy, workers, _, _ = make_team()
    observation = state()
    observation["friendly"][1]["id"] = "f2"  # the knights reuse the swordsmen's id
    with pytest.raises(team.TeamHarnessError, match="duplicate friendly unit ids"):
        policy.decide(observation)
    assert not workers.tasks


def test_a_member_owning_the_rest_must_keep_every_unit_it_was_given():
    # ModelTeam's partition shape (one member owns the rest); a subset check passed every test.
    from wh3_team_fixtures import Workers
    policy = team.TeamPolicy({"cavalry": ((team.KNIGHT,), Script()), "line": (None, Script())},
                             executor=Workers())
    first = state()
    first["friendly"].append({**first["friendly"][0], "id": "f3"})
    policy.decide(first)
    later = state(seq=2, time_ms=11000)
    later["friendly"].append({**later["friendly"][0], "id": "f9"})  # f3 gone, f9 new
    with pytest.raises(team.TeamHarnessError, match="line: expected stable units of the rest"):
        policy.decide(later)
