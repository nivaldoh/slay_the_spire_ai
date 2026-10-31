"""Bounded scheduler tests use the real rollout auditor with a simulated bridge."""

import copy
import hashlib
import importlib.util
import signal
import time
from contextlib import nullcontext

import combat_evidence as evidence_fixtures
import pytest
from combat_support import harness

from gameai import provenance
from gameai.provenance import REPO_ROOT
from spire.combat import rollout
from spire.combat.evidence import audit_run, normalized_observation_fingerprint
from spire.engine import doctor
from spire.engine.bridge import BridgeDisconnected
from spire.protocol import decision_from_message

SCRIPT = REPO_ROOT / "scripts/inventory_scenarios.py"
spec = importlib.util.spec_from_file_location("inventory_scenarios", SCRIPT)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
runtime_harness = harness
REAL_REFERENCE = REPO_ROOT / "runs/first-combat/baseline-heuristic-settled-20261011"


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def combat(seed):
    value = evidence_fixtures.combat_message()
    state = value["game_state"]
    state.update(gold=199, deck=[
        {"id": name, "upgrades": 0, "cost": 1 if name != "Bash" else 2}
        for name in ["Strike_R"] * 5 + ["Defend_R"] * 4 + ["Bash"]
    ], relics=[{"id": "Burning Blood"}], potions=[{"id": "Potion Slot"}] * 3)
    kind = int(seed[-2:]) % 3 if seed != "SPIREAI1" else 0
    ids = {0: ["FuzzyLouseNormal", "FuzzyLouseDefensive"],
           1: ["Cultist"], 2: ["JawWorm"]}[kind]
    original = state["combat_state"]["monsters"][0]
    state["combat_state"]["monsters"] = [{**original, "id": name} for name in ids]
    return value


def messages(seed, policy, *, won=True):
    first = combat(seed)
    terminal = copy.deepcopy(first)
    game = terminal["game_state"]
    game.pop("combat_state")
    game.update(room_phase="COMPLETE", screen_type="COMBAT_REWARD", current_hp=77)
    if policy == "end_turn" or not won:
        game.update(current_hp=0, screen_type="GAME_OVER", screen_name="DEATH",
                    screen_state={"victory": False})
    return [
        {"ready_for_command": True, "in_game": False, "available_commands": ["start"]},
        {"ready_for_command": True, "in_game": True, "available_commands": ["choose"],
         "game_state": {"screen_type": "EVENT", "choice_list": ["obtain 100 gold"],
                        "screen_state": {"event_id": "Neow Event", "options": [
                            {"choice_index": 0, "label": "obtain 100 gold", "text": "Gold"}
                        ]}}},
        {"ready_for_command": True, "in_game": True, "available_commands": ["choose"],
         "game_state": {"screen_type": "MAP", "choice_list": ["x=0"]}},
        first, terminal,
    ]


@pytest.fixture
def setup(tmp_path, monkeypatch, runtime_harness):
    runtime = runtime_harness
    runtime.before = None
    runtime.after = None
    runtime.calls = []
    revision = "a" * 40
    fingerprints = {"src/spire/policies.py": sha("policy")}
    monkeypatch.setattr(rollout, "source_fingerprints", lambda: fingerprints)
    monkeypatch.setattr(provenance.subprocess, "check_output", lambda cmd, **kwargs:
                        revision if cmd[:3] == ["git", "rev-parse", "HEAD"] else "")
    monkeypatch.setattr(doctor, "collect_diagnostics", lambda: {
        "game": {"sha256": sha("game")}, "mods": {"mod": {"sha256": sha("mod")}},
    })
    monkeypatch.setattr(inventory, "source", lambda: {
        "source_revision": revision, "source_files": fingerprints,
        "driver_sha256": sha("driver"), "research_sha256": sha("research"),
    })
    monkeypatch.setattr(inventory, "bounded_collection", lambda seconds: nullcontext())
    monkeypatch.setattr(inventory.time, "time", lambda: 100 + runtime.clock)
    public = decision_from_message(combat("SPIREAI1"), session_id="x", sequence=1).to_dict()[
        "observation"
    ]
    expected = normalized_observation_fingerprint(public)
    monkeypatch.setattr(inventory, "START_SHA256", expected)
    contract = copy.deepcopy(inventory.CONTRACT)
    contract["sentinel_start_sha256"] = expected
    monkeypatch.setattr(inventory, "CONTRACT", contract)
    reference = tmp_path / "reference"
    runtime.sessions.append(messages("SPIREAI1", "heuristic"))
    rollout.rollout(reference, {"policy": "heuristic", "game_seed": "SPIREAI1",
                               "policy_seed": 1000, "episodes": 1, "max_actions": 500,
                               "episode_timeout": 180, "bridge_timeout": 45,
                               "expected_start_sha256": expected})
    runtime.games.clear()

    def collect(directory, config):
        parent = inventory.read(directory.parents[1] / "inventory.json")
        assert parent["attempts"][-1]["status"] == "reserved"
        assert parent["attempts"][-1]["config"] == config
        assert parent["deadline_unix"] == 1900
        assert inventory.digest(directory.parents[1] / "contract.json") == parent["contract_sha256"]
        stream = messages(config["game_seed"], config["policy"])
        runtime.calls.append(copy.deepcopy(config))
        if runtime.before:
            runtime.before(directory, config, stream)
        runtime.sessions.append(stream)
        result = rollout.rollout(directory, config)
        if runtime.after:
            runtime.after(directory, config)
        return result

    monkeypatch.setattr(inventory, "rollout", collect)
    return tmp_path / "inventory", reference, runtime


