import base64
import gzip
import json
import re
from copy import deepcopy

import pytest

from gameai.provenance import REPO_ROOT
from twwarhammer3.battle import replay, report, report_html

G1 = REPO_ROOT / "runs/twwarhammer3/battle/bench-g1-cavalry-ai10-01-20261014"


def frame(time, friendly=None, enemy=None, **extra):
    return {"time_ms": time, "seq": time, "friendly": friendly or [], "enemy": enemy or [],
            "enemy_roster": [], "source": {"file": "trace.jsonl", "line": time + 1}, **extra}


def unit(uid="f1", states=None, **extra):
    return {"id": uid, "type": "demo_knight", "state": states if states is not None else [],
            "men": 10, "men0": 10, "x": 0, "z": 0, **extra}


def test_missing_observation_or_state_never_becomes_death_rally_or_contact():
    frames = [frame(0, [unit(states=["routing"])], [unit("e1")]), frame(1000),
              frame(2000, [unit(states=["melee"])], [unit("e1", men=0)])]
    assert replay.state_events(frames, []) == []
    frames[1]["friendly"] = [{"id": "f1", "error": "no data"}]
    assert replay.state_events(frames, []) == []


def test_visible_transitions_objectives_timer_and_confirmed_roster_death():
    a = frame(0, [unit(commander=True)], [unit("e1", commander=True)], remaining_ms=65000,
              mode={"capture_points": [{"id": "p1", "holder": "enemy"}]})
    b = frame(1000, [unit(states=["melee", "routing"], commander=True,
                          morale={"effect": "Attacked in the rear"})],
              remaining_ms=59000, mode={"capture_points": [{"id": "p1", "holder": "friendly"}]})
    c = frame(2000, [unit()], enemy_roster=[{"id": "e1", "type": "general", "dead": True}])
    d = frame(3000, [unit(men=0, commander=True)])
    events = replay.state_events([a, b, c, d], ["demo_knight"])
    assert {e["kind"] for e in events} == {"contact", "rout", "rally", "death", "objective",
                                           "timer"}
    rout = next(e for e in events if e["kind"] == "rout")
    assert "general" in rout["caption"] and "protected" in rout["caption"]
    assert "Attacked in the rear" in rout["caption"]
    assert sum(e["kind"] == "death" for e in events) == 2
    assert "general" in next(e["caption"] for e in events if e["unit"] == "e1")
    assert all(e["source"] for e in events)


def test_order_lapsed_requires_a_live_visible_target_and_no_superseding_order():
    decision = {"time_ms": 0, "applied_ms": 1000, "orders": [
        {"order": {"unit": "f1", "type": "attack", "target": "e1"}, "ack": {"ok": True}}]}
    snapshot = frame(2000, [unit(states=["idle"])], [unit("e1")])
    assert replay.order_events([decision], [snapshot])[0]["kind"] == "lapsed"
    for bad in [frame(2000, [unit(states=["idle"])]),
                frame(6001, [unit(states=["idle"])], [unit("e1")]),
                frame(2000, [{"id": "f1", "men": 10}], [unit("e1")])]:
        assert replay.order_events([decision], [bad]) == []
    queued = deepcopy(decision)
    queued["orders"][0]["ack"]["queued"] = True
    assert replay.order_events([queued], [snapshot]) == []
    superseded = deepcopy(decision)
    superseded.update(time_ms=1500, applied_ms=1800)
    superseded["orders"][0]["order"]["type"] = "move"
    assert replay.order_events([decision, superseded], [snapshot]) == []


@pytest.mark.parametrize("rejection,text", [("unreachable", "destination unreachable"),
                                            ("unit_routing", "unit is fleeing")])
