"""Proposed, not yet agreed: team members that own unit groups, and model members.

Real Python components with fake workers or fake transports; no game and no paid call.
"""
import json
import sys
import time
from functools import partial
from pathlib import Path
from threading import Event

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wh3_fixtures import CONFIG, USAGE, FakeMailbox, FakeSend, opening
from wh3_team_fixtures import Script, Workers, ack, make_team, move, state

from gameai.ledger import BudgetExhausted, Ledger
from gameai.llm import APIError, usage_cost
from twwarhammer3.battle import controllers, digest, export, llm, play, report, team, watch
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
    refusal = next(e for e in policy.drain_events() if e["event"] == "feedback")
    assert watch.Feed("e").lines({"kind": "team", **refusal}) == [
        f"        cavalry-1 refused: {refusal['ack']['validation_error']}"]
    reinforced = {**later, "seq": 3, "friendly": raw["friendly"] + [
        {"id": "f4", "type": team.SWORD, "x": 0, "z": 0, "bearing": 0, "men": 100}]}
    ack(policy)
    policy.decide(reinforced)  # a bought or summoned unit joins the member owning the rest
    assert policy.members["line"].units == {"f2", "f3", "f4"}


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


class Failing(Script):
    def __init__(self, error):
        super().__init__()
        self.error = error

    def decide(self, observation):
        raise self.error


@pytest.mark.parametrize("error,status,events", [
    (BudgetExhausted("cap"), "budget_exhausted", ["failed", "discarded"]),
    (APIError("HTTP 402: no credits"), "budget_exhausted", ["failed", "discarded"]),
    (APIError("team closed; request not sent"), "won", ["discarded"]),  # cut short, no forfeit
    (ValueError("member bug"), "policy_failure", ["failed", "discarded"]),
])
def test_a_call_collected_at_cleanup_is_discarded_and_a_stop_still_stops_the_job(
        tmp_path, error, status, events):
    policy = team.TeamPolicy({"infantry": (team.SWORD, Failing(error)),
                              "cavalry": (team.KNIGHT, Script())}, executor=Workers())
    mailbox = FakeMailbox([state(0, 0), state(1, 1000), state(2, 2000, result="won")])
    result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0},
                               lambda: policy, mailbox, not_battle=None)
    assert result["status"] == status and result["engine_ending"]["result"] == "won", result
    if status == "policy_failure":
        assert result["failure"]["member"] == "infantry"
    records = [json.loads(line) for line in (tmp_path / "e/trace.jsonl").open()]
    assert [e["event"] for e in records if e.get("member") == "infantry"
            and e.get("event") in ("failed", "discarded")] == events


def play_two(tmp_path, infantry, cavalry):
    """The infantry's first call ends at seq 2, the cavalry's only at cleanup."""
    workers = Workers()
    policy = team.TeamPolicy({"infantry": (team.SWORD, infantry),
                              "cavalry": (team.KNIGHT, cavalry)}, executor=workers)

    class Mailbox(FakeMailbox):
        def wait_observation(self, **kwargs):
            if self.queue[0]["seq"] == 2:
                workers.finish(0)
            return super().wait_observation(**kwargs)

    mailbox = Mailbox([state(0, 0), state(1, 1000), state(2, 2000, ack=True),
                       state(3, 3000, ack=True)])
    result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0},
                               lambda: policy, mailbox, not_battle=None)
    return result, [json.loads(line) for line in (tmp_path / "e/trace.jsonl").open()]


@pytest.mark.parametrize("first,late,status,error", [
    (ValueError("member bug"), BudgetExhausted("cap"), "policy_failure", "member bug"),
    (BudgetExhausted("cap"), ValueError("member bug"), "budget_exhausted", "cap"),
])
def test_a_failure_at_cleanup_keeps_an_earlier_failure(tmp_path, first, late, status, error):
    result, _ = play_two(tmp_path, Failing(first), Failing(late))
    assert result["status"] == status and error in result["error"]


