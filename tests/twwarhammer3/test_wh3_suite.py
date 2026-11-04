"""The coordination suite: plans, measures and the comparison, on planted cases.

The expected values are worked by hand from each case, not recorded from the code. These
establish the arithmetic only; whether a measure means what it says needs real battles.
"""
import json

import pytest

from gameai.ledger import Ledger
from gameai.provenance import REPO_ROOT
from twwarhammer3.battle import benchmark, configured, graph, suite, team
from twwarhammer3.battle.setup import check_battle, scenarios, validate_declaration
from twwarhammer3.protocol import ProtocolError


def unit(id, state=(), men=100, x=0, z=0, kind="infantry"):
    return {"id": id, "state": list(state), "men": men, "x": x, "z": z, "class": kind}


def frame(seconds, friendly, enemy=()):
    return {"time_ms": seconds * 1000, "friendly": list(friendly), "enemy": list(enemy)}


def test_a_piecemeal_army_shows_a_larger_spread_than_one_that_arrives_together():
    together = [frame(10, [unit("f1", ["melee"]), unit("f2", ["melee"]), unit("f3", ["melee"])])]
    piecemeal = [frame(10, [unit("f1", ["melee"]), unit("f2"), unit("f3")]),
                 frame(40, [unit("f1", ["melee"]), unit("f2", ["melee"]), unit("f3")]),
                 frame(70, [unit("f1", ["melee"]), unit("f2", ["melee"]), unit("f3", ["melee"])])]
    assert suite.coordination(together)["spread_s"] == 0
    assert suite.coordination(piecemeal)["spread_s"] == 30  # the median unit joined at 40 s
    assert suite.coordination(piecemeal)["first_contact_s"] == 10


def test_idle_share_counts_able_melee_units_after_contact_and_skips_shooters_and_routers():
    frames = [
        frame(1, [unit("f1", ["idle"])]),  # before contact: not counted
        frame(2, [unit("f1", ["melee"]), unit("f2", ["idle"]), unit("f3", ["moving"]),
                  unit("gun", ["idle"], kind="missile"), unit("f4", ["idle", "routing"])]),
    ]
    assert suite.coordination(frames)["idle_share"] == pytest.approx(1 / 3, abs=.001)


def test_local_share_is_men_near_the_fight_and_ignores_far_or_routing_men():
    frames = [frame(5, [unit("f1", ["melee"], men=100), unit("f2", men=100, x=50),
                        unit("far", men=500, x=400)],
                    [unit("e1", men=100, x=10), unit("gone", ["routing"], men=900, x=10),
                     unit("e2", men=900, x=400)])]
    assert suite.coordination(frames)["local_share"] == pytest.approx(200 / 300, abs=.001)


def test_a_battle_without_contact_has_no_coordination_reading():
    assert set(suite.coordination([frame(5, [unit("f1", ["idle"])])]).values()) == {None}


def test_taken_reads_the_engines_enemy_totals_and_never_invents_a_value():
    assert suite.taken({"final": {"enemy": {"men0": 200, "active_men": 150}}}) == 25
    assert suite.taken({"final": {"enemy": {"men0": 200}}}) is None
    assert suite.taken({}) is None


def test_killed_counts_dead_men_so_a_won_battle_need_not_read_100():
    result = {"final": {"enemy": {"men0": 200, "men": 90, "active_men": 0}}}
    assert suite.taken(result) == 100 and suite.killed(result) == 55
    assert suite.killed({}) is None


def test_the_score_rewards_what_a_loss_took_as_well_as_what_it_kept():
    fled = {"own": 40, "taken": 2}  # the first screen's shape: routed nearly intact
    fought = {"own": 0, "taken": 60}
    rows = [{"outcome": "lost", **fled}], [{"outcome": "lost", **fought}]
    assert suite.scenario_value(rows[1]) > suite.scenario_value(rows[0])


