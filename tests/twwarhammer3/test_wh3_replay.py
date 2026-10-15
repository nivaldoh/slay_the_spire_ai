import base64
import gzip
import json
from copy import deepcopy
from pathlib import Path

import pytest

from twwarhammer3.battle import replay, report, report_html

G1 = Path("runs/twwarhammer3/battle/bench-g1-cavalry-ai10-01-20261014")


def frame(time, friendly=None, enemy=None, **extra):
    return {
        "time_ms": time,
        "seq": time,
        "friendly": friendly or [],
        "enemy": enemy or [],
        "enemy_roster": [],
        "source": {"file": "trace.jsonl", "line": time + 1},
        **extra,
    }


def unit(uid="f1", states=None, **extra):
    return {
        "id": uid,
        "type": "demo_knight",
        "state": states if states is not None else [],
        "men": 10,
        "men0": 10,
        "x": 0,
        "z": 0,
        **extra,
    }


def test_missing_observation_or_state_never_becomes_death_rally_or_contact():
    frames = [
        frame(0, [unit(states=["routing"])], [unit("e1")]),
        frame(1000),
        frame(2000, [unit(states=["melee"])], [unit("e1", men=0)]),
    ]
    assert replay.state_events(frames, []) == []
    frames[1]["friendly"] = [{"id": "f1", "error": "no data"}]
    assert replay.state_events(frames, []) == []


def test_visible_transitions_objectives_timer_and_confirmed_roster_death():
    a = frame(
        0,
        [unit(commander=True)],
        [unit("e1")],
        remaining_ms=65000,
        mode={"capture_points": [{"id": "p1", "holder": "enemy"}]},
    )
    b = frame(
        1000,
        [
            unit(
                states=["melee", "routing"],
                commander=True,
                morale={"effect": "Attacked in the rear"},
            )
        ],
        remaining_ms=59000,
        mode={"capture_points": [{"id": "p1", "holder": "friendly"}]},
    )
    c = frame(2000, [unit()], enemy_roster=[{"id": "e1", "type": "general", "dead": True}])
    d = frame(3000, [unit(men=0, commander=True)])
    events = replay.state_events([a, b, c, d], ["demo_knight"])
    assert {e["kind"] for e in events} == {
        "contact",
        "rout",
        "rally",
        "death",
        "objective",
        "timer",
    }
    rout = next(e for e in events if e["kind"] == "rout")
    assert "general" in rout["caption"] and "protected" in rout["caption"]
    assert "Attacked in the rear" in rout["caption"]
    assert sum(e["kind"] == "death" for e in events) == 2
    assert all(e["source"] for e in events)


def test_order_lapsed_requires_a_live_visible_target_and_no_superseding_order():
    decision = {
        "time_ms": 0,
        "applied_ms": 1000,
        "orders": [
            {"order": {"unit": "f1", "type": "attack", "target": "e1"}, "ack": {"ok": True}}
        ],
    }
    snapshot = frame(2000, [unit(states=["idle"])], [unit("e1")])
    assert replay.order_events([decision], [snapshot])[0]["kind"] == "lapsed"
    for bad in [
        frame(2000, [unit(states=["idle"])]),
        frame(6001, [unit(states=["idle"])], [unit("e1")]),
        frame(2000, [{"id": "f1", "men": 10}], [unit("e1")]),
    ]:
        assert replay.order_events([decision], [bad]) == []
    queued = deepcopy(decision)
    queued["orders"][0]["ack"]["queued"] = True
    assert replay.order_events([queued], [snapshot]) == []
    superseded = deepcopy(decision)
    superseded.update(time_ms=1500, applied_ms=1800)
    superseded["orders"][0]["order"]["type"] = "move"
    assert replay.order_events([decision, superseded], [snapshot]) == []


