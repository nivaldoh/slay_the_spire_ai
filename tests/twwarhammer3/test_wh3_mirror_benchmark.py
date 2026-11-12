"""Owner's simple-score contract, challenged independently of engine totals.

The Lua cases check calls/readbacks against a fake engine, not the live game's values.
The agreed screenshot comparison remains necessary for live measurement correctness.
"""

import io
import json
import signal
import time
import urllib.error
from copy import deepcopy

import pytest
from wh3_lua import load_battle, runtime

from gameai.ledger import BudgetExhausted, Ledger
from gameai.llm import APIError, post
from twwarhammer3.battle import benchmark, llm, play, setup
from twwarhammer3.protocol import PolicyFailure, ProtocolError


def units():
    return [{"id": f"f{i}", "hp": 1, "men": 100, "wavering": False, "routing": False,
             "shattered": False, "departed": False} for i in range(1, 6)]


def ended(outcome="won"):
    return {"status": outcome, "engine_ending": {"result": outcome},
            "setup_checks": {"rosters": True}, "start": {"friendly": {f"f{i}": {}
                                                                         for i in range(1, 6)}},
            "benchmark": {"version": benchmark.VERSION, "units": units()}}


def test_hand_calculation_and_rally_uses_current_flags():
    rows = units()
    rows[1].update(hp=.5, wavering=True)  # .5 * .8 = .4
    rows[2].update(hp=.6, wavering=True, routing=True)  # strongest only: .6 * .5 = .3
    rows[3].update(hp=.9, shattered=True)
    rows[4].update(hp=.8, departed=True)
    score = benchmark.condition([u["id"] for u in rows], rows)
    assert score["condition"] == pytest.approx(34)  # (1 + .4 + .3 + 0 + 0) / 5 * 100
    rows[2].update(wavering=False, routing=False)
    assert benchmark.condition([u["id"] for u in rows], rows)["condition"] == pytest.approx(40)
    rows[0]["men"] = 0
    assert benchmark.condition([u["id"] for u in rows], rows)["condition"] == pytest.approx(20)


@pytest.mark.parametrize("fault", ["absent", "hp", "routing", "men", "departed", "error", "nan"])
def test_missing_reads_never_become_destroyed_units(fault):
    rows = units()
    if fault == "absent":
        rows.pop()
    elif fault == "error":
        rows[-1]["error"] = "failed engine read"
    elif fault == "nan":
        rows[-1]["hp"] = float("nan")
    else:
        rows[-1].pop(fault)
    assert benchmark.condition([f"f{i}" for i in range(1, 6)], rows)["condition"] is None


def test_outcome_first_timer_wins_and_late_errors_stand():
    won, lost = ended(), ended("lost")
    won["benchmark"]["units"] = [dict(u, hp=.01) for u in units()]
    won.update(status="budget_exhausted", error="cleanup", ended_by="time_limit")
    assert benchmark.evaluate(won)["rank"] > benchmark.evaluate(lost)["rank"]
    assert benchmark.evaluate({"status": "policy_failure", "battle": "b1"})["outcome"] is None
    won["benchmark"]["units"].pop()
    assert benchmark.evaluate(won)["outcome"] == "won"
    assert benchmark.evaluate(won)["condition"] is None


def test_no_repairs_or_partial_salvage(tmp_path):
    sent = []

    def send(body):
        sent.append(body)
        return {"id": "reply", "status": "completed", "usage": {
            "input_tokens": 10, "output_tokens": 10}, "output": [{"type": "message",
            "content": [{"type": "output_text", "text": json.dumps({"orders": [
                {"unit": "not-ours", "type": "halt"}], "notes": None, "reason": "bad"})}]}]}

    policy = llm.LLMPolicy("claude-haiku-5-5", "low", Ledger(tmp_path / "spend", 2),
                           send=send, provider="anthropic", benchmark=True)
    with pytest.raises(PolicyFailure):
        policy.decide({"friendly": [], "enemy": [], "seq": 1, "time_ms": 0})
    assert len(sent) == 1
    assert len(list(policy.api.drain_exchanges())[0]["attempts"]) == 1


