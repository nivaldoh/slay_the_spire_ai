"""Proposed, not yet agreed: team members that own unit groups, and model members.

Real Python components with fake workers or fake transports; no game and no paid call.
"""
import json
import time
from functools import partial
from threading import Event

import pytest
from test_wh3_play import CONFIG, FakeMailbox
from test_wh3_prompts import opening
from test_wh3_team import Script, Workers, ack, move, state
from wh3_fixtures import USAGE, FakeSend

from gameai.ledger import BudgetExhausted, Ledger
from gameai.llm import APIError
from twwarhammer3.battle import controllers, llm, play, team
from twwarhammer3.protocol import PolicyFailure

GUNS = "wh_main_emp_inf_handgunners"
HORN = {"unit": "army", "type": "ability", "ability": "horn", "target": None, "x": 0, "z": 0}
ADVANCE = {"unit": "f2", "type": "move", "x": 10, "z": 20}


def reply(orders=(), notes=None):
    return json.dumps({"orders": list(orders), "reason": "plan", "notes": notes})


def battle(seq, time_ms, **changes):
    """Swordsmen f2 (the line member's) and Knights f1 (the cavalry member's) against e1."""
    observation = state(seq, time_ms, **changes)
    del observation["terrain"]  # the scripted fixture's grid lacks the renderer's fields
    return observation


def model_team(tmp_path, send, **options):
    return team.ModelTeam("gpt-6-luna", "low", Ledger(tmp_path / "spend.jsonl", 1.0),
                          send=send, system_prompt="rules", **options)


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


def test_a_member_never_sees_its_teammate_feedback_notes_or_the_global_ack(tmp_path):
    send = FakeSend(reply([ADVANCE], notes="QQ"),
                    reply([{"unit": "f1", "type": "attack", "target": "e1"}]), reply(), reply())
    workers = Workers()
    policy = model_team(tmp_path, send, executor=workers)
    cavalry, line = policy.members["cavalry"].policy, policy.members["line"].policy
    policy.decide(battle(1, 10000))
    workers.finish(1)
    assert policy.decide(battle(2, 11000)) == [ADVANCE]
    rejected = {"request": "r1", "applied_ms": 11500,
                "results": [{"index": 1, "unit": "f2", "ok": False, "error": "XYZZY"}]}
    policy.acknowledge(rejected, {"delay_ms": 500, "think_s": .1})
    workers.finish(0)  # cavalry attacks e1, out of sight when its batch is checked
    policy.decide({**battle(3, 12000, enemy=False), "orders": rejected})
    workers.finish(2)
    workers.finish(3)
    seen = cavalry.metadata()["prompt"]
    assert "Last orders: f1 #1 rejected: f1: target 'e1' is not visible." in seen
    assert "XYZZY" not in seen and "QQ" not in seen
    assert "f2 #1 rejected: XYZZY" in line.metadata()["prompt"]
    assert "QQ" in line.metadata()["prompt"]
    inputs = [e["observation"] for e in policy.drain_events()
              if e["event"] == "input" and e["member"] == "cavalry"]
    assert len(inputs) == 2 and "XYZZY" not in json.dumps(inputs)


def test_cleanup_is_bounded_sends_nothing_new_and_leaves_a_running_member_open(
        tmp_path, monkeypatch):
    monkeypatch.setattr(team, "CLOSE_WAIT_S", .2)
    entered, release, bodies, closed = Event(), Event(), [], []

    def send(body):
        bodies.append(body)
        text = reply()
        if "Your units:\n- f1 " in body["input"][0]["content"]:
            entered.set()
            assert release.wait(5)
            text = "not json"  # rejected: the member would ask again
        return {"id": "r", "usage": USAGE, "output": [
            {"type": "message", "content": [{"type": "output_text", "text": text}]}]}

    policy = model_team(tmp_path, send)
    for name, member in policy.members.items():
        member.policy.close = partial(closed.append, name)
    try:
        policy.decide(battle(1, 10000))
        assert entered.wait(5)
        policy.members["line"].future.result(timeout=5)
        started = time.monotonic()
        policy.close()
        assert time.monotonic() - started < 1
    finally:
        release.set()
    assert isinstance(policy.members["cavalry"].future.exception(timeout=5), PolicyFailure)
    assert len(bodies) == 2 and closed == ["line"]
    assert policy.members["line"].policy.api.ledger.held == 0
    discarded = {e["member"]: e for e in policy.drain_events() if e["event"] == "discarded"}
    assert discarded["cavalry"]["running"] is True and discarded["line"]["running"] is False


def test_the_team_policy_shares_the_job_ledger_and_plays_the_rules_prompt(tmp_path,
                                                                          monkeypatch):
    monkeypatch.setattr(controllers, "api_key", lambda provider="openai": "test-only")
    (tmp_path / "spend.jsonl").touch()
    config = {"policy": "llm_rules,team_llm_rules", "model": "gpt-6-luna", "effort": "low",
              "ledger": str(tmp_path / "spend.jsonl"), "budget_usd": 1}
    makers = controllers.factories(config)
    single, policy = makers["llm_rules"](), makers["team_llm_rules"]()
    cavalry, line = (member.policy for member in policy.members.values())
    assert cavalry.api.ledger is line.api.ledger is single.api.ledger
    assert cavalry.api is not line.api
    assert cavalry.api.instructions == line.api.instructions == llm.RULES_PROMPT_PATH.read_text()
    card = controllers.card("team_llm_rules", policy, config)
    assert (card["kind"], card["cost_source"], card["timing"], card["model"]) == (
        "model", "WH3 ledger", "asynchronous", "gpt-6-luna")
    assert card["disclosure"]["max_age_ms"] is None
    assert card["disclosure"]["army_owner"] == "line" and card["disclosure"]["paid_calls"]
    policy.close()
