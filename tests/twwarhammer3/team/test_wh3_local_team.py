"""C's local information, asynchronous delivery and model interface; no live game."""

import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wh3_fixtures
from wh3_fixtures import CONFIG, FakeSend
from wh3_team_fixtures import Script, Workers, ack

from gameai.ledger import Ledger
from twwarhammer3.battle import controllers, llm, local_team, play, setup
from twwarhammer3.battle import local_command as local
from twwarhammer3.protocol import PolicyFailure


def scenario(arm="bounded"):
    suffix = "" if arm == "bounded" else f"-{arm}"
    return setup.scenarios()[f"emp-envelopment-c{suffix}-v1"]


def state(seq=1, time_ms=5200):
    placements = scenario()["deployment"]["friendly"]
    return {"schema": 1, "battle": "b1", "seq": seq, "time_ms": time_ms,
            "phase": "Deployed", "speed": 1, "remaining_ms": 1200000 - time_ms,
            "friendly": [dict(p, id=f"f{i+1}", men=90, men0=90, state=[], hp=1)
                         for i, p in enumerate(placements)],
            "enemy_roster": [{"id": "e1", "type": "sword"}, {"id": "e2", "type": "horse"}],
            "enemy": [{"id": "e1", "type": "sword", "x": 170, "z": -175, "men": 90},
                      {"id": "e2", "type": "horse", "x": 400, "z": -465, "men": 45}],
            "mode": {"type": "land_normal", "role": "defender"}}


class Sender(Script):
    def __init__(self, messages=None, orders=None):
        super().__init__(orders)
        self.messages = messages or []
        self.guards = []

    def drain_messages(self):
        messages, self.messages = self.messages, []
        return messages

    def dispatch_guard(self, orders, latest):
        self.guards.append(deepcopy(latest))


def team(*, arm="bounded", centre=None, **options):
    policies = {name: Sender() for name in local.GROUP_SLOTS}
    if centre is not None:
        policies["centre"] = centre
    workers = Workers()
    policy = local_team.LocalTeam(policies, scenario=scenario(arm), executor=workers, **options)
    return policy, workers, policies


def test_blocked_peer_does_not_stop_orders_or_mutate_its_pending_prompt():
    sender = Sender([{"channel": "signal", "code": "HELP"}])
    policy, workers, policies = team(centre=sender)
    try:
        assert policy.decide(state()) == []
        old_left = deepcopy(workers.tasks[1][2][1])
        workers.finish(0)
        assert policy.decide(state(2, 5500))[0]["unit"] == "f1"
        ack(policy, applied=5600)
        assert policy.decide(state(3, 8000)) == []
        assert workers.tasks[1][2][1] == old_left
        assert old_left["command"]["received"] == []
        assert all(not workers.tasks[i][0].done() for i in (1, 2, 3, 4))
        workers.finish(1)
        assert policy.decide(state(4, 8500))[0]["unit"] == "f5"
        ack(policy, applied=8600)
        policy.decide(state(5, 9000))
        left = next(args[1] for future, fn, args in reversed(workers.tasks)
                    if args[0] is policy.members["left_infantry"])
        received = left["command"]["received"]
        assert len(received) == 1 and received[0]["code"] == "HELP"
        assert received[0]["source_ms"] == 5200
        assert received[0]["sent_ms"] == 5500 and received[0]["arrived_ms"] == 8000
        assert policies["centre"].guards[0]["enemy"] == [state()["enemy"][0]]
        assert "e2" not in json.dumps(policies["centre"].guards[0]["enemy"])
    finally:
        policy.close()