def test_commander_is_also_read_against_skills_its_own_executor():
    def battle(arm, outcome):
        return {**row("a", arm, outcome), "status": outcome, **dict.fromkeys(
            ("killed", "battle_s", "usd", "authoring_usd", "calls", "think_s", "age_s",
             "age_p90_s", "plan_age_s", "orders", "refused", "bad_replies", "call_failures",
             "spread_s", "idle_share", "local_share"))}

    arms = suite.summarize([battle("commander", "lost"), battle("skills", "won")])["arms"]
    assert arms["commander"]["control"]["against"] == "skills"
    assert arms["commander"]["control"]["worse"] == 1
    assert "control" not in arms["skills"]


def test_a_win_bound_reads_as_a_range_or_an_upper_bound():
    assert suite.bound_text(suite.win_bound(0, 10)) == "below 26%"
    assert suite.bound_text(suite.win_bound(4, 5)) == "38%-96%"
    assert suite.bound_text(None) is None


def test_win_bounds_and_sign_test_match_the_guidelines_worked_values():
    # evaluation-guidelines.md 7.2: 0 of 10 is below 26%; 4 of 5 is 38-96%.
    assert suite.win_bound(0, 10) == {"method": "exact one-sided 95%", "upper": .259}
    assert suite.win_bound(4, 5) == {"method": "Wilson 95%", "lower": .376, "upper": .964}
    assert suite.win_bound(0, 0) is None
    assert suite.sign_test(6, 0) == .0312  # 2 x (1/2)^6
    assert suite.sign_test(0, 0) is None
    assert suite.sign_test(3, 3) == 1


def row(scenario, arm, outcome, own=0, taken=0):
    return {"scenario": scenario, "arm": arm, "outcome": outcome, "own": own, "taken": taken}


def test_pairing_compares_wins_first_and_skips_a_scenario_either_arm_missed():
    rows = [row("a", "team", "won"), row("a", "single", "lost", own=90, taken=90),
            row("b", "team", "lost", taken=10), row("b", "single", "lost", taken=30),
            row("c", "team", "lost", taken=30), row("c", "single", "lost", taken=30),
            row("d", "team", None), row("d", "single", "won")]
    pair = suite.paired(rows, "team", "single", ["a", "b", "c", "d"])
    assert (pair["better"], pair["worse"], pair["tied"]) == (1, 1, 1)


def test_the_taken_difference_is_paired_by_scenario_with_a_hand_worked_interval():
    rows = [row("a", "team", "lost", taken=30), row("a", "single", "lost", taken=20),
            row("b", "team", "lost", taken=50), row("b", "single", "lost", taken=20),
            row("c", "team", "lost", taken=10)]  # single missed c, so c is not a pair
    gap = suite.taken_difference(rows, "team", "single", ["a", "b", "c"])
    assert gap["scenarios"] == 2 and gap["mean"] == 20
    # gaps 10 and 30: sd 14.14, se 10, t(1) = 12.706, so 20 +- 127.06
    assert gap["t_95"] == [-107.1, 147.1]
    assert suite.taken_difference(rows[:2], "team", "single", ["a"])["t_95"] is None


def test_a_plan_visits_every_pair_once_per_repeat_and_is_repeatable(tmp_path, monkeypatch):
    monkeypatch.setattr(suite.subprocess, "check_output", lambda *a, **k: "abc\n")
    names = ["coord-relief", "coord-pincer"]
    plan = suite.make_plan(tmp_path / "p.json", names, ["hold", "single"], 2, 5, seed=1)
    pairs = [(job["scenario"], job["arm"]) for job in plan["jobs"]]
    assert len(pairs) == 8 and all(pairs.count(pair) == 2 for pair in set(pairs))
    again = suite.make_plan(tmp_path / "q.json", names, ["hold", "single"], 2, 5, seed=1)
    assert pairs == [(job["scenario"], job["arm"]) for job in again["jobs"]]
    assert "--budget-usd" in next(j for j in plan["jobs"] if j["arm"] == "single")["args"]
    assert "--budget-usd" not in next(j for j in plan["jobs"] if j["arm"] == "hold")["args"]
    assert set(plan["scenarios"]) == set(names) and plan["keep_going"]


@pytest.mark.parametrize("names,arms,message", [
    (["kho5-dwf5"], ["hold"], "not a suite-v1"), (["coord-relief"], ["nobody"], "unknown arm")])