def test_replay_public_boundary_identity_and_exact_text(tmp_path):
    episode = tmp_path / "episode-0000"
    episode.mkdir()
    prompt = "</script> literal prompt & unicode ☃"
    a = frame(
        1000,
        [unit()],
        [unit("e1")],
        evaluation={"hidden": "SECRET"},
        setup={"private": "SECRET"},
        final={"hidden": "SECRET"},
    )
    b = frame(6000, [unit(x=3, z=4)], [], enemy_roster=[{"id": "e1", "type": "demo"}])
    records = [
        {"kind": "observation", "observation": a},
        {
            "kind": "decision",
            "seq": 1000,
            "time_ms": 1000,
            "request": "r1",
            "orders": [
                {"unit": "f1", "type": "move", "x": 4, "z": 5},
                {"unit": "f1", "type": "move", "x": 6, "z": 7},
            ],
            "behavior": {
                "prompt": prompt,
                "reason": "Quote me",
                "notes": "Notes",
                "attempts": [
                    {"text": prompt, "seconds": 3, "provider_processing_ms": 2500, "usd": 0.1}
                ],
            },
        },
        {
            "kind": "ack",
            "request": "r1",
            "latency": {"think_s": 3.1, "roundtrip_s": 3.5},
            "ack": {
                "applied_ms": 4500,
                "results": [
                    {"index": 2, "unit": "f1", "ok": False, "error": "unreachable"},
                    {"index": 1, "unit": "f1", "ok": True, "queued": True},
                ],
            },
        },
        {"kind": "observation", "observation": b},
        {
            "kind": "decision",
            "seq": 6000,
            "time_ms": 6000,
            "request": "r2",
            "orders": [{"unit": "f1", "type": "halt"}],
        },
    ]
    (episode / "trace.jsonl").write_text("\n".join(map(json.dumps, records)) + '\n{"kind":')
    data = replay.build(episode, {"config": {}, "scenario": {}})
    assert "SECRET" not in json.dumps(data)
    assert [f["time_ms"] for f in data["frames"]] == [1000, 6000]
    decision = data["decisions"][0]
    assert decision["prompt"] == prompt == decision["attempts"][0]["text"]
    assert decision["after_frame"] == 1 and decision["displacements"][0]["metres"] == 5
    assert [o["status"] for o in decision["orders"]] == ["queued", "rejected"]
    assert data["summary"]["unacknowledged_orders"] == 1
    assert len(data["warnings"]) == 1
    assert not any(e["kind"] == "death" for e in data["events"])
    assert decision["latency_parts"]["transport_residual_s"] == 0.5
    assert decision["latency_parts"]["harness_roundtrip_residual_s"] == pytest.approx(0.4)


@pytest.mark.skipif(not G1.exists(), reason="local original-engine evidence absent")
def test_g1_matches_trace_and_never_invents_general_death():
    payloads = [replay.build(p) for p in sorted(G1.glob("episode-*"))]
    sol = payloads[2]
    assert sol["summary"]["decisions"] == 96
    assert sol["summary"]["orders"] == 441
    assert sol["summary"]["acknowledged_orders"] == 436
    assert sol["summary"]["unacknowledged_orders"] == 5
    assert sol["summary"]["rejections"] == 29
    assert sol["summary"]["notes_changes"] == 29
    assert sol["summary"]["empty_decisions"] == 9
    assert sol["summary"]["llm"]["usd"] == pytest.approx(0.793363)
    assert sol["summary"]["age_s"]["p50"] == 5.1
    assert sol["summary"]["age_s"]["p90"] == 7.2
    assert (
        sum(
            o.get("ack", {}).get("error") == "unreachable"
            for d in sol["decisions"]
            for o in d["orders"]
        )
        == 23
    )
    assert any(e["kind"] == "rout" and e["unit"] == "e1" for e in sol["events"])
    assert not any(e["kind"] == "death" and e["unit"] == "e1" for e in sol["events"])
    assert [len(p["frames"]) for p in payloads] == [423, 302, 98]
    assert all(len(gzip.compress(json.dumps(p).encode())) < 500_000 for p in payloads)
    html = report_html.render(report.collect([G1]))
    # Nine trials of this scale, including base64 expansion, fit well below 20 MiB.
    assert len(html.encode()) * 3 < 20 * 1024 * 1024
    import re

    embedded = json.loads(
        re.search(r'id="report-data" type="application/json">(.*?)</script>', html, re.S)[1]
    )
    decoded = json.loads(gzip.decompress(base64.b64decode(embedded["replays"]["g0-t2"])))
    assert decoded == sol
    assert len(embedded["prompts"]) == 1