@pytest.mark.parametrize("change", ("foreign_order", "stale"))
def test_local_ownership_and_source_age_refusals_do_not_reveal_other_units(change):
    sender = Sender(orders=[{"unit": "f9", "type": "halt"}] if change == "foreign_order" else None)
    # This tests hidden coordinates, not wall timing. Real latency decimals can contain
    # "400" by chance; engine-time source ages below still exercise expiry independently.
    policy, workers, _ = team(centre=sender, max_age_ms=5000, clock=lambda: 0)
    try:
        policy.decide(state())
        workers.finish(0)
        later = state(2, 11000 if change == "stale" else 5500)
        assert policy.decide(later) == []
        assert policy.members["centre"].local_refusals == 1
        assert sender.feedback[0][0]["results"][0]["ok"] is False
        assert "400" not in json.dumps(sender.feedback)
    finally:
        policy.close()


def test_identity_is_stable_after_movement_and_wrong_episode_is_refused():
    policy, workers, _ = team()
    try:
        policy.decide(state())
        groups = deepcopy(policy.groups)
        moved = state(2, 5500)
        moved["friendly"].reverse()
        for unit in moved["friendly"]:
            unit["x"] += 200
        policy.decide(moved)
        assert policy.groups == groups
        moved["battle"] = "b2"
        with pytest.raises(local_team.TeamHarnessError, match="identity changed"):
            policy.decide(moved)
    finally:
        policy.close()


def test_close_discards_completed_but_unsent_messages():
    policy, workers, _ = team(centre=Sender([{"channel": "signal", "code": "HELP"}]))
    policy.decide(state())
    policy.close()  # fake shutdown finishes every pending worker
    assert not policy.router.pending and all(not v for v in policy.router.inboxes.values())
    assert any(e["event"] == "message_discarded" for e in policy.drain_events())


def test_probe_moves_left_infantry_only_after_a_centre_courier_enters_its_next_input():
    workers = Workers()
    policy = local_team.ProbeTeam(scenario=scenario(), executor=workers)
    try:
        policy.decide(state())
        workers.finish(0)
        assert policy.decide(state(2, 5500)) == []
        ack(policy, applied=5600)
        workers.finish(1)  # initial left input predates delivery and only sends its own mail
        assert policy.decide(state(3, 12000)) == []
        ack(policy, applied=12100)
        policy.decide(state(4, 12500))
        index = next(i for i in range(len(workers.tasks) - 1, -1, -1)
                     if workers.tasks[i][2][0] is policy.members["left_infantry"])
        workers.finish(index)
        orders = policy.decide(state(5, 12800))
        assert orders == [{"unit": "f5", "type": "move", "x": 40, "z": -125, "run": True}]
        assert policy.metadata()["cue"]["sender"] == "centre"
        assert policy.metadata()["cue"]["source_ms"] == 5200
        assert policy.metadata()["cue"]["arrived_ms"] == 12000
    finally:
        policy.close()


def test_probe_second_input_without_a_courier_keeps_left_infantry_stationary():
    policy, _, _ = team()
    try:
        policy._partition(state())
        view = policy._view(state(), policy.members["left_infantry"], for_input=True)
        member = local_team.ProbeMember()
        assert member.decide(view) == []
        member.drain_messages()
        later = deepcopy(view)
        later.update(seq=2, time_ms=6000)
        assert later["command"]["received"] == []
        assert member.decide(later) == []
        assert member.metadata()["cue"] is None
    finally:
        policy.close()


def test_stale_target_feedback_does_not_distinguish_distant_alive_from_distant_dead():
    feedback = []
    for men in (90, 0):
        sender = Sender(orders=[{"unit": "f1", "type": "attack", "target": "e1"}])
        policy, workers, _ = team(centre=sender)
        try:
            policy.decide(state())
            workers.finish(0)
            latest = state(2, 5500)
            latest["enemy"][0].update(x=700, men=men)
            assert policy.decide(latest) == []
            feedback.append(sender.feedback[0])
        finally:
            policy.close()
    assert feedback[0][0] == feedback[1][0]
    assert feedback[0][0]["results"][0]["ok"] is False