def test_failed_response_no_resend_and_uncertain_transport_one_request(tmp_path, monkeypatch):
    calls = []

    def fail(request, timeout):
        calls.append(timeout)
        raise urllib.error.HTTPError("https://offline", 503, "unavailable", {}, io.BytesIO(b"bad"))

    monkeypatch.setattr("gameai.llm.urllib.request.urlopen", fail)
    with pytest.raises(APIError):
        post("dummy", {}, attempts=1, timeout_s=60)
    assert calls == [60]
    policy = llm.LLMPolicy("claude-haiku-5-5", "low", Ledger(tmp_path / "spend", 2),
                           send=lambda body: {"status": "failed", "error": "server",
                           "usage": {"input_tokens": 10, "output_tokens": 0}},
                           provider="anthropic", benchmark=True)
    with pytest.raises(APIError) as error:
        policy.api.ask("x", llm.REPLY_SCHEMA, json.loads, retries=0)
    assert len(error.value.attempts) == 1


def test_per_battle_limits_include_failed_calls_and_keep_cumulative_spend(tmp_path):
    ledger = Ledger(tmp_path / "spend", 10)
    ledger.charge(.5, reason="earlier job")
    battle = benchmark.BattleBudget(ledger)
    for _ in range(200):
        battle.reserve(.001)
        battle.charge(.001, estimated=True)
        battle.release(.001)
    with pytest.raises(BudgetExhausted, match="200"):
        battle.reserve(.001)
    next_battle = benchmark.BattleBudget(ledger)
    next_battle.reserve(.01)
    next_battle.release(.01)
    with pytest.raises(BudgetExhausted, match="battle allowance"):
        next_battle.reserve(2.01)
    assert ledger.spent == pytest.approx(.7)
    assert len(ledger.path.read_text().splitlines()) == 201


def test_plan_report_keeps_all_attempts_and_preserves_outcomes(tmp_path):
    plan = tmp_path / "pilot.json"
    planned = benchmark.make_plan(plan, "pilot", 2)
    assert [job["controller"] for job in planned["jobs"]] == [
        "hold", "attack_nearest", "rush_nearest"]
    job = planned["jobs"][0]
    directory = tmp_path / "pilot-01"
    episode = directory / "episode-0000"
    episode.mkdir(parents=True)
    (directory / "manifest.json").write_text(json.dumps({
        "source_revision": planned["source_revision"], "status": "completed",
        "scenario": setup.scenarios()[benchmark.SCENARIO], "config": {
            "scenario": benchmark.SCENARIO, "policy": "hold", "episodes": 1,
            "provider": "anthropic"}}))
    result = ended()
    result.update(battle="b1", policy="hold", status="policy_failure", error="cleanup failed")
    (episode / "result.json").write_text(json.dumps(result))
    (episode / "trace.jsonl").write_text(
        json.dumps({"kind": "forfeit", "error": "APIError"}) + "\n")
    data = benchmark.report(plan, tmp_path / "report")
    assert data["planned"] == 3 and data["completed"] == 1 and data["never_started"] == 2
    assert data["outcomes"] == {"won": 1, "draw": 0, "lost": 0}
    assert data["error_categories"] == {"forfeit": 1, "episode": 1}
    assert data["rows"][0]["condition"] == 100
    assert data["rows"][0]["output"] == job["output"]
    assert all((tmp_path / ("report" + ext)).exists() for ext in (".json", ".txt", ".html"))
    model_plan = benchmark.make_plan(tmp_path / "model.json", "model", 2)
    assert len(model_plan["jobs"]) == 5
    assert all("claude-haiku-5-5" in j["controller"] for j in model_plan["jobs"])


def test_total_deadline_interrupts_trickling_or_stalled_send_without_resend(monkeypatch):
    seen = []
    before = signal.getsignal(signal.SIGALRM)

    def stalled(*args, **kwargs):
        seen.append(kwargs)
        time.sleep(1)

    monkeypatch.setattr(benchmark, "READ_TIMEOUT_S", .02)
    monkeypatch.setattr(benchmark, "post", stalled)
    with pytest.raises(APIError) as error:
        benchmark.send_once("dummy", {}, provider="anthropic")
    assert error.value.uncertain_attempts == 1
    assert len(seen) == 1 and seen[0]["attempts"] == 1
    assert signal.getitimer(signal.ITIMER_REAL) == (0, 0)
    assert signal.getsignal(signal.SIGALRM) == before