def test_replay_public_boundary_identity_and_exact_text(tmp_path, rejection, text):
    episode = tmp_path / "episode-0000"
    episode.mkdir()
    prompt = "</script> literal prompt & unicode ☃"
    a = frame(1000, [unit()], [unit("e1")], evaluation={
        "hidden": "SECRET", "version": 2, "enemy": {"units": {"destroyed": 15}}},
              setup={"private": "SECRET"}, final={"hidden": "SECRET"})
    b = frame(6000, [unit(x=3, z=4)], [], enemy_roster=[{"id": "e1", "type": "demo"}])
    records = [
        {"kind": "observation", "observation": a},
        {"kind": "decision", "seq": 1000, "time_ms": 1000, "request": "r1",
         "orders": [{"unit": "f1", "type": "move", "x": 4, "z": 5},
                    {"unit": "f1", "type": "move", "x": 6, "z": 7}],
         "behavior": {"prompt": prompt, "reason": "Quote me", "notes": "Notes", "attempts": [
             {"text": prompt, "seconds": 3, "provider_processing_ms": 2500, "usd": 0.1}]}},
        {"kind": "ack", "request": "r1", "latency": {"think_s": 3.1, "roundtrip_s": 3.5},
         "ack": {"applied_ms": 4500, "results": [
             {"index": 2, "unit": "f1", "ok": False, "error": rejection},
             {"index": 1, "unit": "f1", "ok": True, "queued": True}]}},
        {"kind": "observation", "observation": b},
        {"kind": "decision", "seq": 6000, "time_ms": 6000, "request": "r2",
         "orders": [{"unit": "f1", "type": "halt"}]},
    ]
    (episode / "trace.jsonl").write_text("\n".join(map(json.dumps, records)) + '\n{"kind":')
    data = replay.build(episode, {"config": {}, "scenario": {}})
    assert "SECRET" not in json.dumps(data)
    assert all("evaluation" not in f and "final" not in f for f in data["frames"])
    assert [f["time_ms"] for f in data["frames"]] == [1000, 6000]
    decision = data["decisions"][0]
    assert decision["prompt"] == prompt == decision["attempts"][0]["text"]
    assert decision["after_frame"] == 1 and decision["displacements"][0]["metres"] == 5
    assert [o["status"] for o in decision["orders"]] == ["queued", "rejected"]
    assert next(e["caption"] for e in data["events"] if e["kind"] == "rejected") == (
        f"Order rejected: Demo Knight: walk 10 m north-east ({text})")
    assert data["summary"]["unacknowledged_orders"] == 1
    assert len(data["warnings"]) == 1
    assert not any(e["kind"] == "death" for e in data["events"])
    assert decision["latency_parts"]["transport_residual_s"] == 0.5
    assert decision["latency_parts"]["harness_roundtrip_residual_s"] == pytest.approx(0.4)


def test_recorder_gaps_terminal_frames_and_visibility_keep_stable_ids(tmp_path):
    episode = tmp_path / "episode-0000"
    episode.mkdir()
    base = {"job": "j", "battle": "b", "recorder": 1, "time_ms": 0,
            "friendly": [{"id": "f1", "x": 1, "z": 2}], "enemy": [{"id": "e1", "x": 3, "z": 4}],
            "enemy_roster": [{"id": "e1"}]}
    records = [base, {**base, "time_ms": 1000, "enemy": []}, {**base, "time_ms": 4000},
               {**base, "time_ms": 4300, "terminal": True, "result": "won"},
               {**base, "time_ms": 5000, "battle": "wrong"}]
    (episode / "trace.jsonl").write_text(
        json.dumps({"kind": "battle", "observation": {**base, "seq": 0}}))
    (episode / "replay.jsonl").write_text("\n".join(map(json.dumps, records)) + "\n{")
    payload = replay.build(episode, {"config": {}, "scenario": {}})
    frames = [f for f in payload["frames"] if f["source"]["file"] == "replay.jsonl"]
    assert [f["time_ms"] for f in frames] == [0, 1000, 4000, 4300]
    assert frames[1]["enemy"] == []
    assert frames[0]["enemy"][0]["id"] == frames[2]["enemy"][0]["id"] == "e1"
    assert frames[-1]["result"] == "won"
    assert len(payload["warnings"]) == 2
    assert not any(e["kind"] == "death" for e in payload["events"])