def test_all_four_c_conditions_keep_physical_setup_fixed_and_change_only_declared_interface():
    base = scenario()
    for arm in ("bounded", "silent", "fast", "global"):
        entry = scenario(arm)
        for key in ("deployment", "player", "enemy", "expect", "map"):
            assert entry[key] == base[key]
        policy, _, _ = team(arm=arm)
        try:
            policy.decide(state())
            view = policy._view(state(), policy.members["centre"], for_input=False)
            assert len(view["enemy"]) == (2 if arm == "global" else 1)
            assert policy.router.enabled is (arm not in {"silent", "global"})
        finally:
            policy.close()


def test_a_global_controller_is_refused_for_c_before_any_environment_read(tmp_path, monkeypatch):
    monkeypatch.setattr(play, "collect_diagnostics", lambda: pytest.fail("environment read"))
    config = {**CONFIG, "policy": "hold", "scenario": "emp-envelopment-c-v1",
              "episode_timeout": 1320, "run_timeout": 2000}
    with pytest.raises(ValueError, match="requires.*local_team"):
        play.play(tmp_path / "job", config, makers={"hold": lambda: None})
    assert not (tmp_path / "job").exists()


def test_configured_model_members_share_ledger_but_have_private_notes_and_local_prompts(
        tmp_path, monkeypatch):
    send = FakeSend(json.dumps({"orders": [{"unit": "f1", "type": "halt"}],
                                "reason": "hold", "notes": "my private report",
                                "messages": [{"channel": "signal", "code": "READY"}]}))
    monkeypatch.setattr(controllers, "api_key", lambda *a: "unused")
    monkeypatch.setattr(controllers, "post", lambda key, body, **kwargs: send(body))
    path = setup.SCENARIOS_PATH.parent / "controllers/cannae-local-model.json"
    config = {"policy": "configured", "controller_config": str(path),
              "scenario": "emp-envelopment-c-v1", "model": "gpt-6-luna", "effort": "low",
              "ledger": str(tmp_path / "spend.jsonl"), "budget_usd": 1}
    Path(config["ledger"]).touch()
    policy = controllers.factories(config)["configured"]()
    try:
        policy._partition(state())
        centre = policy.members["centre"].policy
        view = policy._view(state(), policy.members["centre"], for_input=True)
        assert centre.decide(view) == [{"unit": "f1", "type": "halt"}]
        assert centre.drain_messages() == [{"channel": "signal", "code": "READY"}]
        assert centre.notes == "my private report"
        others = [m.policy for n, m in policy.members.items() if n != "centre"]
        assert all(m.notes == "" for m in others)
        assert all(m.api.ledger is centre.api.ledger for m in others)
        body = send.bodies[0]
        assert body["instructions"].endswith(local_team.PROMPT_PATH.read_text())
        assert body["text"]["format"]["schema"]["properties"]["messages"]["maxItems"] == 2
        prompt = json.loads(body["input"][0]["content"])
        assert prompt["observation"]["command"]["member"] == "centre"
        assert {u["id"] for u in prompt["observation"]["friendly"]} == {"f1", "f2", "f3", "f4"}
        assert "e2" not in json.dumps(prompt["observation"]["enemy"])
        assert len(policy.card["model_prompts"]) == 1
    finally:
        policy.close()


class QuietPolls(wh3_fixtures.FakeMailbox):
    """Observations 300 ms apart from 5200 ms, each acknowledging the last request. ``finish``
    maps a time to the call that runs as that observation is read; with ``result_in_call`` the
    result is already published when the decide call on the last observation returns."""

    def __init__(self, finish, last_ms, result_in_call):
        super().__init__([])
        self.finish, self.last_ms, self.result_in_call = finish, last_ms, result_in_call
        self.seq, self.ms = 1, 5200

    def wait_new_battle(self, *, not_battle, timeout):
        return state(0, 5000)

    def wait_observation(self, *, battle, after_seq, timeout):
        if self.ms > self.last_ms:
            return {**state(self.seq, self.ms), "result": "lost", "final": {}}
        item = state(self.seq, self.ms)
        if self.pending:
            item["orders"] = {"request": self.pending[0], "based_on": 0,
                              "applied_ms": self.ms, "results": []}
            self.pending = None
        if self.ms in self.finish:
            self.finish[self.ms]()
        self.seq, self.ms = self.seq + 1, self.ms + 300
        return item

    def read_observation(self):
        return {"result": "lost"} if self.result_in_call and self.ms > self.last_ms else None