def test_queue_failures_and_capture_errors_are_not_silent(tmp_path):
    plan = tmp_path / "pilot.json"
    declared = benchmark.make_plan(plan, "pilot", 2)
    (tmp_path / "pilot-state.json").write_text(json.dumps({"status": "failed", "error": "key",
        "completed": [{"output": declared["jobs"][0]["output"], "exit_code": 2}]}))
    directory = tmp_path / "pilot-01/episode-0000"
    directory.mkdir(parents=True)
    (directory / "stills.json").write_text(json.dumps([
        {"status": "capture_failed", "error": "capture failed"}]))
    data = benchmark.collect(plan)
    assert data["error_categories"] == {"queue": 1, "screenshot": 1}
    assert data["rows"][0]["not_started_reason"] == "key"
    assert data["completed"] == 0 and data["never_started"] == 3


def test_foreign_profile_controller_or_source_is_never_credited(tmp_path):
    plan = tmp_path / "model.json"
    declared = benchmark.make_plan(plan, "model", 2)
    episode = tmp_path / "model-01/episode-0000"
    episode.mkdir(parents=True)
    (episode / "result.json").write_text(json.dumps(ended()))
    (episode.parent / "manifest.json").write_text(json.dumps({
        "source_revision": declared["source_revision"], "scenario": {"name": "foreign"},
        "config": {"policy": "hold", "scenario": "foreign", "episodes": 1}}))
    data = benchmark.collect(plan)
    assert data["completed"] == 0 and data["engine_completed"] == 1
    assert data["rows"][0]["recorded_engine_outcome"] == "won"
    assert data["rows"][0]["condition"] is None
    assert data["error_categories"]["provenance"] == 1


def test_first_ending_measurements_are_frozen_and_private():
    result = {}
    observation = {"result": "won", "time_ms": 100, "final": {"benchmark": {"units": units()}}}
    play.record_ending(result, observation, {"benchmark": benchmark.VERSION})
    first = deepcopy(result)
    play.record_ending(result, {**observation, "time_ms": 200, "final": {}},
                       {"benchmark": benchmark.VERSION})
    assert result == first
    assert "final" not in play.public(observation, {})
    assert play.public(observation, {}) == play.public({**observation, "final": {"secret": 42}}, {})


def test_lua_terminal_health_uses_unit_bars_and_explicit_departure():
    lua = runtime()
    lua.execute("""
        function get(unit, key, default)
            if unit[key] == nil then return default end return unit[key]
        end
        function round(value, digits) return value end
        state = {friendly_ids = {'f1', 'f2', 'f3'}, friendly = {
            f1 = {unit = {unary_hitpoints=.73, number_of_men_alive=40, is_deployed=true,
                         is_routing=true, is_wavering=false, is_shattered=false}},
            f2 = {unit = {unary_hitpoints=.4, number_of_men_alive=10,
                         is_deployed=false, is_deploying=false}},
            f3 = {unit = {}}}}
    """)
    read = load_battle(lua, "benchmark_condition")
    measured = read(123)
    rows = list(measured["units"].values())
    assert measured["time_ms"] == 123
    assert rows[0]["hp"] == .73 and rows[0]["men"] == 40
    assert rows[0]["routing"] is True and rows[0]["departed"] is False
    assert rows[1]["departed"] is True
    assert rows[2]["hp"] is None and rows[2]["men"] is None and rows[2]["departed"] is None


def test_profile_is_explicit_and_rejects_missing_toggle_measurements():
    profile = setup.scenarios()[benchmark.SCENARIO]
    # Owner, 2026-11-02: add two enemy Swordsmen; our original five stay unchanged.
    assert len(profile["player"]["units"]) == 5
    assert len(profile["enemy"]["units"]) == 7
    assert profile["expect"]["difficulty"] == "ai_level_normal"
    assert "scoring" not in profile and not profile["player"]["lord"]
    with pytest.raises(ProtocolError, match="behaviour"):
        setup.check_battle(profile, {"setup": {}, "friendly": [{"id": "f1"}]})