def test_a_plan_refuses_what_is_not_in_the_suite(tmp_path, names, arms, message):
    with pytest.raises(ValueError, match=message):
        suite.make_plan(tmp_path / "p.json", names, arms, 1, 5, seed=1)


def test_the_gap_arm_needs_authored_graphs_and_plays_each_scenarios_own(tmp_path, monkeypatch):
    monkeypatch.setattr(suite.subprocess, "check_output", lambda *a, **k: "abc\n")
    with pytest.raises(ValueError, match="--graphs"):
        suite.make_plan(tmp_path / "p.json", ["coord-relief"], ["gap"], 1, 5, seed=1)
    with pytest.raises(ValueError, match="no ready graphs"):
        suite.make_plan(tmp_path / "p.json", ["coord-relief"], ["gap"], 1, 5, seed=1,
                        graphs=tmp_path / "written")
    ready = tmp_path / "written/coord-relief/attempt-2"
    ready.mkdir(parents=True)
    (ready / "manifest.json").write_text('{"status": "ready"}')
    plan = suite.make_plan(tmp_path / "p.json", ["coord-relief"], ["gap"], 1, 5, seed=1,
                           graphs=tmp_path / "written")
    args = plan["jobs"][0]["args"]
    assert args[args.index("--controller-config") + 1] == str(ready)


def test_the_authors_task_is_public():
    scenario = scenarios()["coord-relief"]
    task = suite.author_task(scenario)
    assert "wh_main_emp_inf_halberdiers at x=" in task and "defender" in task
    assert "wh_main_grn_inf_orc_boyz" in task  # the roster is public
    for place in scenario["deployment"]["enemy"]:  # the enemy's start is not
        assert f"x={place['x']}, z={place['z']}" not in task


def test_authoring_writes_three_graphs_a_configured_team_loads(tmp_path):
    end = {"version": graph.VERSION, "entry": "owned", "nodes": {
        "owned": {"op": "owned", "inputs": {}, "next": {"succeeded": "pick", "empty": "owned"}},
        "pick": {"op": "select_target", "inputs": {"units": {"ref": "owned.units"}},
                 "next": {"succeeded": "owned", "empty": "owned"}}}}
    tasks = [{"member": name, "task": "Fight."} for name in team.CLASS_PARTITION]
    canned = ["not json", "not json",  # a whole first try fails; the second succeeds
              json.dumps({"tasks": tasks}), *[json.dumps({"graph_json": json.dumps(end)})] * 3]

    def send(body):
        return {"id": "canned", "status": "completed",
                "usage": {"input_tokens": 100, "output_tokens": 100},
                "output": [{"type": "message", "content": [
                    {"type": "output_text", "text": canned.pop(0)}]}]}

    (tmp_path / "spend.jsonl").touch()
    book = Ledger(tmp_path / "spend.jsonl", 5, must_exist=True)
    totals = suite.author(tmp_path / "written", ["coord-relief"], book, send=send)
    assert totals["coord-relief"]["status"] == "ready" and totals["coord-relief"]["tries"] == 2
    assert not canned
    written = suite.written_graphs(tmp_path / "written", "coord-relief")
    frozen, _, _, artifact = configured.load(written, {"provider": "anthropic"})
    assert set(frozen["members"]) == set(team.CLASS_PARTITION) and frozen["optional"]
    result = {"card": {"disclosure": {"artifact": artifact}}}
    # the failed try's two calls cost money too and count
    assert suite.authoring_usd(result) > totals["coord-relief"]["usd"]
    assert suite.authoring_usd({"card": {}}) == 0


