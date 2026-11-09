"""The camp attack and two-front defence declarations (emp-chd-camp-v1, ksl-nor-lines-a-v1 and
ksl-nor-lines-b-v1) and the ablation-diff helper wh3_ablation.py.

Reference: the 2026-11-08 designs in runs/siege-evals-20261108 (final-belgrade.md and
final-alesia.md, "Settings", "Rosters", "Map and placements", "Infrastructure"; portfolio.md S8)
and setup.py's field list. Offline only: none of this shows that a card recruits, that a
placement holds in the engine, that the lobby accepts the funds or that the native AI behaves as
the designs expect. The emp-chd-camp-v1 case of the first test also needs
setup.validate_deployment to compare by-type placements with setup.battle_units (the mounted
General), a change to setup.py outside this file.
"""

import json
import math
import unicodedata
from collections import Counter

import pytest
from wh3_ablation import assert_ablation
from wh3_fixtures import bridge_observation

from twwarhammer3.battle import play, setup
from twwarhammer3.protocol import HIDDEN_KEYS

# The three entries in configs/twwarhammer3/scenarios.json cannot carry a comment, so their
# markers are on the battles' pages (docs/judgement.md). The design pages they copy from are
# untracked (runs/siege-evals-20261108/final-belgrade.md and final-alesia.md).
# Camp construction profile and Authored widths (which also covers the Boyar's width in
# ksl-nor-lines-a-v1) are marked on docs/twwarhammer3/camp-eval.md.
# Lines mode, Lines forces, Lines enemy lord, Lines settings, Lines layout, Reserve facing, Norsca
# banner and Lines briefing are marked on docs/twwarhammer3/lines-eval.md.

NAMES = ("emp-chd-camp-v1", "ksl-nor-lines-a-v1", "ksl-nor-lines-b-v1")
# A play job before fill_timeouts: one episode, the default 900 s start cap (__main__.py).
PLAY_CONFIG = {"episodes": 1, "start_timeout": 900, "episode_timeout": None, "run_timeout": None}
# Historical names and the lines' own terms, which no declaration text or job may hold; each
# declaration's withheld list must hold them all. Rests on JUDGEMENT?
# docs/twwarhammer3/lines-eval.md Withheld names.
WITHHELD = ("belgrade", "nandorfehervar", "hunyadi", "szilagyi", "capistran", "mehmed",
            "ottoman", "crusade", "janissar", "sipahi", "sultan", "1456", "hungar", "turk",
            "alesia", "caesar", "vercingetorix", "vercassivellaunus", "labienus", "reginus",
            "rebilus", "sedulius", "gallic", "gaul", "roman", "vallation", "circumvallation",
            "contravallation")
# The designs' own prompt-test names (final-belgrade.md, Infrastructure; final-alesia.md, check 6),
# folded to ASCII and spelled as a job might spell them.
DESIGN_NAMES = ("belgrade", "nandorfehervar", "hunyadi", "szilagyi", "capistrano", "mehmed",
                "ottoman", "crusader", "janissary", "sipahi", "1456", "alesia", "caesar",
                "vercingetorix")
# The mirror axis of the two cases; rests on JUDGEMENT docs/twwarhammer3/lines-eval.md Lines
# layout.
MIRROR_X = 130
HEAVY = {"wh_dlc08_nor_inf_marauder_champions_0", "wh_dlc08_nor_inf_marauder_berserkers_0",
         "wh_dlc08_nor_mon_fimir_0"}
JOB = "lines-r1-017"