def test_legacy_report_uses_preserved_engine_endings_for_benchmark_denominators(tmp_path):
    from wh3_fixtures import make_job

    from twwarhammer3.battle import report

    job = make_job(tmp_path, "late", [("hold", .1, "won"), ("hold", .1, "policy_failure")])
    manifest_path = job / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["scenario"] = setup.scenarios()[benchmark.SCENARIO]
    manifest_path.write_text(json.dumps(manifest))
    path = job / "episode-0001/result.json"
    result = json.loads(path.read_text())
    result["engine_ending"] = {"result": "won"}
    path.write_text(json.dumps(result))
    data = report.collect([job])
    assert data["groups"][0]["controllers"][0]["win_rate"] == 1


def test_factory_wires_one_request_budget_and_deadline(tmp_path, monkeypatch):
    from twwarhammer3.battle import controllers

    monkeypatch.setattr(controllers, "api_key", lambda provider: "dummy")
    config = {"scenario": benchmark.SCENARIO, "policy": "llm_rules", "provider": "anthropic",
              "model": benchmark.MODEL, "effort": "low", "budget_usd": 2}
    ledger = Ledger(tmp_path / "spend", 2)
    factory = controllers.factories(config, _ledger=ledger)["llm_rules"]
    first, second = factory(), factory()
    assert first.api.send.func is benchmark.send_once
    assert first.api.send.keywords == {"provider": "anthropic"}
    assert first.api.failed_resends == 0 and first.api.transport_attempts == 1
    assert first.api.ledger is not second.api.ledger
    assert first.api.ledger.ledger is ledger


def test_lua_sets_both_armies_toggles_and_releases_enemy_control():
    lua = runtime()
    lua.execute("""
        local function unit()
            return {values={fire_at_will=false, skirmish=true, defend=true},
                can_use_behaviour=function(self, key) return self.values[key] ~= nil end,
                is_behaviour_active=function(self, key) return self.values[key] end}
        end
        local function controller()
            return {add_units=function(self, u) self.unit=u end,
                take_control=function(self) self.owned=true end,
                release_control=function(self) self.owned=false end,
                change_behaviour_active=function(self, key, value) self.unit.values[key]=value end}
        end
        friendly, enemy = unit(), unit()
        friendly_controller, enemy_controller = controller(), controller()
        friendly_controller.unit=friendly
        friendly_controller.owned=true
        state={friendly_ids={'f1'}, enemy_ids={'e1'},
            friendly={f1={unit=friendly, controller=friendly_controller}},
            enemy={e1={unit=enemy, army={create_unit_controller=function()
                return enemy_controller end}}}}
    """)
    _, _, read = load_battle(lua, "BEHAVIOURS", "get", "benchmark_behaviours")
    measured = read()
    for side, uid in (("friendly", "f1"), ("enemy", "e1")):
        assert measured[side][uid]["fire_at_will"] is True
        assert measured[side][uid]["skirmish"] is False
        assert measured[side][uid]["defend"] is False
    assert lua.globals().friendly_controller["owned"] is True
    assert lua.globals().enemy_controller["owned"] is False


def test_engine_ending_during_a_budget_error_is_retained(tmp_path):
    from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation

    from twwarhammer3.battle.scripted import Hold

    terminal = bridge_observation(3, 2000, result="won")
    terminal["final"] = {"benchmark": {"units": units(), "time_ms": 2000}}

    class BudgetPolicy(Hold):
        def decide(self, observation):
            raise BudgetExhausted("cap")

    mailbox = FakeMailbox([bridge_observation(0, 0, phase="Loading"),
                           bridge_observation(2, 1000)])
    mailbox.read_observation = lambda: terminal
    result = play.play_episode(tmp_path / "episode", CONFIG, BudgetPolicy, mailbox,
                               not_battle=None, scenario={"benchmark": benchmark.VERSION})
    assert result["status"] == "budget_exhausted"
    assert result["engine_ending"]["result"] == "won"
    assert result["benchmark"]["units"] == units()
    assert mailbox.requests == []