@pytest.mark.parametrize("arm", [arm for arm in suite.ARMS if arm != "gap"])
def test_each_arm_builds_for_a_suite_scenario_without_a_game_or_a_call(arm, tmp_path, monkeypatch):
    from twwarhammer3.battle import controllers
    from twwarhammer3.battle.benchmark import validate_config

    monkeypatch.setattr(controllers, "api_key", lambda provider="openai": "test-only")
    monkeypatch.setattr(configured, "api_key", lambda provider="openai": "test-only")
    (tmp_path / "spend.jsonl").touch()
    args = dict(zip(suite.ARMS[arm][::2], suite.ARMS[arm][1::2]))
    monkeypatch.chdir(REPO_ROOT)
    config = {"scenario": "coord-relief", "policy": args["--policy"], "episodes": 1,
              "provider": args.get("--provider", "openai"), "budget_usd": 5,
              "ledger": str(tmp_path / "spend.jsonl"), "delay_seconds": "0",
              "controller_config": args.get("--controller-config"), "start_timeout": 900,
              "episode_timeout": 1320, "observe_ms": 1000, "tick_ms": 250}
    validate_config(scenarios()["coord-relief"], config)
    policy = controllers.factories(config)[config["policy"]]()
    assert callable(policy.decide) and callable(policy.metadata)
    getattr(policy, "close", lambda: None)()


def test_every_suite_scenario_declares_a_complete_authored_or_native_start():
    entries = {k: v for k, v in scenarios().items() if v.get("benchmark") == benchmark.SUITE}
    assert len(entries) >= 6
    limits = {"episode_timeout": 1320, "run_timeout": 2280, "start_timeout": 900, "episodes": 1}
    for scenario in entries.values():
        validate_declaration(scenario, limits)
        assert scenario.get("tests") and not scenario.get("scoring")
        for side, army in (("friendly", "player"), ("enemy", "enemy")):
            placed = scenario.get("deployment", {}).get(side)
            if placed is not None:
                assert len(placed) == len(scenario[army]["units"])


def test_condition_takes_any_army_size_in_the_suite_but_five_in_the_mirror():
    units = [{"id": f"f{i}", "hp": 1, "men": 1, "wavering": False, "routing": False,
              "shattered": False, "departed": False} for i in range(1, 8)]
    ids = [u["id"] for u in units]
    assert benchmark.condition(ids, units, None)["condition"] == 100
    assert benchmark.condition(ids, units)["condition"] is None


def test_evaluate_reads_a_suite_battle_and_keeps_its_version():
    units = [{"id": "f1", "hp": .5, "men": 10, "wavering": False, "routing": True,
              "shattered": False, "departed": False}]
    result = {"status": "lost", "setup_checks": {"ok": True}, "start": {"friendly": {"f1": {}}},
              "benchmark": {"version": benchmark.SUITE, "units": units}}
    scored = benchmark.evaluate(result)
    assert scored["version"] == benchmark.SUITE and scored["condition"] == 25


def battle(defend=False):
    toggles = {"friendly": {"f1": {"supported": ["defend"], "defend": defend},
                            "f2": {"supported": []}},
               "enemy": {"e1": {"supported": []}}}
    return ({"benchmark": benchmark.SUITE, "expect": {"unit_scale": .75, "realism": False,
                                                      "player_defends": True}},
            {"setup": {"benchmark_behaviours": toggles},
             "friendly": [{"id": "f1", "type": "a"}, {"id": "f2", "type": "monster"}],
             "enemy_roster": [{"id": "e1", "type": "gun"}]})


def test_a_suite_army_with_no_toggles_on_a_unit_passes_but_a_wrong_toggle_does_not():
    with pytest.raises(ProtocolError, match="f1 defend"):
        check_battle(*battle(defend=True))
    with pytest.raises(ProtocolError, match="unit_scale"):  # past the toggles, to the next read
        check_battle(*battle())


ROSTER = [{"id": "f1", "type": "sword", "class": "infantry"},
          {"id": "f2", "type": "gun", "class": "missile"},
          {"id": "f3", "type": "knight", "class": "cavalry"},
          {"id": "f4", "type": "lord", "class": "lord"}]


class Quiet:
    def __init__(self):
        self.closed = False

    def decide(self, observation):
        return []

    def acknowledge(self, ack, latency):
        pass

    def metadata(self):
        return {}

    def close(self):
        self.closed = True