def test_sample_interval_is_the_recorders_or_the_observed_spacing_without_it(tmp_path):
    # A trace-only run claimed config observe_ms (1000) while its frames were ~5 s apart.
    trace = tmp_path / "trace-only" / "episode-0000"
    trace.mkdir(parents=True)
    observations = [{"kind": "observation", "observation": frame(t, [unit()])}
                    for t in (0, 5000, 10100, 14900, 20000)]
    (trace / "trace.jsonl").write_text("\n".join(map(json.dumps, observations)))
    manifest = {"config": {"observe_ms": 1000}, "scenario": {}}
    assert replay.build(trace, manifest)["sample_interval_ms"] == 5000
    recorder = tmp_path / "recorder" / "episode-0000"
    recorder.mkdir(parents=True)
    base = {"job": "j", "battle": "b", "recorder": 1, "friendly": [{"id": "f1", "x": 1, "z": 2}],
            "enemy": [], "enemy_roster": []}
    (recorder / "trace.jsonl").write_text(
        json.dumps({"kind": "battle", "observation": {**base, "time_ms": 0, "seq": 0}}))
    (recorder / "replay.jsonl").write_text(
        "\n".join(json.dumps({**base, "time_ms": t}) for t in (0, 500, 1000)))
    manifest = {**manifest, "recorder": {"enabled": True, "interval_ms": 500}}
    assert replay.build(recorder, manifest)["sample_interval_ms"] == 500


@pytest.mark.skipif(not G1.exists(), reason="local original-engine evidence absent")
def test_g1_matches_trace_and_never_invents_general_death():
    payloads = [replay.build(p) for p in sorted(G1.glob("episode-*"))]
    sol = payloads[2]
    assert sol["summary"] == {"decisions": 96, "orders": 441, "acknowledged_orders": 436,
                              "unacknowledged_orders": 5, "rejections": 29, "orders_batches": 87,
                              "empty_decisions": 9, "notes_changes": 29}
    assert sum(o.get("ack", {}).get("error") == "unreachable"
               for d in sol["decisions"] for o in d["orders"]) == 23
    assert any(e["kind"] == "rout" and e["unit"] == "e1" for e in sol["events"])
    assert not any(e["kind"] == "death" and e["unit"] == "e1" for e in sol["events"])
    assert [len(p["frames"]) for p in payloads] == [423, 302, 98]
    assert all(len(gzip.compress(json.dumps(p).encode())) < 500_000 for p in payloads)
    collected = report.collect([G1])
    trial = collected["groups"][0]["trials"][2]
    assert trial["llm"]["usd"] == pytest.approx(0.793363)
    # The verdict's information age is the collector's: non-empty batches only.
    assert trial["metrics"]["order_age_s"]["p50"] == 5.25
    html = report_html.render(collected)
    # Nine trials of this scale, including base64 expansion, fit well below 20 MiB.
    assert len(html.encode()) * 3 < 20 * 1024 * 1024
    embedded = json.loads(
        re.search(r'id="report-data" type="application/json">(.*?)</script>', html, re.S)[1])
    # The page embeds the fields it draws, rounded (report_html.compact), and its route outline.
    assert json.loads(gzip.decompress(base64.b64decode(embedded["replays"]["g0-t2"]))) == {
        **report_html.compact(sol), "highlights": []}
    # 87 batches of orders, one never acknowledged: its age is unknown, not zero.
    timing = embedded["battles"]["g0-t2"]["timing"]
    assert len(timing["ages"]) == 86 and timing["moved"] == []
    assert len(embedded["prompts"]) == 1


KNIGHTS = {"name": "Knights of the Realm", "short": "KR", "role": "Lance cavalry",
           "about": "Charge cavalry.", "glyph": "cavalry"}
NOTES = {"units": {"wh_main_brt_cav_knights_of_the_realm": KNIGHTS,
                   "wh_main_brt_cha_lord_4": {"name": "Lord", "short": "Lord",
                                              "role": "Mounted lord", "glyph": "general"}}}