def test_full_schedule_freezes_inputs_and_uses_first_two_per_family(setup):
    output, reference, runtime = setup
    report = inventory.inventory(output, reference)
    assert report["status"] == "completed" and report["admissions_valid"]
    assert len(runtime.calls) == len(report["attempts"]) == 23
    assert [call["game_seed"] for call in runtime.calls[1:13]] == list(inventory.SEEDS)
    assert [item["game_seed"] for item in report["admissions"]] == [
        "SPIREINV01", "SPIREINV04", "SPIREINV02", "SPIREINV05", "SPIREINV03", "SPIREINV06",
    ]
    assert [call["game_seed"] for call in runtime.calls if call["policy"] == "end_turn"] == [
        "SPIREINV01", "SPIREINV02", "SPIREINV03",
    ]
    assert report["unattempted"] == [] and not report["retry_used"]
    assert all(audit_run(output / record["directory"])["valid"] for record in report["attempts"])
    manifest = inventory.read(output / "runs/attempt-0000/manifest.json")
    assert manifest["purpose"] == "development"
    assert manifest["inventory_assignment"]["contract_sha256"] == report["contract_sha256"]
    with pytest.raises(FileExistsError):
        inventory.inventory(output, reference)


def test_gameplay_loss_does_not_change_selection(setup):
    output, reference, runtime = setup

    def lose(directory, config, stream):
        if config["game_seed"] == "SPIREINV01":
            stream[:] = messages(config["game_seed"], config["policy"], won=False)

    runtime.before = lose
    report = inventory.inventory(output, reference)
    assert report["admissions"][0]["game_seed"] == "SPIREINV01"
    assert report["attempts"][1]["status"] == "lost"


def test_failed_repeat_never_backfills_or_changes_later_assignments(setup):
    output, reference, runtime = setup

    def change_repeat(directory, config, stream):
        if config["game_seed"] == "SPIREINV01" and config["expected_start_sha256"]:
            stream[-1]["game_state"]["current_hp"] = 76

    runtime.before = change_repeat
    report = inventory.inventory(output, reference)
    assert "SPIREINV01" not in [a["game_seed"] for a in report["admissions"]]
    assert "SPIREINV07" not in [c["game_seed"] for c in runtime.calls[13:]]
    assert [c["game_seed"] for c in runtime.calls if c["policy"] == "end_turn"][0] == "SPIREINV04"
    assert len(report["selected"]) == 6


def test_one_immediate_infrastructure_retry_preserves_same_assignment(setup):
    output, reference, runtime = setup

    def fail_once(directory, config, stream):
        if len(runtime.calls) == 3:
            stream[:] = [BridgeDisconnected("synthetic disconnect")]

    runtime.before = fail_once
    report = inventory.inventory(output, reference)
    assert report["status"] == "completed" and len(runtime.calls) == 24
    assert report["retry_used"] and report["infrastructure_failures"] == 1
    assert runtime.calls[2] == runtime.calls[3]
    assert report["attempts"][3]["retry_of"] == 2
    assert report["attempts"][2]["status"] == "infrastructure_failure"


def test_second_infrastructure_failure_stops_without_replacement_seed(setup):
    output, reference, runtime = setup

    def fail(directory, config, stream):
        if len(runtime.calls) > 1:
            stream[:] = [BridgeDisconnected("synthetic disconnect")]

    runtime.before = fail
    report = inventory.inventory(output, reference)
    assert len(runtime.calls) == 3 and report["stop_reason"] == "second_infrastructure_failure"
    assert runtime.calls[1]["game_seed"] == runtime.calls[2]["game_seed"] == "SPIREINV01"
    assert "discovery-SPIREINV02" in report["unattempted"]


def test_remaining_budget_clips_episode_and_bridge_then_stops(setup):
    output, reference, runtime = setup

    def advance(directory, config):
        runtime.clock = 1790 if len(runtime.calls) == 1 else 1801

    runtime.after = advance
    report = inventory.inventory(output, reference)
    assert len(runtime.calls) == 2
    assert runtime.calls[-1]["episode_timeout"] == runtime.calls[-1]["bridge_timeout"] == 10
    assert report["stop_reason"] == "deadline" and report["post_deadline_seconds"] == 1
    assert not report["admissions_valid"]