def class_team(roster):
    policies = {name: Quiet() for name in team.CLASS_PARTITION}
    policy = team.TeamPolicy({name: (kinds, policies[name])
                              for name, kinds in team.CLASS_PARTITION.items()},
                             army_owner=team.CLASS_OWNER, optional=True, max_age_ms=None)
    policy.decide({"battle": "b", "seq": 1, "time_ms": 0, "friendly": roster, "enemy": []})
    return policy, policies


def test_a_class_team_owns_every_unit_exactly_once():
    policy, _ = class_team(ROSTER)
    owned = {name: sorted(member.units) for name, member in policy.members.items()}
    assert owned == {"ranged": ["f2"], "mobile": ["f3"], "front": ["f1", "f4"]}
    policy.close()


def test_a_class_with_no_units_is_dropped_and_its_army_orders_move():
    policy, policies = class_team([row for row in ROSTER if row["class"] in ("missile", "cavalry")])
    assert set(policy.members) == {"ranged", "mobile"} and policy.army_owner == "ranged"
    assert policies["front"].closed
    policy.close()


def test_a_later_unit_of_a_class_joins_its_member():
    policy, _ = class_team(ROSTER)
    arrived = [*ROSTER, {"id": "f5", "type": "pistol", "class": "missile_cavalry"}]
    policy.selected = None
    policy.decide({"battle": "b", "seq": 2, "time_ms": 100, "friendly": arrived, "enemy": []})
    assert "f5" in policy.members["mobile"].units
    policy.close()


def test_the_gap_arm_loads_without_credentials_and_keeps_the_class_split():
    path = REPO_ROOT / "configs/twwarhammer3/graphs/suite-gap.json"
    frozen, _, goal_models, _ = configured.load(path, {"provider": "anthropic"})
    assert goal_models == {(benchmark.MODEL, benchmark.EFFORT)} and frozen["optional"]
    declared = {name: member["unit_types"] for name, member in frozen["members"].items()}
    assert declared["front"] is None
    assert declared["ranged"] == list(team.CLASS_PARTITION["ranged"])
    assert declared["mobile"] == list(team.CLASS_PARTITION["mobile"])


def test_the_suite_prompt_states_the_public_rule_and_only_for_the_suite():
    from twwarhammer3.battle.llm import render_mode

    assert "destroy or rout" in render_mode({"type": "land_normal", "benchmark": benchmark.SUITE})
    assert "destroy or rout" not in render_mode({"type": "land_normal"})


def test_a_battle_never_started_keeps_its_row_with_no_measures(tmp_path):
    plan = {"benchmark": benchmark.SUITE, "source_revision": "x",
            "scenarios": {"s": {}}, "jobs": [{"output": str(tmp_path / "never"), "arm": "hold",
                                              "scenario": "s", "controller": "hold"}]}
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    data = suite.gather([path])
    assert data["planned"] == 1 and data["completed"] == 0
    assert data["rows"][0]["status"] == "never_started" and data["rows"][0]["taken"] is None
    assert data["summary"]["arms"]["hold"]["planned"] == 1
    assert data["summary"]["arms"]["hold"]["win_bound"] is None


def test_a_suite_goal_model_has_no_retries_and_a_battle_allowance(tmp_path, monkeypatch):
    from twwarhammer3.battle import controllers

    monkeypatch.setattr(controllers, "api_key", lambda provider="openai": "test-only")
    monkeypatch.setattr(configured, "api_key", lambda provider="openai": "test-only")
    (tmp_path / "spend.jsonl").touch()
    config = {"scenario": "coord-relief", "provider": "anthropic", "budget_usd": 5,
              "ledger": str(tmp_path / "spend.jsonl")}
    make = configured.factory(REPO_ROOT / suite.GRAPH_TEMPLATE, config)
    policy = make()
    api = next(iter(policy.members.values())).policy.api
    assert api.failed_resends == 0 and api.transport_attempts == 1
    assert isinstance(api.ledger, benchmark.BattleBudget)
    assert api.ledger.battle_usd == benchmark.SUITE_BATTLE_USD
    policy.close()