def folded(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()


def strings(value):
    """Every key and string value inside a declaration."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, str):
        yield value


def mirror(placement):
    return {**placement, "x": 2 * MIRROR_X - placement["x"],
            "bearing": (360 - placement["bearing"]) % 360}


def spots(placements):
    return Counter(tuple(sorted(placement.items())) for placement in placements)


@pytest.mark.parametrize("name", NAMES)
def test_each_declaration_passes_plays_checks_with_explicit_rosters(name):
    """Wrong versions: a roster left to the game, a missing expect field, a role the first
    observation would contradict, or a status that admits the battle."""
    scenario = setup.load_scenario({"scenario": name})
    config = dict(PLAY_CONFIG)
    setup.fill_timeouts(scenario, config)
    setup.validate_declaration(scenario, config)
    assert (scenario["status"], scenario["split"]) == ("prototype_not_admitted", "development")
    assert scenario["behaviour_defaults"] is True
    defends = scenario["attacker"] == "enemy"
    assert scenario["expect"]["player_defends"] is defends
    assert setup.expected_mode(scenario) == {"type": "land_normal",
                                             "role": "defender" if defends else "attacker"}


@pytest.mark.parametrize("name", NAMES)
def test_every_roster_unit_is_placed_once_under_its_battle_type(name):
    """The engine binds a placement to a unit by the type the unit has in battle, and a mounted
    lord reads his mount's key, so each side's placements must be its battle units as a
    multiset. Wrong versions: a deployment missing one unit; the General placed under his foot
    card; a point off the ±512 m map."""
    scenario = setup.scenarios()[name]
    for side, army in (("friendly", scenario["player"]), ("enemy", scenario["enemy"])):
        placements = scenario["deployment"][side]
        assert Counter(p["type"] for p in placements) == Counter(setup.battle_units(army)), side
        assert all(abs(p["x"]) < 512 and abs(p["z"]) < 512 and p["width"] > 0
                   for p in placements), side


@pytest.mark.parametrize("name", NAMES)
def test_no_declaration_text_names_the_history_or_reaches_a_controller(name):
    """Labels and provenance carry no historical name, and the declaration adds nothing to what
    a controller reads: no benchmark tag, scoring rule or briefing in its view, and a battle
    session with only the behaviour defaults, the private deployment and the evaluator-only
    record. Wrong versions: 'belgrade' or 'alesia' in a name or brief; a benchmark tag or
    briefing that carries them."""
    scenario = setup.scenarios()[name]
    entry = json.loads(setup.SCENARIOS_PATH.read_text())[name]
    texts = [name, *(text for value in (entry, scenario)
                     for text in strings({k: v for k, v in value.items() if k != "withheld"}))]
    assert sorted({word for text in texts for word in WITHHELD if word in folded(text)}) == []
    observation = bridge_observation(1, 1000)
    observation.update(job=JOB, mode={"type": "land_normal", "role": "defender"})
    assert play.public(observation, scenario) == play.public(observation, {})
    # The record rests on JUDGEMENT? src/twwarhammer3/battle/capture.py Private record in scored
    # battles.
    assert play.battle_session(scenario) == {"benchmark": "behaviour-defaults",
                                             "deployment": scenario["deployment"],
                                             "private_record": True}


@pytest.mark.parametrize("name", NAMES)
def test_a_job_that_names_the_history_is_refused_and_a_neutral_one_accepted(name):
    """The job reaches every controller, so play and the owner's recorder refuse one that holds a
    withheld word at a word start (setup.check_job). Wrong versions: no withheld list, which
    accepts any job; a list missing one of the designs' names or of WITHHELD; a word that also
    starts a neutral job, such as camp or lines."""
    scenario = setup.scenarios()[name]
    assert set(WITHHELD) <= set(scenario["withheld"])
    for job in ("belgrade-camp-r1", "alesia-a-r1", "bench-Hunyadi-a", "w-circumvallation-2",
                *(f"{word}-r1" for word in DESIGN_NAMES)):
        with pytest.raises(ValueError, match="withheld word"):
            setup.check_job(scenario, job)
    for job in ("camp-r1-003", JOB, "bench-ksl-nor-lines-hold-20261109"):
        setup.check_job(scenario, job)


def test_case_b_mirrors_every_enemy_placement_of_case_a_and_changes_nothing_else():
    """The friendly army and the town-side group are their own mirror images, so the two cases
    differ only in which side the heavy relief group attacks. Wrong versions: a friendly unit
    moved in b only; one heavy unit left in the west slot in b; a roster or setting changed."""
    a, b = (setup.scenarios()[f"ksl-nor-lines-{case}-v1"] for case in "ab")
    assert {key for key in {*a, *b} if a.get(key) != b.get(key)} == {
        "name", "calibration_change", "deployment"}
    assert b["deployment"]["friendly"] == a["deployment"]["friendly"]
    assert b["deployment"]["enemy"] == [mirror(p) for p in a["deployment"]["enemy"]]
    friendly = a["deployment"]["friendly"]
    assert spots(friendly) == spots(mirror(p) for p in friendly)
    town = [p for p in a["deployment"]["enemy"] if p["z"] > -165]
    assert len(town) == 4 and spots(town) == spots(mirror(p) for p in town)
    for scenario, west in ((a, True), (b, False)):
        xs = [p["x"] for p in scenario["deployment"]["enemy"] if p["type"] in HEAVY]
        assert len(xs) == 4 and all((x < MIRROR_X) is west for x in xs)


class Nearest:
    """Each unit attacks its nearest visible enemy; a unit in ``farthest`` attacks the farthest
    one instead once the battle is past ``after_ms``."""

    def __init__(self, farthest=(), after_ms=0):
        self.farthest, self.after_ms = set(farthest), after_ms

    def decide(self, observation):
        assert not set(HIDDEN_KEYS) & set(observation), "a controller read a hidden key"
        orders = []
        for unit in observation["friendly"]:
            late = observation["time_ms"] > self.after_ms
            pick = max if late and unit["id"] in self.farthest else min
            target = pick(observation["enemy"], key=lambda enemy: math.hypot(
                enemy["x"] - unit["x"], enemy["z"] - unit["z"]))
            orders.append({"unit": unit["id"], "type": "attack", "target": target["id"],
                           "run": False})
        return orders

    def acknowledge(self, ack, latency):
        pass


class ReadsJob(Nearest):
    """Nearest, except that f1's target follows the job name, as a case read from it would."""

    def decide(self, observation):
        self.farthest = set() if observation.get("job") == JOB else {"f1"}
        return super().decide(observation)


def closing_in():
    """Six observations 1 s apart: f1-f3 stand on z = 0 while e1-e3 close in from the north.
    At every step each friendly unit's nearest and farthest enemies differ. Like a recorded
    trace, each carries hidden enemy totals that play never hands a controller."""
    observations = []
    for step in range(6):
        observation = bridge_observation(step + 1, 1000 * (step + 1))
        observation["job"] = JOB
        observation["evaluation"] = {"enemy": {"men": 270, "men0": 270}}
        observation["friendly"] = [
            {"id": f"f{i}", "type": "wh3_main_ksl_inf_kossars_1", "class": "infantry", "x": x,
             "z": 0.0, "men": 67, "men0": 67, "hp": 1.0, "state": [], "target": None}
            for i, x in ((1, 0.0), (2, 100.0), (3, 200.0))]
        observation["enemy"] = [
            {"id": f"e{i}", "type": "wh_dlc08_nor_inf_marauder_spearman_0", "class": "infantry",
             "x": x, "z": z - 20.0 * step, "men": 90, "men0": 90, "hp": 1.0, "state": []}
            for i, x, z in ((1, 0.0, 300.0), (2, 150.0, 250.0), (3, 300.0, 400.0))]
        observation["enemy_roster"] = [{"id": e["id"], "type": e["type"]}
                                       for e in observation["enemy"]]
        observations.append(observation)
    return observations


def test_the_ablation_helper_allows_only_the_named_units_and_rules_and_ignores_the_job():
    """Wrong versions of the helper this must catch: one that compares only order counts (the
    foil changes f1's target, not how many orders it gives); one that skips the job check or runs
    it on the ablation only; one that passes an ablation that never differs (an unwired arm
    flag), named by units or by rules; and one that hands policies hidden observation keys."""
    observations = closing_in()
    assert assert_ablation(Nearest, lambda: Nearest({"f2"}), observations,
                           units={"f2"}) == [0, 1, 2, 3, 4, 5]
    late = {"after 3 s": lambda observation, order: observation["time_ms"] > 3000}
    assert assert_ablation(Nearest, lambda: Nearest({"f1", "f2", "f3"}, after_ms=3000),
                           observations, rules=late) == [3, 4, 5]
    with pytest.raises(AssertionError, match="outside units"):
        assert_ablation(Nearest, lambda: Nearest({"f1", "f2"}), observations, units={"f2"})
    with pytest.raises(AssertionError, match="never changed an order"):
        assert_ablation(Nearest, Nearest, observations, units={"f2"})
    with pytest.raises(AssertionError, match="never changed an order"):
        assert_ablation(Nearest, Nearest, observations, rules=late)
    with pytest.raises(AssertionError, match="the ablation's orders changed when only the job"):
        assert_ablation(Nearest, ReadsJob, observations)
    with pytest.raises(AssertionError, match="the witness's orders changed when only the job"):
        assert_ablation(ReadsJob, Nearest, observations)
