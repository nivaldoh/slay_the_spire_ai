"""Independent synthetic cases from the supplied plan; no game-strength claims."""

import copy
import json

import pytest

from twwarhammer3.battle import setup
from twwarhammer3.battle import support_evidence as evidence
from twwarhammer3.battle import support_timing as timing
from twwarhammer3.protocol import ProtocolError, validate_orders


def view(ms=1000, *, melee=False, cavalry=False, routed=False, seq=None):
    # Deliberately reverse recruitment order and use unrelated IDs.
    infantry = {"id": "f9", "type": "wh_main_emp_inf_swordsmen", "men": 90, "hp": .8,
                "x": 0, "z": 0, "state": (["melee"] if melee else []) +
                (["routing"] if routed else []), "morale": {"fraction": .7}}
    horse = {"id": "f2", "type": "wh_main_emp_cav_empire_knights", "men": 45, "hp": .9,
             "x": -100, "z": 60, "state": ["melee"] if cavalry else []}
    enemy = {"id": "e8", "type": "wh_main_emp_inf_greatswords", "men": 90, "hp": 1,
             "x": 0, "z": -160, "bearing": 0, "state": ["melee"] if melee else []}
    return {"phase": "Deployed", "battle": "b1", "job": "j", "seq": seq or ms,
            "time_ms": ms, "speed": 1, "friendly": [horse, infantry], "enemy": [enemy],
            "enemy_roster": [{"id": "e8", "type": "wh_main_emp_inf_greatswords"}]}


def acknowledge(policy, orders):
    policy.acknowledge({"results": [{"index": i + 1, "unit": order["unit"], "ok": True}
                                     for i, order in enumerate(orders)]}, {})


def test_roster_settings_and_development_scope_match_owner_plan():
    s = setup.scenarios()["emp-support-timing-v1"]
    assert s["player"]["units"] == ["wh_main_emp_inf_swordsmen", "wh_main_emp_cav_empire_knights"]
    assert s["enemy"]["units"] == ["wh_main_emp_inf_greatswords"]
    assert s["player"]["lord"] is s["enemy"]["lord"] is False
    assert s["player"]["experience"] == {"0": 0, "1": 0}
    assert s["enemy"]["experience"] == {"0": 0}
    assert s["expect"] == {"battle_type": "land_normal", "difficulty": "ai_level_normal",
                           "funds": "funds_custom", "funds_amount": 2000, "time_limit_s": 1200,
                           "ai_stats_modifier": 1.0, "unit_scale": .75, "realism": False,
                           "player_defends": True}
    assert s["split"] == "development" and s["status"] == "candidate_unverified"
    assert "benchmark" not in s and "scoring" not in s and s["behaviour_defaults"] is True
    assert [(u["x"], u["z"], u["bearing"], u["width"])
            for u in s["deployment"]["friendly"]] == [(0, 0, 180, 40), (-100, 60, 180, 30)]
    assert [(u["x"], u["z"], u["bearing"], u["width"])
            for u in s["deployment"]["enemy"]] == [(0, -160, 0, 40)]
    setup.validate_declaration(s, {"episode_timeout": 1320, "run_timeout": 2280,
                                   "start_timeout": 900, "episodes": 1})


@pytest.mark.parametrize("kind,count", [(timing.Direct, 2), (timing.Opening, 4),
                                        (timing.Scheduled, 1), (timing.Contact, 1),
                                        (timing.Delayed, 1), (timing.NoneIntervention, 1)])
def test_all_arms_use_same_infantry_and_public_legal_orders(kind, count):
    policy = kind()
    obs = view()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert len(orders) == count
    assert orders[0] == {"type": "attack", "unit": "f9", "target": "e8", "mode": "melee",
                         "run": True, "queue": False}
    acknowledge(policy, orders)
    assert policy.decide(view(2000)) == []


