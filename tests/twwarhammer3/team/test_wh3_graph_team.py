"""Graph dispatch on current views, with independently completed real member calls."""

import json
import sys
from pathlib import Path
from threading import Event, Thread

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_wh3_graph import attack_graph, move_graph
from wh3_team_fixtures import Script, Workers, ack, state

from twwarhammer3.battle import controllers, graph, team


def test_target_hiding_after_worker_completion_is_locally_refused_with_original_age():
    member = graph.GraphPolicy(attack_graph())
    # Hand-computed member view: f2 owns the line. Prepare selector nodes first.
    member.decide(team.project(state(), {"f2"}))
    member.decide(team.project(state(2, 10100), {"f2"}))
    peer, pool = Script(), Workers()
    policy = team.TeamPolicy({"line": (team.SWORD, member), "cav": (team.KNIGHT, peer)},
                             executor=pool)
    policy.decide(state(3, 10200))
    pool.finish(0)
    pool.finish(1)
    hidden = state(4, 10300)
    hidden["enemy"] = []
    assert policy.decide(hidden)[0]["unit"] == "f1"  # peer still dispatched
    local = next(e for e in policy.drain_events() if e["event"] == "feedback")
    assert local["member"] == "line" and local["source"] == "local"
    assert "not visible" in local["ack"]["validation_error"]
    assert "applied_ms" not in local["ack"] and "delay_ms" not in local["latency"]
    assert member.source["time_ms"] == 10200  # never relabel old work as current
    assert member.run.status == "failed"
    ack(policy)
    policy.close()


@pytest.mark.parametrize("slow_name", ["line", "cav"])
def test_real_workers_dispatch_graph_while_peer_is_blocked_and_discard_at_close(slow_name):
    entered, release = Event(), Event()

    class Slow(Script):
        def decide(self, observation):
            entered.set()
            assert release.wait(3), "test failed to release slow peer"
            return super().decide(observation)

    spec = move_graph()
    fast_uid = "f1" if slow_name == "line" else "f2"
    spec["nodes"]["move"]["inputs"]["units"] = [fast_uid]
    # Cavalry starts at x=20; use a distinct waypoint.
    spec["nodes"]["move"]["inputs"]["point"] = {"x": 50, "z": 0}
    fast = graph.GraphPolicy(spec)
    slow = Slow()
    members = {"line": (team.SWORD, slow if slow_name == "line" else fast),
               "cav": (team.KNIGHT, slow if slow_name == "cav" else fast)}
    policy = team.TeamPolicy(members)
    try:
        assert policy.decide(state()) == []
        assert entered.wait(2)
        fast_member = policy.members["cav" if slow_name == "line" else "line"]
        fast_member.future.result(timeout=2)
        orders = policy.decide(state(2, 10100))
        assert len(orders) == 1 and orders[0]["unit"] == fast_uid
        assert not release.is_set() and not slow.feedback
        ack(policy, applied=10200)
        assert any(e["event"] == "member_event" for e in policy.drain_events())
        assert fast.run.status == "running"  # accepted, no arrival
    finally:
        release.set()
        policy.close()
    assert fast.closed and slow.closed
    assert any(e["event"] == "discarded" for e in policy.drain_events())


def test_configured_model_cannot_send_reply_retry_after_team_cleanup(tmp_path, monkeypatch):
    entered, release = Event(), Event()
    sends = []

    def send(key, body, **options):
        sends.append(body)
        entered.set()
        assert release.wait(3), "test failed to release model response"
        return {"id": "fake", "status": "completed",
                "usage": {"input_tokens": 10, "output_tokens": 10},
                "output": [{"type": "message", "content": [
                    {"type": "output_text", "text": "invalid"}]}]}

    monkeypatch.setattr(controllers, "post", send)
    monkeypatch.setattr(controllers, "api_key", lambda provider: "fake-only")
    path = tmp_path / "controller.json"
    path.write_text(json.dumps({"type": "team", "members": {
        "line": {"unit_types": None, "controller": {"type": "llm_rules"}},
        "cav": {"unit_types": [team.KNIGHT], "controller": {"type": "hold"}}}}))
    ledger = tmp_path / "synthetic-spend.jsonl"
    ledger.touch()
    policy = controllers.factories({"policy": "configured", "controller_config": str(path),
                                    "provider": "anthropic", "model": "claude-haiku-5-5",
                                    "effort": "low", "ledger": str(ledger),
                                    "budget_usd": 5})["configured"]()
    view = state()
    view.pop("terrain")
    closer = None
    try:
        policy.decide(view)
        assert entered.wait(2)
        closer = Thread(target=policy.close)
        closer.start()
        assert policy.stop.wait(2)
        release.set()
        closer.join(3)
        assert not closer.is_alive()
        assert len(sends) == 1
    finally:
        release.set()
        if closer is not None:
            closer.join(3)
        else:
            policy.close()