def test_a_member_bug_at_cleanup_still_fails_a_truncated_episode(tmp_path, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(play.time, "time", lambda: clock[0])

    class Mailbox(FakeMailbox):
        def wait_observation(self, **kwargs):
            if not self.queue:
                clock[0] += 3600  # the episode's time runs out while it waits
            return super().wait_observation(**kwargs)

    policy = team.TeamPolicy({"infantry": (team.SWORD, Script()),
                              "cavalry": (team.KNIGHT, Failing(ValueError("member bug")))},
                             executor=Workers())
    result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0}, lambda: policy,
                               Mailbox([state(0, 0), state(1, 1000)]), not_battle=None)
    assert result["status"] == "policy_failure" and result["failure"]["member"] == "cavalry"


def test_a_failed_acknowledgement_is_not_also_discarded(tmp_path):
    class Deaf(Script):
        def acknowledge(self, ack, latency):
            raise ValueError("deaf")

    result, records = play_two(tmp_path, Deaf(), Script())
    assert result["status"] == "policy_failure" and "deaf" in result["error"]
    assert not [e for e in records if e.get("event") == "discarded" and e["member"] == "infantry"]


def test_a_peer_stop_is_collected_before_a_new_call_starts():
    policy, workers, _, _ = make_team(Script(), Failing(BudgetExhausted("cap")))
    policy.decide(state())
    workers.finish(0)
    policy.decide(state(2, 10100))  # the infantry's batch goes out
    ack(policy)
    workers.finish(1)
    with pytest.raises(BudgetExhausted):
        policy.decide(state(3, 10200))
    assert len(workers.tasks) == 2  # no new infantry call


def test_a_member_may_aim_an_ability_at_its_teammates_unit():
    raw = state()
    raw["friendly"][0]["abilities"] = [{"key": "aura", "can_use": True}]
    aura = [{"unit": "f2", "type": "ability", "ability": "aura", "target": "f1"}]
    policy, workers, _, _ = make_team(Script(aura))
    policy.decide(raw)
    workers.finish(0)
    assert policy.decide({**raw, "seq": 2, "time_ms": 10100}) == aura


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
    workers.finish(0)  # cavalry attacks e1, out of sight by dispatch: the engine refuses it
    later = battle(3, 12000, enemy=False)
    later["friendly"][0].update(  # f2's order state, which only its owner may see
        dest=[-20, 90], command_queue=[ADVANCE], attack_mode="melee",
        navigation={"rejected": {"x": 400, "z": 400}, "alternatives": [], "sampled_ms": 11000},
        fatigue="tired", morale={"fraction": .42, "effect": "flanked"})  # its teammate's too
    assert policy.decide({**later, "orders": rejected}) == [
        {"unit": "f1", "type": "attack", "target": "e1"}]
    policy.acknowledge({"request": "r2", "applied_ms": 12100, "results": [
        {"index": 1, "unit": "f1", "ok": False, "error": "target_not_visible"}]},
        {"delay_ms": 2100, "think_s": .1})
    policy.decide({**later, "seq": 4, "time_ms": 12200, "orders": rejected})
    workers.finish(2)
    workers.finish(3)
    seen = cavalry.metadata()["prompt"]
    assert "Last orders: f1 #1 rejected: target_not_visible." in seen
    assert "XYZZY" not in seen and "QQ" not in seen and "heading to" not in seen
    assert "tired, leadership 42%; largest effect: flanked" in seen
    assert "f2 #1 rejected: XYZZY" in line.metadata()["prompt"]
    assert "QQ" in line.metadata()["prompt"] and "heading to (-20, 90)" in line.metadata()["prompt"]
    inputs = [e["observation"] for e in policy.drain_events()
              if e["event"] == "input" and e["member"] == "cavalry"]
    assert len(inputs) == 2 and "XYZZY" not in json.dumps(inputs)
    assert not inputs[1]["allies"][0].keys() & {"dest", "command_queue", "navigation",
                                                "attack_mode"}


def test_a_batch_is_checked_on_its_members_source_not_the_dispatch_state(tmp_path):
    """As the single controller's: an enemy gone from sight by dispatch is the engine's to
    refuse, so the member's other orders still go."""
    orders = [move("f2"), {"unit": "f2", "type": "attack", "target": "e1", "queue": True}]
    policy, workers, infantry, _ = make_team(Script(orders), Script([]))

    class Mailbox(FakeMailbox):
        def wait_observation(self, **kwargs):
            if self.queue[0]["seq"] == 2:
                workers.finish(0)  # decided while e1 was in sight
            return super().wait_observation(**kwargs)

    mailbox = Mailbox([state(0, 0), state(1, 1000), state(2, 2000, ack=True, enemy=False),
                       state(3, 3000, ack=True, enemy=False), state(4, 4000, result="won")])
    result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0},
                               lambda: policy, mailbox, not_battle=None)
    assert result["status"] == "won", result
    assert [request[2] for request in mailbox.requests if request[2]] == [orders]
    assert infantry.feedback[0][1]["source"] == "engine"