def test_deadline_inside_collection_preserves_attempt_and_never_retries(setup):
    output, reference, runtime = setup

    def expire(directory, config, stream):
        stream[-1] = inventory.InventoryDeadline()
        runtime.clock = 1800

    runtime.before = expire
    report = inventory.inventory(output, reference)
    assert report["stop_reason"] == "deadline"
    assert len(runtime.calls) == 1 and not report["retry_used"]
    assert report["attempts"][0]["status"] == "deadline"
    assert (output / "runs/attempt-0000/episode-0000/result.json").exists()


def test_keyboard_interrupt_preserves_reservation_and_forbids_resume(setup):
    output, reference, runtime = setup
    runtime.before = lambda directory, config, stream: stream.__setitem__(-1, KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        inventory.inventory(output, reference)
    report = inventory.read(output / "inventory.json")
    assert report["status"] == "interrupted" and not report["admissions_valid"]
    assert report["attempts"][0]["status"] == "interrupted"
    assert report["assignments"][0]["status"] == "incomplete"


@pytest.mark.parametrize("when", [1, 23])
def test_sentinel_mismatch_invalidates_inventory(setup, when):
    output, reference, runtime = setup

    def mutate(directory, config, stream):
        if len(runtime.calls) == when:
            stream[-1]["game_state"]["current_hp"] = 75

    runtime.before = mutate
    report = inventory.inventory(output, reference)
    assert report["stop_reason"] == "sentinel_mismatch"
    assert len(runtime.calls) == when and not report["admissions_valid"]


def test_changed_prior_evidence_stops_before_next_game(setup):
    output, reference, runtime = setup

    def change(directory, config):
        if len(runtime.calls) == 2:
            (output / "runs/attempt-0000/episode-0000/combat_start.json").write_text("{}")

    runtime.after = change
    with pytest.raises(ValueError, match="Earlier inventory evidence changed"):
        inventory.inventory(output, reference)
    assert len(runtime.calls) == 2
    assert not inventory.read(output / "inventory.json")["admissions_valid"]


def test_wrong_repeat_start_is_rejected_without_retry_or_backfill(setup):
    output, reference, runtime = setup

    def wrong_start(directory, config, stream):
        if config["game_seed"] == "SPIREINV01" and config["expected_start_sha256"]:
            stream[-2]["game_state"]["current_hp"] = 79

    runtime.before = wrong_start
    report = inventory.inventory(output, reference)
    repeat = next(item for item in report["assignments"] if item["id"] == "repeat-cultist-0")
    assert repeat["status"] == "rejected" and len(repeat["attempts"]) == 1
    attempted = report["attempts"][repeat["attempts"][0]]
    assert attempted["status"] == "unsupported"
    assert attempted["audit"]["reported_error"] == "Combat start differs from the frozen suite"
    assert not report["retry_used"]
    assert "SPIREINV07" not in [c["game_seed"] for c in runtime.calls[13:]]


def test_changed_source_stops_before_next_collector(setup, monkeypatch):
    output, reference, runtime = setup
    original = inventory.source

    def changed(directory, config):
        monkeypatch.setattr(
            inventory, "source", lambda: {**original(), "driver_sha256": sha("new")}
        )

    runtime.after = changed
    with pytest.raises(ValueError, match="Frozen inventory source"):
        inventory.inventory(output, reference)
    assert len(runtime.calls) == 1


def test_absolute_alarm_interrupts_blocking_collection_and_restores_handler():
    previous = signal.getsignal(signal.SIGALRM)
    with pytest.raises(inventory.InventoryDeadline), inventory.bounded_collection(0.02):
        time.sleep(1)
    assert signal.getsignal(signal.SIGALRM) == previous
    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0


def test_real_engine_v1_reference_is_eligible_and_equivalence_accepts_it():
    if not REAL_REFERENCE.exists():
        pytest.skip("Local original-engine evidence is not shipped in Git")
    reference, episode = inventory.load_reference(REAL_REFERENCE)
    assert reference["public_episode"]["combat_start_sha256"] == inventory.START_SHA256
    # This is an acceptance control. Independent repeat trajectories are checked in
    # test_inventory_engine_regressions.py, rather than by comparing a run to itself.
    assert inventory.equivalent(episode, episode)
    assert inventory.eligibility(episode, inventory.start_context(REAL_REFERENCE))["eligible"]


@pytest.mark.parametrize("change", ["hp", "gold", "deck", "relic", "potion", "prefix", "room"])
def test_public_eligibility_rejects_noncanonical_conditions(setup, change):
    _, reference, _ = setup
    _, episode = inventory.load_reference(reference)
    episode = copy.deepcopy(episode)
    public = episode["transitions"][0]["observation"]
    context = inventory.start_context(reference)
    if change == "hp":
        public["max_hp"] = 88
    elif change == "gold":
        public["gold"] = 99
    elif change == "deck":
        public["deck"][0]["upgrades"] = 1
    elif change == "relic":
        public["relics"].append({"id": "Other"})
    elif change == "potion":
        public["potions"][0]["id"] = "Fire Potion"
    elif change == "prefix":
        episode["prefix"][1]["choice"] = "gain max hp"
    else:
        context["room_type"] = "MonsterRoomElite"
    assert not inventory.eligibility(episode, context)["eligible"]