def test_a_dry_shooter_no_longer_stops_the_rest_of_its_group():
    from twwarhammer3.battle.skill_contracts import SkillRun, preconditions

    view = {"time_ms": 1000, "friendly": [
        {"id": "a", "men": 10, "x": 0, "z": 0, "ammo": 5, "range": 150, "class": "missile"},
        {"id": "b", "men": 10, "x": 5, "z": 0, "ammo": 0, "range": 150, "class": "missile"}],
        "enemy": [{"id": "e", "men": 10, "x": 50, "z": 0, "state": []}]}
    inputs = {"units": ["a", "b"], "target": "e"}
    assert preconditions("shoot", inputs, view) is None
    status, orders, _ = SkillRun("shoot", inputs, 0).tick(view)
    assert status == "running" and [order["unit"] for order in orders] == ["a"]
    view["friendly"][0]["ammo"] = 0
    assert preconditions("shoot", inputs, view) == "no ammunition"
    run = SkillRun("shoot", inputs, 0)
    assert run.tick(view)[0] == "failed"  # none can fire: not a false success


def test_a_class_member_is_told_which_ids_it_may_order_and_a_two_member_team_is_not():
    view = {"friendly": [{"id": "f2"}, {"id": "f7"}], "allies": [{"id": "f1", "men": 0}]}
    told = team.ClassTeamLLM.section_of(view)
    assert "The only ids you may order: f2, f7." in told
    assert team.TeamLLM.section_of(view) == team.team_section(view)


def test_each_unit_joins_the_declared_group_nearest_its_start():
    groups = [{"name": "West", "x": -100, "z": 0}, {"name": "East", "x": 100, "z": 0}]
    units = {"f1": {"x": -90, "z": 5}, "f2": {"x": 80, "z": 0}, "f3": {"x": None, "z": 0}}
    assert suite.groups_of(units, groups) == {"f1": "West", "f2": "East"}


def test_lanes_show_when_each_group_fought_and_when_it_had_no_able_unit_left():
    members = {"a": "West", "b": "East"}
    frames = [frame(1, [unit("a"), unit("b")]),
              frame(2, [unit("a", ["melee"]), unit("b")]),
              frame(3, [unit("a", ["melee"]), unit("b", ["melee"])]),
              frame(4, [unit("a", ["routing"]), unit("b", ["melee"])])]
    assert suite.lanes(frames, members) == {
        "West": [[1, 1, "ready"], [2, 3, "fight"]],
        "East": [[1, 2, "ready"], [3, 4, "fight"]]}


def test_a_recorder_gap_splits_a_stretch_only_when_it_is_long():
    frames = [frame(1, [unit("a")]), frame(3, [unit("a")]), frame(20, [unit("a")])]
    assert suite.lanes(frames, {"a": "West"})["West"] == [[1, 3, "ready"], [20, 20, "ready"]]


def test_every_played_scenarios_notes_name_all_its_units_and_real_groups():
    notes = json.loads((REPO_ROOT / "configs/twwarhammer3/report_notes.json").read_text())
    known = scenarios()
    pictured = [name for name, note in notes["scenarios"].items() if note.get("groups")]
    assert len(pictured) == 6
    for name in pictured:
        note, places = notes["scenarios"][name], known[name]["deployment"]
        for side, groups in (("friendly", note["groups"]), ("enemy", note["enemy"])):
            units = {str(i): place for i, place in enumerate(places[side])}
            assert set(suite.groups_of(units, groups).values()) == {g["name"] for g in groups}
        names = {group["name"] for group in note["groups"]}
        assert all(a in names and b in names for a, b in note["links"])
        assert note["question"] and note["why"] and all(g["job"] for g in note["groups"])
        rule = note["answer"]
        foes = {group["name"] for group in note["enemy"]}
        assert all(rule[key] in names | foes for key in ("a", "b", "who") if key in rule)
        assert set(rule.get("among", [])) <= names
    methods = notes["suite"]["methods"]
    assert set(notes["suite"]["order"]) == set(methods) <= set(suite.ARMS)


def positioned(id, x, state=()):
    return unit(id, state, x=x)