@pytest.mark.parametrize("owner", [None, "cavalry"])
def test_only_a_member_without_the_army_and_with_every_unit_destroyed_is_not_asked(owner):
    policy, workers, _, _ = make_team(army_owner=owner)
    raw = state()
    raw["friendly"][1]["men"] = 0  # the Knights
    policy.decide(raw)
    assert len(workers.tasks) == (2 if owner else 1)
    raw["friendly"][1]["men"] = 30  # a living unit gives it something to order again
    policy.decide({**raw, "seq": 2, "time_ms": 11000})
    assert len(workers.tasks) == 2


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


def test_each_member_is_charged_counted_and_labelled_as_itself(tmp_path):
    usage = {"cavalry": dict(USAGE, input_tokens=100), "line": dict(USAGE, input_tokens=1000)}
    first = {"cavalry": [{"unit": "f1", "type": "attack", "target": "e1"}], "line": [ADVANCE]}
    bodies = []

    def send(body):  # the cavalry member owns f1, the line member f2
        bodies.append(body)
        prompt = body["input"][0]["content"]
        member = "cavalry" if "Your units:\n- f1 " in prompt else "line"
        text = reply(first[member] if len(bodies) <= 2 else [], notes=f"{member} NOTES")
        return {"id": f"r{len(bodies)}", "usage": usage[member], "output": [
            {"type": "message", "content": [{"type": "output_text", "text": text}]}]}

    workers = Workers()
    policy = model_team(tmp_path, send, executor=workers)

    class Mailbox(FakeMailbox):
        def wait_observation(self, **kwargs):
            # Both first calls end before seq 2, where e1 is hidden: the cavalry's attack is
            # still sent, decided while e1 was in sight. Its second call ends before seq 4.
            for index in {2: (0, 1), 4: (2,), 5: (3,)}.get(self.queue[0]["seq"], ()):
                workers.finish(index)
            return super().wait_observation(**kwargs)

    mailbox = Mailbox([battle(0, 0), battle(1, 1000), battle(2, 2000, ack=True, enemy=False),
                       battle(3, 3000, ack=True), battle(4, 4000, ack=True),
                       battle(5, 5000, result="won")])
    result = play.play_episode(tmp_path / "e", {**CONFIG, "policy": "team_llm_rules",
                                                "model": "gpt-6-luna", "effort": "low",
                                                "interval_ms": 0},
                               lambda: policy, mailbox, not_battle=None)
    assert result["status"] == "won" and [r[2] for r in mailbox.requests] == [
        [], first["cavalry"], [ADVANCE], []]
    cost = {name: 2 * usage_cost("gpt-6-luna", usage[name]) for name in usage}
    assert {name: (row["calls"], row["usd"], row["local_refusals"])
            for name, row in result["members"].items()} == {
        name: (2, pytest.approx(cost[name]), 0) for name in usage}
    assert result["llm"]["usd"] == pytest.approx(sum(cost.values()))
    assert len((tmp_path / "spend.jsonl").read_text().splitlines()) == 4
    # Both first batches came from the 1 s state; acknowledged at 2.5 s and 3.5 s.
    assert (result["decisions"], result["invalid"], result["delays_ms"]) == (2, 0, [1500, 2500])
    assert result["polls"]["decisions"] == 4 and result["polls"]["delays_ms"] == [500] * 3
    events = [json.loads(line) for line in (tmp_path / "e/trace.jsonl").open()]
    exchanges = sorted((e["member"], e["prompt"]) for e in events
                       if e["kind"] == "model_exchange")
    assert exchanges == sorted(
        ("cavalry" if "Your units:\n- f1 " in b["input"][0]["content"] else "line",
         b["input"][0]["content"]) for b in bodies)
    text = digest.digest(tmp_path / "e")
    assert "2 decisions" in text and "count member batches" in text
    assert text.splitlines()[-2:] == ["notes (cavalry): cavalry NOTES", "notes (line): line NOTES"]
    # A member's delay runs from its own source state, not from the dispatch.
    assert "[delay 1.5s]" in text and "[delay 2.5s]" in text and "[delay 0.5s]" not in text
    at = digest.decision_at(tmp_path / "e", 2)
    assert "state at 1.0 s" in at and "(delay 1.5 s)" in at
    feed = watch.Feed("e")
    lines = [line for event in events for line in feed.lines(event)]
    # Its second request was built from the 3 s state and dispatched at 4 s.
    assert any(line.startswith("    3s -> [cavalry] gpt-6-luna:") for line in lines)
    assert feed.usd == pytest.approx(result["llm"]["usd"])
    job = tmp_path / "job"  # report and export do not read member records yet
    job.mkdir()
    (tmp_path / "e").rename(job / "episode-0000")
    manifest = {"config": {"policy": "team_llm_rules", "model": "gpt-6-luna", "effort": "low"}}
    (job / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="team episodes"):
        report.collect([job])
    assert export.episode_records(job / "episode-0000", manifest, {})[1]["excluded"]
    path = job / "episode-0000/result.json"  # team evidence from before polls were recorded
    path.write_text(json.dumps({k: v for k, v in json.loads(path.read_text()).items()
                                if k != "polls"}))
    assert "describe dispatcher polls" in digest.digest(job / "episode-0000")