def test_roster_names_numbers_describes_and_reads_base_stats(tmp_path):
    episode = tmp_path / "episode-0000"
    episode.mkdir()
    knights = {"type": "wh_main_brt_cav_knights_of_the_realm", "class": "cavalry"}
    friendly = [{"id": "f10", "type": "wh_main_brt_cav_grail_knights", "class": "cavalry"},
                {"id": "f2", **knights}, {"id": "f1", **knights},
                {"id": "f3", "type": "wh_main_brt_cha_lord_4", "class": "lord"},
                {"id": "f4", "type": "wh3_main_kho_inf_chaos_warriors_0", "class": "infantry"}]
    (episode / "trace.jsonl").write_text(json.dumps({"kind": "observation", "observation": {
        "seq": 0, "time_ms": 0, "friendly": friendly, "enemy": [
            {"id": "e1", **knights}, {"id": "e3", "type": "wh_main_emp_inf_handgunners"},
            *({"id": uid, "type": "wh_main_emp_inf_halberdiers"} for uid in ("e2", "e4"))]}}))
    (episode / "unit_names.json").write_text(json.dumps({"f3": "Recorded lord",
                                                         "f10": "Grail Knights"}))
    (episode / "result.json").write_text(json.dumps({"setup": {"unit_base_stats": (
        "wh_main_brt_bretonnia@wh_main_brt_cav_knights_of_the_realm:stat_armour=100.00/"
        "scalar_speed=84.00/stat_melee_attack=32.50/stat_unrecorded=1.00;"
        "wh_main_brt_cha_lord_4:stat_armour=110.00@@wh_main_emp_empire@"
        "wh_main_emp_inf_handgunners:stat_ammo=22.00/scalar_missile_range=145.00")}}))
    roster = replay.build(episode, {"config": {}, "scenario": {}}, NOTES)["roster"]
    assert [(u["id"], u["display"], u["short"], u["role"], u["glyph"]) for u in roster] == [
        ("f1", "Knights of the Realm 1", "KR1", "Lance cavalry", "cavalry"),
        ("f2", "Knights of the Realm 2", "KR2", "Lance cavalry", "cavalry"),
        ("f3", "Lord", "Lord", "Mounted lord", "general"),  # notes win over unit_names.json
        ("f4", "Chaos Warriors", "CW", "Infantry", "infantry"),  # type key, asset number gone
        ("f10", "Grail Knights", "GK", "Cavalry", "cavalry"),
        ("e1", "Knights of the Realm", "KR", "Lance cavalry", "cavalry"),
        # bench-g1 without notes labelled both "H1": shared initials take three letters
        ("e2", "Halberdiers 1", "Hal1", "Unit", "unknown"),
        ("e3", "Handgunners", "Han", "Unit", "unknown"),
        ("e4", "Halberdiers 2", "Hal2", "Unit", "unknown")]
    assert roster[0]["about"] == "Charge cavalry." and roster[3]["about"] is None
    assert roster[0]["stats"] == {"armour": 100, "speed": 84, "melee_attack": 32.5}
    assert roster[0]["stats_source"] == "result.json setup.unit_base_stats"
    assert roster[3]["stats"] is None
    assert replay.base_stats("x@a:stat_ammo=22.00/scalar_missile_range=145.00") == {
        "a": {"ammo": 22, "range_m": 145}}


def item(order, ok=True, error=None, queued=False):
    if ok is None:
        return {"order": order, "status": "issued; acknowledgement missing"}
    return {"order": order, "ack": {"ok": ok, "error": error, "queued": queued},
            "status": "rejected" if not ok else "queued" if queued else "acknowledged"}


LABELS = {"f1": "Knights 1", "f2": "Lord", "f3": "Archers", "f4": "Guard", "f5": "Knights 2",
          "e1": "Cannon", "e2": "Gunners"}


