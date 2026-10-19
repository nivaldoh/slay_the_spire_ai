import json
import threading
from concurrent.futures import wait

import pytest
from wh3_fixtures import USAGE, observation

from gameai.ledger import BudgetExhausted, Ledger
from twwarhammer3.battle.commander import CommanderPolicy
from twwarhammer3.protocol import PolicyFailure


class GatedSend:
    """Replies in order, each only after the test releases it."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.bodies = []
        self.gate = threading.Semaphore(0)

    def __call__(self, body):
        self.bodies.append(body)
        assert self.gate.acquire(timeout=5)
        return {"id": "resp", "status": "completed", "usage": USAGE,
                "output": [{"type": "message", "content": [{"type": "output_text",
                                                             "text": self.replies.pop(0)}]}]}


def plan(assignments=(), abilities=(), reason="go", notes=None):
    return json.dumps({"assignments": [
        {"unit": "f2", "skill": "engage", "target": None, "x": None, "z": None, **item}
        for item in assignments], "abilities": list(abilities), "reason": reason, "notes": notes})


def commander(tmp_path, *replies, budget=1.0):
    send = GatedSend(*replies)
    agent = CommanderPolicy("gpt-6-luna", "low", Ledger(tmp_path / "ledger.jsonl", budget),
                            send=send, system_prompt="Command well.")
    agent.fake = send
    return agent


def answer(agent):
    """Let the request in flight return, and wait until it has."""
    agent.fake.gate.release()
    wait([agent.pending], timeout=5)


def finish(agent):
    agent.fake.gate.release(len(agent.fake.replies) + 1)
    agent.close()


def test_decide_never_waits_and_keeps_one_request_in_flight(tmp_path):
    agent = commander(tmp_path, plan(), plan())
    orders = agent.decide(observation(30000))
    assert orders == [{"unit": "f2", "type": "attack", "target": "e1", "mode": "melee",
                       "run": False, "queue": False}]
    assert agent.skills.assignments["f1"]["skill"] == "charge"
    assert "Units follow their default skills" in agent.metadata()["prompt"]
    # f2's attack was sent this tick: the state cannot show it yet, so it is not annotated.
    assert "your order" not in agent.metadata()["prompt"]
    assert agent.decide(observation(31000)) == []
    assert "prompt" not in agent.metadata()
    answer(agent)
    agent.decide(observation(34000))
    meta = agent.metadata()
    assert meta["plan_age_s"] == 4.0 and "battle time 34 s" in meta["prompt"]
    assert "last plan reached the units 4.0 s after" in meta["prompt"]
    assert "state 30 s, adopted 34 s: no changes (go)" in meta["prompt"]
    assert "- f1 charge (since 30 s): waiting for melee" in meta["prompt"]
    body = agent.fake.bodies[0]
    assert body["instructions"] == "Command well."
    assert body["text"]["format"]["strict"] is True
    assert "assignments" in body["text"]["format"]["schema"]["properties"]
    finish(agent)


def test_plans_are_checked_against_the_state_they_arrive_in(tmp_path):
    reply = plan([{"unit": "f9"}, {"unit": "f1", "skill": "move"},
                  {"unit": "f2", "skill": "shoot"}, {"unit": "f1", "target": "e9"},
                  {"unit": "f2", "skill": "charge", "target": "e2", "x": 5, "z": -60}])
    agent = commander(tmp_path, reply, plan())
    agent.decide(observation(30000))
    answer(agent)
    agent.decide(observation(36000))
    assert agent.metadata()["dropped"] == [
        "f9 engage: no such unit alive", "f1 move: a move needs x and z",
        "f2 shoot: the unit has no missiles",
        "f1 engage e9: target e9 is not a live enemy, so it was cleared"]
    assert agent.skills.assignments["f1"] == {"skill": "engage", "target": None, "x": None,
                                              "z": None, "since_s": 36.0}
    # e2 is in the roster but not visible: the assignment keeps it, and acts without it.
    assert agent.skills.assignments["f2"]["target"] == "e2"
    assert agent.skills.phase["f2"] == "waiting for melee (e2 out of sight), moving to post"
    assert "dropped f2 shoot: the unit has no missiles" in agent.metadata()["prompt"]
    answer(agent)
    agent.decide(observation(40000))
    # Units the plan leaves out keep their assignments.
    assert agent.skills.assignments["f2"]["target"] == "e2"
    assert "(none)" in agent.metadata()["prompt"].split("Dropped or rejected")[1][:60]
    finish(agent)


def test_assignments_may_leave_out_target_and_point(tmp_path):
    reply = json.dumps({"assignments": [{"unit": "f2", "skill": "hold"}], "abilities": [],
                        "reason": "go", "notes": None})
    agent = commander(tmp_path, reply, plan())
    agent.decide(observation(30000))
    answer(agent)
    agent.decide(observation(33000))
    assert agent.metadata()["dropped"] == []
    assert agent.skills.assignments["f2"]["skill"] == "hold"
    finish(agent)


def test_only_abilities_builds_reinforcements_and_flight_go_in_abilities(tmp_path):
    move = {"unit": "f2", "type": "move", "x": 5, "z": 1}
    agent = commander(tmp_path, plan(abilities=[move]), plan())
    agent.decide(observation(30000))
    answer(agent)
    orders = agent.decide(observation(33000))
    assert move not in orders and agent.metadata()["abilities"] == []
    assert agent.metadata()["dropped"] == [
        "f2 move (5, 1): not an ability, build, reinforce or flight order"]
    finish(agent)


def test_abilities_are_revalidated_and_sent_once(tmp_path):
    roar = {"unit": "f1", "type": "ability", "ability": "roar", "target": None, "x": None,
            "z": None, "facing": None, "width": None}
    agent = commander(tmp_path, plan(abilities=[roar, dict(roar, ability="fly")]), plan())
    state = observation(30000)
    state["friendly"][0]["abilities"] = [{"key": "roar", "can_use": True}]
    agent.decide(state)
    answer(agent)
    orders = agent.decide(dict(state, time_ms=33000))
    assert orders[-1] == roar and len(orders) == 2
    assert agent.metadata()["dropped"] == ["f1 ability fly at self: f1: unavailable ability 'fly'"]
    assert roar not in agent.decide(dict(state, time_ms=33500))
    finish(agent)


def test_engine_rejections_reach_the_next_prompt(tmp_path):
    agent = commander(tmp_path, plan(), plan())
    agent.decide(observation(30000))
    agent.acknowledge({"results": [{"index": 1, "unit": "f2", "ok": False,
                                    "error": "unreachable"}]}, {})
    answer(agent)
    agent.decide(observation(35000))
    assert "engine rejected f2 attack e1 melee: unreachable" in agent.metadata()["prompt"]
    finish(agent)


def test_close_waits_for_the_call_in_flight(tmp_path):
    agent = commander(tmp_path, plan())
    agent.decide(observation(30000))
    threading.Timer(0.05, agent.fake.gate.release).start()
    agent.close()
    assert agent.totals["calls"] == 1 and "plans" not in agent.totals


def test_budget_and_invalid_replies_surface_from_decide(tmp_path):
    broke = commander(tmp_path, budget=0.0)
    broke.decide(observation(30000))
    wait([broke.pending], timeout=5)
    with pytest.raises(BudgetExhausted):
        broke.decide(observation(31000))
    finish(broke)
    garbled = commander(tmp_path, "not json", "still not json", plan())
    garbled.decide(observation(30000))
    garbled.fake.gate.release()
    answer(garbled)
    with pytest.raises(PolicyFailure) as failure:
        garbled.decide(observation(31000))
    assert failure.value.failure["kind"] == "invalid_reply"
    assert len(failure.value.failure["attempts"]) == 2
    garbled.decide(observation(32000))  # it surfaces once; the next tick asks again
    assert "battle time 32 s" in garbled.metadata()["prompt"]
    finish(garbled)


@pytest.mark.parametrize(("bad", "message"), [
    ([], "reply must be a JSON object"),
    ({"assignments": [], "abilities": [], "reason": "go"}, "reply has no 'notes' field"),
    ({"assignments": {}, "abilities": [], "reason": "go", "notes": None},
     "reply field 'assignments' must be array"),
    ({"assignments": [], "abilities": [], "reason": True, "notes": None},
     "reply field 'reason' must be string"),
    ({"assignments": ["f2 engage"], "abilities": [], "reason": "go", "notes": None},
     "assignment 1 must be a JSON object"),
    (json.loads(plan([{"skill": "dance"}])), "assignment 1 field 'skill' must be one of"),
    (json.loads(plan([{"skill": "move", "x": "5", "z": 1}])),
     "assignment 1 field 'x' must be number or null"),
    (json.loads(plan([{"skill": "move", "x": float("nan"), "z": 1}])),
     "assignment 1 field 'x' must be number or null"),
    (json.loads(plan([{"skill": "move", "x": 10**400, "z": 1}])),
     "assignment 1 field 'x' must be number or null"),
    ({"assignments": [{"unit": "f2", "target": None}], "abilities": [], "reason": "go",
      "notes": None}, "assignment 1 has no 'skill' field"),
])
def test_off_schema_plans_are_retried_then_fail_as_policy_failure(tmp_path, bad, message):
    # Open-weight backends need not enforce the strict schema; a strict one does.
    bad = json.dumps(bad)
    agent = commander(tmp_path, bad, plan(), plan())
    agent.decide(observation(30000))
    agent.fake.gate.release()
    answer(agent)
    agent.decide(observation(31000))
    error, retried = [a.get("error") for a in agent.metadata()["attempts"]]
    assert error.startswith(message) and retried is None
    assert f"previous reply was invalid: {message}" in agent.fake.bodies[1]["input"][0]["content"]
    finish(agent)
    failing = commander(tmp_path, bad, bad)
    failing.decide(observation(30000))
    failing.fake.gate.release()
    answer(failing)
    with pytest.raises(PolicyFailure) as failure:
        failing.decide(observation(31000))
    assert failure.value.failure["kind"] == "invalid_reply"
    assert [a["error"][:len(message)] for a in failure.value.failure["attempts"]] == [message] * 2
    finish(failing)