def test_a_member_caption_shows_the_state_it_decided_on():
    behavior = {"type": "llm", "model": "gpt-6-luna", "reason": "Go.", "member": "cavalry",
                "source_ms": 30000}
    assert play.caption(battle(5, 36000), behavior, [ADVANCE]) == (
        "36 s: cavalry (gpt-6-luna) from the state at 30 s\nGo.\nf2 move (10, 20)")


def test_think_time_runs_from_the_members_own_start():
    now = [10.0]

    class Slow(Script):
        def decide(self, observation):
            now[0] += .3
            return super().decide(observation)

    slow = Slow()
    policy, workers, _, _ = make_team(slow, Script([]), clock=lambda: now[0])
    policy.decide(state())
    now[0] += 1  # waiting to be run is not thinking
    workers.finish(0)
    policy.decide(state(2, 10100))
    ack(policy)
    assert slow.feedback[0][1]["think_s"] == pytest.approx(.3)
    assert policy.records()["think_s"] == [.3]


def test_a_local_refusal_counts_as_invalid(tmp_path):
    result, _ = play_two(tmp_path, Script([move("f1")]), Script())  # the infantry orders f1
    assert result["invalid"] == 1 and result["members"]["infantry"]["local_refusals"] == 1


@pytest.mark.parametrize("track", [{}, {"interval_ms": 0, "delay_ms": 1000}])  # CONFIG: 5 s
def test_a_team_refuses_an_interval_or_aged_track(tmp_path, track):
    result = play.play_episode(tmp_path / "e", {**CONFIG, **track}, team.DelayInfantry,
                               FakeMailbox([]), not_battle=None)
    assert result["status"] == "unsupported_or_invalid" and "teams require" in result["error"]


def test_the_team_version_follows_the_rules_prompt():
    rules = controllers.VERSIONS["llm_rules"]
    assert controllers.VERSIONS["team_llm_rules"].startswith(rules + "+t")

def test_a_member_whose_call_outlives_cleanup_says_so_in_its_record(tmp_path, monkeypatch):
    # Its cost and call reach only the ledger, so the record's usd and calls are short of it.
    monkeypatch.setattr(team, "CLOSE_WAIT_S", .2)
    entered, release = Event(), Event()

    def send(body):
        if "Your units:\n- f1 " in body["input"][0]["content"]:
            entered.set()
            assert release.wait(5)
        return {"id": "r", "usage": USAGE, "output": [
            {"type": "message", "content": [{"type": "output_text", "text": reply()}]}]}

    policy = model_team(tmp_path, send)
    try:
        policy.decide(battle(1, 10000))
        assert entered.wait(5)
        policy.members["line"].future.result(timeout=5)
        policy.close()
        members = policy.records()["members"]
    finally:
        release.set()
    assert {name: row["running_at_close"] for name, row in members.items()} == {
        "cavalry": True, "line": False}
    assert (members["cavalry"]["calls"], members["line"]["calls"]) == (0, 1)