class Forfeits(Sender):
    def decide(self, observation):
        raise PolicyFailure("no valid reply")


SIGNAL = {"channel": "signal", "code": "READY"}


# Found in c-model-smoke-02: 2 of 729 inputs and 184 of 640 arrivals had no frame. Members stay
# idle, because a scripted member that replies on every poll never leaves a quiet poll.
@pytest.mark.parametrize("centre,finish_ms,poll_ms,last_ms,result_in_call", [
    (lambda: Sender([SIGNAL], []), 5500, 7600, 8000, False),  # sent 5500, due 7500
    (Forfeits, 6100, 6100, 6700, False),  # the retry input lands on the forfeit's quiet poll
    (lambda: Sender([SIGNAL], []), 5500, 7600, 7600, True),  # the arrival poll closes the battle
], ids=["signal-arrival", "forfeit-retry", "closing-race"])
def test_a_quiet_poll_that_writes_team_rows_keeps_its_global_frame(
        tmp_path, centre, finish_ms, poll_ms, last_ms, result_in_call):
    policy, workers, _ = team(centre=centre())
    mailbox = QuietPolls({finish_ms: lambda: workers.finish(0)}, last_ms, result_in_call)
    play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0, "policy": "configured"},
                      lambda: policy, mailbox, not_battle=None)
    rows = [json.loads(line) for line in (tmp_path / "e/trace.jsonl").open()]
    framed = {row["observation"]["time_ms"] for row in rows
              if row["kind"] in ("roster", "observation")}
    sources = {row.get("source_ms", row.get("time_ms")) for row in rows if row["kind"] == "team"
               and row["event"] in ("input", "communication")}
    assert poll_ms in sources and sources <= framed


@pytest.mark.parametrize("bad", ({"orders": []}, [], {"orders": [], "reason": "wait",
                                                  "notes": None, "messages": [None]}))
def test_malformed_model_envelopes_are_forfeits_instead_of_python_crashes(tmp_path, bad):
    policy = llm.LLMPolicy("gpt-6-luna", "low", Ledger(tmp_path / "spend.jsonl", 1),
                           send=FakeSend(json.dumps(bad)))
    member = local_team.LocalModel(policy)
    with pytest.raises(PolicyFailure):
        member.decide(state())


class MemberSend(FakeSend):
    """Keeps each member's real requests. Centre halts f1, left infantry sends a near and a far
    courier, and every member writes its own notes."""

    def __init__(self):
        super().__init__()
        self.requests = {}

    def __call__(self, body):
        member = json.loads(body["input"][0]["content"])["observation"]["command"]["member"]
        self.requests.setdefault(member, []).append(body)
        orders = [{"unit": "f1", "type": "halt"}] if member == "centre" else []
        mail = [{"channel": "courier", "to": to, "text": "Peer report"}
                for to in ("decisive_cavalry", "right_infantry") if member == "left_infantry"]
        self.replies = [json.dumps({"orders": orders, "reason": f"{member} reason",
                                    "notes": f"{member} private notes", "messages": mail})]
        return super().__call__(body)