def test_delayed_freezes_public_cue_route_and_waits_full_battle_delay():
    policy = timing.Delayed()
    orders = policy.decide(view(10000, melee=True))
    acknowledge(policy, orders)
    early = view(21999, melee=True)
    early["enemy"][0].update(x=700, z=700, bearing=180)
    assert policy.decide(early) == []
    late = copy.deepcopy(early)
    late.update(time_ms=22000, seq=22000)
    orders = policy.decide(late)
    validate_orders(orders, late)
    assert [(o["x"], o["z"]) for o in orders[:2]] == [(-80, -160), (-80, -220)]
    assert [o["queue"] for o in orders] == [False, True, True]
    assert orders[-1]["target"] == "e8"
    assert policy.metadata()["cue"]["time_ms"] == 10000
    assert policy.metadata()["submitted"]["time_ms"] == 22000


def test_relative_geometry_rotates_with_enemy_bearing():
    obs = view()
    obs["enemy"][0].update(x=10, z=20, bearing=90)
    orders = timing.Opening().decide(obs)[1:]
    assert orders[0]["x"] == pytest.approx(10)
    assert orders[0]["z"] == pytest.approx(100)
    assert orders[1]["x"] == pytest.approx(-50)
    assert orders[1]["z"] == pytest.approx(100)


def test_contact_requires_both_regiments_and_schedule_uses_battle_time():
    contact, scheduled = timing.Contact(), timing.Scheduled()
    obs = view(29999)
    obs["friendly"][1]["state"] = ["melee"]
    for policy in (contact, scheduled):
        orders = policy.decide(obs)
        assert len(orders) == 1
        acknowledge(policy, orders)
    assert contact.decide(view(30000)) == []
    assert len(scheduled.decide(view(30000))) == 3
    assert len(contact.decide(view(31000, melee=True))) == 3


def test_hidden_data_cannot_supply_a_cue_or_invisible_attack():
    policy = timing.Contact()
    obs = view(10000, melee=True)
    obs["enemy"] = []
    obs["evaluation"] = {"enemy": {"state": ["melee"]}}
    assert policy.decide(obs) == []
    assert policy.metadata()["cue"] is None


def test_no_intervention_keeps_engine_automation_and_never_orders_cavalry():
    policy = timing.NoneIntervention()
    for ms in (1000, 30000, 100000):
        orders = policy.decide(view(ms, melee=True))
        assert all(o["unit"] == "f9" for o in orders)
        assert not any(o["type"] == "behaviour" for o in orders)
        acknowledge(policy, orders)
    assert policy.metadata()["cue"] is None


def test_changed_identity_and_failed_ack_stop_without_retry():
    policy = timing.Direct()
    orders = policy.decide(view())
    with pytest.raises(ProtocolError, match="acknowledgement"):
        policy.acknowledge({"results": []}, {})
    acknowledge(policy, orders)
    changed = view(2000)
    changed["friendly"][0]["id"] = "f99"
    with pytest.raises(ProtocolError, match="identities changed"):
        policy.decide(changed)