def test_orders_read_as_one_line_per_unit_with_distances_and_compass_points():
    basis = frame(0, [unit("f1"), unit("f3", x=10, z=10)])
    decision = {"orders": [
        item({"unit": "f1", "type": "move", "x": 0, "z": 100, "run": True}),
        item({"unit": "f2", "type": "ability",
              "ability": "wh_main_character_abilities_foe_seeker"}),
        item({"unit": "f1", "type": "move", "x": 100, "z": 100, "run": True, "queue": True},
             queued=True),
        item({"unit": "f1", "type": "attack", "target": "e1", "mode": "melee", "queue": True},
             queued=True),
        item({"unit": "f3", "type": "move", "x": -90, "z": -90}, ok=False, error="unreachable"),
        item({"unit": "f3", "type": "attack", "target": "e1", "mode": "ranged", "queue": True},
             ok=False, error="queue_predecessor_failed_or_missing"),
        item({"unit": "f4", "type": "behaviour", "behaviour": "fire_at_will", "enabled": False},
             ok=None),
        item({"unit": "army", "type": "ability", "ability": "wh3_main_army_abilities_blood_rite"}),
    ]}
    steps = replay.order_steps(decision, basis, LABELS)
    assert [(s["kind"], s["queued"], s["status"]) for s in steps[:4]] == [
        ("move", False, "acknowledged"), ("ability", False, "acknowledged"),
        ("move", True, "queued"), ("attack", True, "queued")]
    assert steps[4]["error_text"] == "destination unreachable" and steps[4]["x"] == -90
    assert replay.summary_lines(steps, LABELS) == [
        {"unit": "f1", "status": "ok", "text": "Knights 1: run 100 m north, then run 100 m east, "
                                               "then attack Cannon in melee"},
        {"unit": "f2", "status": "ok", "text": "Lord: use Foe Seeker"},
        {"unit": "f3", "status": "rejected",
         "text": "Archers: walk 140 m south-west (rejected: destination unreachable), then shoot "
                 "at Cannon (rejected: the step before it failed or was missing)"},
        {"unit": "f4", "status": "unacknowledged", "text": "Guard: turn fire at will off"},
        {"unit": None, "status": "ok", "text": "Army: use Blood Rite"}]
    assert replay.summary_lines([], LABELS) == []


def test_next_facts_report_recorded_outcomes_within_each_units_window():
    def knight(uid, x=0, z=0, target=None, states=("moving",)):
        return unit(uid, x=x, z=z, target=target, states=list(states))

    first = {"applied_ms": 1000, "orders": [
        item({"unit": "f1", "type": "attack", "target": "e1", "mode": "melee"}),
        item({"unit": "f2", "type": "move", "x": 0, "z": 50}),
        item({"unit": "f3", "type": "attack", "target": "e2", "mode": "melee"}),
        item({"unit": "f4", "type": "move", "x": 900, "z": 0}, ok=False, error="unreachable"),
        item({"unit": "f5", "type": "attack", "target": "e2", "mode": "melee"})]}
    second = {"applied_ms": 5000, "orders": [item({"unit": "f3", "type": "halt"})]}
    frames = [frame(500, [knight("f1"), knight("f2"), knight("f3"), knight("f5")],
                    [unit("e1"), unit("e2")]),
              frame(1000, [knight("f1", target="e1"), knight("f2")], [unit("e1")]),
              frame(2000, [knight("f1", target="e1", states=["melee"]), knight("f2", z=30)],
                    [unit("e1", states=["melee"])]),
              frame(3000, [knight("f2", z=48)], [unit("e1", states=["routing"])]),
              frame(40000)]
    for decision in (first, second):
        decision["steps"] = replay.order_steps(decision, frames[0], LABELS)
    facts = replay.next_facts(0, [first, second], frames, LABELS, replay.state_events(frames, []))
    assert [fact["text"] for fact in facts] == [
        "Guard: rejected by the game (destination unreachable)",
        "Lord moved about 50 m in 2 s; closest to the final waypoint: 2 m at 0:03",
        "No melee between Archers and Gunners recorded before its next order at 0:05",
        "No melee between Knights 2 and Gunners recorded before 30 s later",
        "Knights 1 in melee with Cannon from 0:02",
        "Cannon began fleeing at 0:03"]
    assert facts[-1]["unit"] == "e1" and facts[-1]["time_ms"] == 3000


def test_melee_with_a_target_needs_it_close_by():
    """visual-sol 3:24: Knights of the Realm 2 targeted Handgunners 1 while in melee with the
    general 16 m away, 89 m from the handgunners; that is no melee with the handgunners."""
    first = {"applied_ms": 1000, "orders": [
        item({"unit": "f1", "type": "attack", "target": "e1", "mode": "melee"})]}
    fighting = {"target": "e1", "states": ["melee"]}
    frames = [frame(0, [unit("f1")], [unit("e1", x=89), unit("e2", x=16)]),
              frame(2000, [unit("f1", **fighting)], [unit("e1", x=89), unit("e2", x=16)]),
              frame(3000, [unit("f1", x=50, **fighting)], [unit("e1", x=89), unit("e2", x=16)])]
    first["steps"] = replay.order_steps(first, frames[0], LABELS)
    facts = replay.next_facts(0, [first], frames, LABELS, replay.state_events(frames, []))
    assert [fact["text"] for fact in facts] == ["Knights 1 in melee with Cannon from 0:03"]