def centre_second_request(ledger, change=lambda observation: None, *, peer_replied=False):
    """Centre's second full model request, after its first order's feedback, from real
    LocalModels in a real LocalTeam. `change` edits each frame after the binding one."""
    def frame(seq, time_ms):
        observation = state(seq, time_ms)
        observation["magic"] = {"current": 40, "reserve": 60}
        for unit in observation["friendly"]:
            unit["morale"] = {"fraction": .9, "effect": "Steady"}
        if seq > 1:
            observation["orders"] = {"request": "r0", "based_on": 0, "applied_ms": 5000,
                                     "results": []}
            change(observation)
        return observation

    send, ledger, workers = MemberSend(), Ledger(ledger, 1), Workers()
    members = {name: local_team.LocalModel(llm.LLMPolicy("gpt-6-luna", "low", ledger, send=send))
               for name in local.GROUP_SLOTS}
    policy = local_team.LocalTeam(members, scenario=scenario(), executor=workers,
                                  clock=lambda: 0)

    def finish(name):
        workers.finish(next(i for i, (future, _, args) in enumerate(workers.tasks)
                            if args[0] is policy.members[name] and not future.done()))

    try:
        policy.decide(frame(1, 5200))
        finish("centre")
        if peer_replied:
            finish("containing_cavalry")
            finish("left_infantry")
        assert policy.decide(frame(2, 5500)) == [{"unit": "f1", "type": "halt"}]
        ack(policy, applied=5600)
        policy.decide(frame(3, 12000))
        ack(policy, applied=12100)  # the peer's batch when it replied, else an idle poll
        finish("centre")
        if peer_replied:  # the peer mail compared: one courier unread, one still travelling
            assert [m["text"] for m in policy.router.inbox("decisive_cavalry")] == ["Peer report"]
            assert [p["recipients"] for p in policy.router.pending] == [["right_infantry"]]
        return send.requests["centre"][1]
    finally:
        policy.close()


def test_distant_state_and_peer_memory_leave_the_full_request_byte_identical_up_to_a_cue(tmp_path):
    def distant(observation):
        observation["magic"] = {"current": 1, "reserve": 2}
        # Lua's last applied batch is army-wide, so it can name a peer's regiment.
        observation["orders"] = {"request": "r9", "based_on": 1, "applied_ms": 5400,
                                 "results": [{"unit": "f9", "ok": True, "index": 1}]}
        # Another member sees e2 die: Lua drops its contact row and marks its roster row for
        # the whole alliance. Two more regiments appear, as Lua adds them on sight.
        del observation["enemy"][1]
        observation["enemy_roster"][1]["dead"] = True
        observation["enemy"] += [{"id": "e3", "type": "horse", "x": 900, "z": -900, "men": 45},
                                 {"id": "e4", "type": "horse", "x": 460, "z": -465, "men": 1,
                                  "state": ["routing"]}]
        observation["enemy_roster"] += [{"id": "e3", "type": "horse"},
                                        {"id": "e4", "type": "horse"}]
        # f9, the whole containing cavalry, 271 m from centre's anchor, routs out of view.
        # Own rows stay equal: an own row's morale.effect label is an open owner decision
        # (audit leak-morale-effect), so this test says nothing about it.
        observation["friendly"][8].update(x=-60, men=1, state=["routing"],
                                          morale={"fraction": .1, "effect": "Routing"})

    def in_view(observation):
        observation["enemy"][1].update(x=100, z=-175)

    base = centre_second_request(tmp_path / "base.jsonl")
    changed = centre_second_request(tmp_path / "changed.jsonl", distant, peer_replied=True)
    assert json.dumps(changed, sort_keys=True) == json.dumps(base, sort_keys=True)
    # A permitted cue does change the request, and by that contact's row alone.
    cue = centre_second_request(tmp_path / "cue.jsonl", in_view)
    seen = json.loads(cue["input"][0]["content"])
    assert [unit["id"] for unit in seen["observation"]["enemy"]] == ["e1", "e2"]
    seen["observation"]["enemy"].pop()
    assert seen == json.loads(base["input"][0]["content"])