def episode(tmp_path, observations, extra=()):
    directory = tmp_path / "episode-0000"
    directory.mkdir()
    rows = [{"kind": "observation", "observation": o} for o in observations] + list(extra)
    (directory / "trace.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    (directory / "result.json").write_text(json.dumps({"status": "won"}))
    return directory


def ending(ms=5000):
    obs = view(ms, melee=True, cavalry=True)
    obs["result"] = "won"
    obs["final"] = {"benchmark": {"time_ms": ms, "units": [
        {"id": "f9", "type": "wh_main_emp_inf_swordsmen", "hp": .4, "men": 40,
         "routing": False, "shattered": False, "departed": False},
        {"id": "f2", "type": "wh_main_emp_cav_empire_knights", "hp": .8, "men": 35,
         "routing": False, "shattered": False, "departed": False}]}}
    return obs


def test_ack_without_execution_is_unknown_and_hp_comes_from_first_engine_ending(tmp_path):
    end = ending()
    end["friendly"][0]["state"] = []
    rows = [view(), view(2000, melee=True), end]
    report = evidence.annotate(episode(tmp_path, rows, [
        {"kind": "ack", "ack": {"results": [{"unit": "f2", "ok": True}]}}]))
    assert report["engine_result"] == "won" and report["H"] == pytest.approx(.6)
    assert report["cavalry_melee"]["label"] == "unclear"
    assert report["contact_before_support_loss"] is None


@pytest.mark.parametrize("same_frame,expected", [(False, False), (True, None)])
def test_late_contact_and_same_interval_are_not_useful_support(tmp_path, same_frame, expected):
    before = view(1000, melee=True)
    rout = view(2000, melee=True, routed=True, cavalry=same_frame)
    contact = view(3000, melee=True, routed=True, cavalry=True)
    report = evidence.annotate(episode(tmp_path, [before, rout, contact]))
    assert report["contact_before_support_loss"] is expected
    assert report["engine_result"] is None  # status is not an engine ending


def test_missing_frames_widen_brackets_and_missing_terminal_unit_does_not_become_dead(tmp_path):
    end = ending(20000)
    end["final"]["benchmark"]["units"].pop()
    hidden = view(10000)
    hidden["enemy"] = []
    report = evidence.annotate(episode(tmp_path, [view(1000), hidden, end]))
    assert report["cue"]["interval_ms"] == [1000, 20000]
    assert report["H"] is None and report["sampling_intervals_ms"] == [9000, 10000]


def test_swapped_unit_ids_do_not_silently_exchange_infantry_and_cavalry(tmp_path):
    end = ending()
    end["friendly"][0]["id"], end["friendly"][1]["id"] = "f9", "f2"
    report = evidence.annotate(episode(tmp_path, [view(), end]))
    assert report["H"] is None and "identity changed" in report["issues"][0]


def test_plan_retains_every_fresh_attempt_rotates_blocks_and_never_replaces(tmp_path, monkeypatch):
    monkeypatch.setattr(timing, "committed_revision", lambda *a: "frozen-revision")
    monkeypatch.setattr(timing, "source_fingerprints", lambda *a: {"source": "hash"})
    path = tmp_path / "plan.json"
    plan = timing.make_plan(path)
    jobs = plan["jobs"]
    assert len(jobs) == len({j["output"] for j in jobs}) == 18
    assert [j["arm"] for j in jobs[:6]] == [
        "direct", "opening", "scheduled", "contact", "delayed", "none"]
    assert [j["arm"] for j in jobs[6:12]] == [
        "opening", "scheduled", "contact", "delayed", "none", "direct"]
    assert all(j["args"][j["args"].index("--episodes") + 1] == "1" for j in jobs)
    assert plan["keep_going"] is False
    report = evidence.summarize(path)
    assert len(report["attempts"]) == 18
    assert all(a["status"] == "missing" for a in report["attempts"])
    assert report["readiness"] == "unverified" and report["proposed_numerical_contrast"] is False
    with pytest.raises(FileExistsError):
        timing.make_plan(path)


@pytest.mark.parametrize("delayed_hp,delayed_result,numeric", [(.3, "lost", True),
                                                             (.3, "won", True),
                                                             (.6, "won", False)])
def test_proposed_contrast_never_establishes_readiness_and_checks_provenance(
        tmp_path, monkeypatch, delayed_hp, delayed_result, numeric):
    monkeypatch.setattr(timing, "committed_revision", lambda *a: "revision")
    monkeypatch.setattr(timing, "source_fingerprints", lambda *a: {"src": "hash"})
    path = tmp_path / "plan.json"
    plan = timing.make_plan(path)
    for job in plan["jobs"]:
        if job["arm"] not in ("contact", "delayed"):
            continue
        directory = tmp_path / f"block-{job['block']}-{job['arm']}"
        directory.mkdir()
        terminal = ending()
        is_contact = job["arm"] == "contact"
        terminal["result"] = "won" if is_contact else delayed_result
        for unit in terminal["final"]["benchmark"]["units"]:
            unit["hp"] = .6 if is_contact else delayed_hp
        ep = episode(directory, [view(), terminal])
        (ep / "result.json").write_text(json.dumps({
            "status": terminal["result"], "setup_checks": {"passed": True},
            "policy": job["args"][job["args"].index("--policy") + 1]}))
        (directory / "manifest.json").write_text(json.dumps({
            k: plan[k] for k in ("source_revision", "source_files", "scenario")} |
            {"setup_checks": {"passed": True}}))
    report = evidence.summarize(path)
    assert report["proposed_numerical_contrast"] is numeric
    assert report["readiness"] == "unverified"
    wrong = tmp_path / "block-1-contact/manifest.json"
    raw = json.loads(wrong.read_text())
    raw["source_revision"] = "different"
    wrong.write_text(json.dumps(raw))
    assert evidence.summarize(path)["proposed_numerical_contrast"] is False


def test_play_logs_windows_stamp_of_the_named_observation(tmp_path):
    from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation

    from twwarhammer3.battle.play import play_episode
    from twwarhammer3.battle.scripted import Hold

    class NewFileDuringDecision(FakeMailbox):
        def wait_observation(self, **kwargs):
            obs = super().wait_observation(**kwargs)
            self.written_ns = 1000000000 + obs["seq"] * 1000000000
            return obs

        def read_observation(self):
            self.written_ns = 99000000000
            return bridge_observation(99, 99000)

    mailbox = NewFileDuringDecision([bridge_observation(0, 0), bridge_observation(1, 1000),
                                    bridge_observation(2, 2000, result="won")])
    directory = tmp_path / "episode"
    result = play_episode(directory, CONFIG, Hold, mailbox, not_battle=None)
    assert result["status"] == "won"
    rows = [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]
    logged = next(r for r in rows if r["kind"] == "observation")
    assert logged["latest_seq"] == 1
    assert logged["latest_written_windows_ns"] == 2000000000


def test_unreadable_intermediate_identity_does_not_erase_engine_outcome(tmp_path):
    unreadable = view(2000)
    unreadable["friendly"][0] = {"id": "f2", "error": "getter failed"}
    report = evidence.annotate(episode(tmp_path, [view(), unreadable, ending()]))
    assert report["engine_result"] == "won"
    assert report["H"] is None
    assert report["issues"]


def test_terminal_ack_failure_retains_engine_outcome_and_condition(tmp_path):
    from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation

    from twwarhammer3.battle.play import play_episode
    from twwarhammer3.battle.scripted import Hold

    class FailedFeedback(Hold):
        def acknowledge(self, *args):
            raise RuntimeError("failed terminal feedback")

    terminal = bridge_observation(2, 2000, result="won", ack=True)
    terminal["final"] = {"benchmark": {"time_ms": 2000, "units": [{"id": "f1", "hp": .7}]}}
    mailbox = FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000), terminal])
    directory = tmp_path / "episode"
    result = play_episode(directory, CONFIG, FailedFeedback, mailbox, not_battle=None,
                          scenario={"behaviour_defaults": True})
    assert result["status"] == "policy_failure"
    assert result["engine_ending"]["result"] == "won"
    assert result["terminal_condition"] == terminal["final"]["benchmark"]
    assert evidence.annotate(directory)["engine_result"] == "won"


def test_partial_trace_does_not_erase_independently_recorded_engine_ending(tmp_path):
    directory = episode(tmp_path, [view()])
    (directory / "result.json").write_text(json.dumps({
        "status": "interrupted", "engine_ending": {"result": "won", "battle_ms": 5000}}))
    with (directory / "trace.jsonl").open("a") as file:
        file.write('\n{"kind":"observation",')
    report = evidence.annotate(directory)
    assert report["engine_result"] == "won"
    assert report["H"] is None and report["issues"]