def test_the_reserve_joins_a_group_only_if_it_fights_beside_it():
    members = {"w": "West", "e": "East", "r": "Reserve"}
    rule = {"kind": "joined", "who": "Reserve", "among": ["West", "East"]}
    frames = [frame(10, [positioned("w", -100), positioned("e", 100), positioned("r", 0)]),
              frame(130, [positioned("w", -100), positioned("e", 100),
                          positioned("r", 90, ["melee"])])]
    assert suite.answer(rule, frames, members, {}) == "Reserve joined the East at 2:10"
    assert suite.answer(rule, frames[:1], members, {}) == "Reserve never fought"
    # 2026-11-04 review: a reserve attacked where it stood had joined nobody.
    alone = [frame(176, [positioned("e", 300), positioned("r", 0, ["melee"])])]
    assert suite.answer(rule, alone, members, {}) == (
        "Reserve first fought away from both groups, at 2:56")


RELIEF = {"kind": "reached", "a": "Garrison", "b": "Column", "text": "Help after {gap}",
          "never": "It never came"}


def test_help_counts_only_once_the_two_fights_are_close():
    members = {"g": "Garrison", "c": "Column"}
    # 2026-11-04 review: the column fighting elsewhere is not help reaching the garrison.
    frames = [frame(30, [positioned("g", 0, ["melee"]), positioned("c", 500)]),
              frame(80, [positioned("g", 0, ["melee"]), positioned("c", 400, ["melee"])])]
    assert suite.answer(RELIEF, frames, members, {}) == "It never came"
    frames.append(frame(125, [positioned("g", 0, ["melee"]), positioned("c", 60, ["melee"])]))
    assert suite.answer(RELIEF, frames, members, {}) == "Help after 1:35"


def test_two_groups_are_read_as_two_fights_with_a_distance_and_a_delay():
    members = {"w": "West", "e": "East"}
    rule = {"kind": "apart", "a": "West", "b": "East", "never": "Only one fought"}
    frames = [frame(40, [positioned("w", -200, ["melee"]), positioned("e", 200)]),
              frame(47, [positioned("w", -200, ["melee"]), positioned("e", 200, ["melee"])])]
    assert suite.answer(rule, frames, members, {}) == "Two fights 400 m apart, starting 0:07 apart"
    assert suite.answer(rule, frames[:1], members, {}) == "Only one fought"


def test_enemy_groups_are_read_from_their_own_first_contact():
    foes = {"e1": "Near", "e2": "Far", "e3": "South"}
    frames = [frame(50, [], [unit("e1", ["melee"])]),
              frame(54, [], [unit("e1", ["melee"]), unit("e2", ["melee"])]),
              frame(95, [], [unit("e3", ["melee"])])]
    waves = {"kind": "waves", "a": "Near", "b": "Far", "text": "{gap} apart", "never": "One wave"}
    assert suite.answer(waves, frames, {}, foes) == "0:04 apart"
    assert suite.answer({"kind": "spread"}, frames, {}, foes) == (
        "No enemy group broke; all 3 in contact by 1:35")
    assert suite.answer({"kind": "spread"}, frames[:2], {}, foes) == (
        "Reached 2 of 3 enemy groups")
    broken = [*frames, frame(120, [], [unit("e1", ["routing"]), unit("e3", ["melee"])])]
    assert suite.answer({"kind": "spread"}, broken, {}, foes) == (
        "Near broke at 2:00; all 3 in contact by 1:35")


def test_a_group_never_seen_fighting_is_not_called_broken():
    foes = {"e1": "West"}
    assert suite.first_broken([frame(9, [], [unit("e1", ["routing"])])], foes) is None


def test_guns_report_their_first_melee_and_the_ammunition_they_spent():
    members = {"g": "Guns"}
    frames = [frame(10, [{**unit("g"), "ammo": 40}]),
              frame(99, [{**unit("g", ["melee"]), "ammo": 10}])]
    rule = {"kind": "guns", "who": "Guns"}
    assert suite.answer(rule, frames, members, {}) == (
        "Guns first in melee at 1:39; fired 75% of their ammunition")
    idle = [frame(10, [{**unit("g"), "ammo": 40}]), frame(99, [{**unit("g"), "ammo": 40}])]
    assert suite.answer(rule, idle, members, {}) == (
        "Guns never in melee; fired 0% of their ammunition")
