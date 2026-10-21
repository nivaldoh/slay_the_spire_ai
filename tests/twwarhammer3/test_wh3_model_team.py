"""Proposed, not yet agreed: team members that own unit groups, and model members.

Real Python components with fake workers or fake transports; no game and no paid call.
"""
import json

import pytest
from test_wh3_play import CONFIG, FakeMailbox
from test_wh3_prompts import opening
from test_wh3_team import Script, Workers, ack, move, state

from gameai.ledger import BudgetExhausted
from gameai.llm import APIError
from twwarhammer3.battle import llm, play, team
from twwarhammer3.protocol import PolicyFailure

GUNS = "wh_main_emp_inf_handgunners"
HORN = {"unit": "army", "type": "ability", "ability": "horn", "target": None, "x": 0, "z": 0}


def test_a_view_of_every_unit_renders_the_single_controller_prompt():
    raw = opening()
    every = {unit["id"] for unit in raw["friendly"]}
    args = ("notes", ["20 s: f1 halt (wait)"], {}, None, None)
    assert llm.render_prompt(team.project(raw, every, army=True), *args) == llm.render_prompt(
        raw, *args)
    member = llm.render_prompt(team.project(raw, {"f2"}), *args)
    assert "Army abilities" not in member and "Building slots" not in member
    assert "Supplies" not in member and "Capture points" in member
    del raw["terrain"]
    assert "Terrain" not in llm.render_prompt(team.project(raw, every), *args)


def test_grouped_members_order_their_own_units_and_only_the_owner_the_army():
    raw = state()
    raw["friendly"].append({"id": "f3", "type": GUNS, "x": -20, "z": 0, "bearing": 0,
                            "men": 80, "state": []})
    raw["army"] = {"abilities": [{"key": "horn", "target": "Ground", "ready": True}]}
    raw["mode"] = {"type": "land_normal", "supplies": 500}
    cavalry, line = Script([HORN]), Script([{"unit": "f3", "type": "halt"}, HORN])
    workers = Workers()
    policy = team.TeamPolicy({"cavalry": ((team.KNIGHT,), cavalry), "line": (None, line)},
                             army_owner="line", max_age_ms=None, executor=workers)
    policy.decide(raw)
    workers.finish(0)
    workers.finish(1)
    assert [u["id"] for u in cavalry.inputs[0]["friendly"]] == ["f1"]
    assert [u["id"] for u in line.inputs[0]["friendly"]] == ["f2", "f3"]
    assert "army" not in cavalry.inputs[0] and "supplies" not in cavalry.inputs[0]["mode"]
    assert line.inputs[0]["army"] == raw["army"] and line.inputs[0]["mode"]["supplies"] == 500
    later = {**raw, "seq": 2, "time_ms": 70000}  # no age limit
    assert policy.decide(later) == line.orders
    assert "army" in cavalry.feedback[0][0]["validation_error"]
    reinforced = {**later, "seq": 3, "friendly": raw["friendly"] + [
        {"id": "f4", "type": team.SWORD, "x": 0, "z": 0, "bearing": 0, "men": 100}]}
    ack(policy)
    with pytest.raises(team.TeamHarnessError):
        policy.decide(reinforced)


@pytest.mark.parametrize("error,status", [
    (PolicyFailure("No valid reply after declared retries"), "won"),
    (APIError("HTTP 503: busy"), "won"),
    (APIError("HTTP 402: no credits"), "budget_exhausted"),
    (BudgetExhausted("cap"), "budget_exhausted"),
    (ValueError("member bug"), "policy_failure"),
])
def test_a_member_failure_is_a_forfeit_or_ends_the_episode_like_the_single_controller(
        tmp_path, error, status):
    class Failing(Script):
        def decide(self, observation):
            if not self.inputs:
                self.inputs.append(observation)
                raise error
            return super().decide(observation)

    a, workers = Failing(), Workers()
    policy = team.TeamPolicy({"infantry": (team.SWORD, a), "cavalry": (team.KNIGHT, Script())},
                             executor=workers)

    class Mailbox(FakeMailbox):
        def wait_observation(self, **kwargs):
            seq = self.queue[0]["seq"]
            if seq in (2, 3):
                workers.finish({2: 0, 3: 2}[seq])  # the first call fails, a forfeit's retry
            return super().wait_observation(**kwargs)

    mailbox = Mailbox([state(0, 0), state(1, 1000), state(2, 2000, ack=True),
                       state(3, 3000, ack=True), state(4, 4000, result="won")])
    result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0},
                               lambda: policy, mailbox, not_battle=None)
    assert result["status"] == status, result
    assert len(a.inputs) == (2 if status == "won" else 1)
    if status == "won":
        assert [r[2] for r in mailbox.requests] == [[], [], [move("f2")]]
    events = [json.loads(line) for line in (tmp_path / "e/trace.jsonl").open()]
    failed, = [e for e in events if e.get("event") == "failed"]
    assert failed["member"] == "infantry" and failed["decision"] == "infantry-1"