def test_next_facts_need_frames_after_the_orders_and_observed_target_transitions():
    """Regressions from real traces: the frame taken at applied_ms shows the battle before
    the orders (bench-g1 episode 0, 0:05); a target is watched while any of the batch's units
    attacks it (visual-sol 6:05, the general's rout at 6:21); an onset across an unobserved
    gap is not a time; no frame after the orders means no facts."""
    def attack(uid, target):
        return item({"unit": uid, "type": "attack", "target": target, "mode": "melee"})

    first = {"applied_ms": 1000, "orders": [attack("f1", "e1"), attack("f2", "e1"),
                                            attack("f3", "e2")]}
    second = {"applied_ms": 3500, "orders": [item({"unit": "f1", "type": "halt"})]}
    last = {"applied_ms": 4000, "orders": [attack("f4", "e1")]}
    fighting = {"target": "e1", "states": ["melee"]}
    frames = [frame(0, [unit("f1"), unit("f2"), unit("f3")], [unit("e1"), unit("e2")]),
              frame(1000, [unit("f1", **fighting), unit("f2"), unit("f3")],
                    [unit("e1"), unit("e2")]),
              frame(3000, [unit("f1"), unit("f2", **fighting), unit("f3")], [unit("e1")]),
              frame(4000, [unit("f1"), unit("f2", **fighting), unit("f3")],
                    [unit("e1", states=["routing"]), unit("e2", states=["routing"])])]
    decisions = [first, second, last]
    for decision in decisions:
        decision["steps"] = replay.order_steps(decision, frames[0], LABELS)
    transitions = replay.state_events(frames, [])
    facts = replay.next_facts(0, decisions, frames, LABELS, transitions)
    assert [(fact["time_ms"], fact["text"]) for fact in facts] == [
        (1000, "Knights 1 already in melee with Cannon at 0:01"),
        (1000, "No melee between Archers and Gunners recorded before the battle ended"),
        (3000, "Lord in melee with Cannon from 0:03"),
        (4000, "Cannon began fleeing at 0:04")]  # Gunners: unseen at 0:03, no onset time
    assert replay.next_facts(2, decisions, frames, LABELS, transitions) == []


def test_key_events_are_first_contact_first_rout_per_side_leaders_and_the_end():
    roster = [{"id": "f1", "side": "friendly"}, {"id": "f2", "side": "friendly", "protected": True},
              {"id": "f3", "side": "friendly"}, {"id": "e1", "side": "enemy", "commander": True},
              {"id": "e2", "side": "enemy"}, {"id": "e3", "side": "enemy"}]
    events = [{"kind": kind, "unit": uid} for kind, uid in (
        ("contact", "f1"), ("rout", "e2"), ("rout", "e3"), ("rout", "e1"), ("rally", "e1"),
        ("rout", "f2"), ("death", "f3"), ("death", "f2"), ("timer", None), ("end", None))]
    replay.mark_key_events(events, roster)
    assert [event["key"] for event in events] == [True, True, False, True, False, True, False,
                                                  True, False, True]


def test_longest_model_reply_needs_a_model_call_and_shows_once_the_reply_took_effect():
    scripted = {"time_ms": 0, "applied_ms": 300, "orders": [], "attempts": [],
                "latency": {"think_s": 0.004}, "source": {"line": 1}, "ack_source": {"line": 2}}
    assert replay.order_events([scripted], []) == []  # bench-g1 attack_nearest: no model
    model = {**scripted, "time_ms": 1000, "applied_ms": 5300, "attempts": [{"seconds": 4.1}],
             "latency": {"think_s": 4.2}, "ack_source": {"line": 9}}
    assert replay.order_events([scripted, model], []) == [{
        "kind": "longest_think", "time_ms": 5300, "decision": 1, "source": {"line": 9},
        "caption": "Longest model reply: 4.2 s"}]
