"""Demonstration exports use public actions and whole-origin split boundaries."""

import copy
import hashlib
import json
import shutil
import subprocess

import pytest
import test_evidence

from spire.combat.evidence import EvidenceError, audit_run, normalized_observation_fingerprint
from spire.language import demonstrations as demos
from spire.protocol import Decision, decision_from_message
from spire.provenance import REPO_ROOT

evidence_run = test_evidence.run


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value) + "\n")


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.fixture
def run(evidence_run):
    root = REPO_ROOT
    manifest = read(evidence_run / "manifest.json")
    manifest.update(
        source_revision=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        source_status="",
        source_files={
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("src/spire/policies.py", "src/spire/protocol.py")
        },
    )
    manifest["config"]["policy"] = "heuristic"
    write(evidence_run / "manifest.json", manifest)
    test_evidence.set_result(evidence_run, policy="heuristic")
    assert audit_run(evidence_run)["valid"]
    return evidence_run


def source(run, split="train", role="heuristic", information="public"):
    return demos.DemonstrationSource(run, split, role, information)


def renamed_copy(run, destination, *, seed="ABC", hp=80):
    shutil.copytree(run, destination)
    for path in destination.rglob("*.json*"):
        path.write_text(path.read_text().replace("session-0", f"session-{destination.name}"))
    manifest = read(destination / "manifest.json")
    manifest["config"]["game_seed"] = seed
    write(destination / "manifest.json", manifest)
    test_evidence.set_result(destination, seed=seed, starting_hp=hp)
    episode = destination / "episode-0000"
    events = test_evidence.events(episode)
    events[2]["command"] = f"START IRONCLAD 0 {seed}"
    raw = events[3]["raw"]
    raw["game_state"]["current_hp"] = hp
    raw["game_state"]["combat_state"]["player"]["current_hp"] = hp
    result = read(episode / "result.json")
    decision = decision_from_message(raw, session_id=result["session_id"], sequence=2).to_dict()
    events[5]["decision"] = decision
    result["combat_start_sha256"] = normalized_observation_fingerprint(decision["observation"])
    events[-1]["result"] = result
    test_evidence.write_events(episode, events)
    write(episode / "result.json", result)
    write(episode / "combat_start.json", decision["observation"])
    manifest = read(destination / "manifest.json")
    manifest["episodes"] = [result]
    write(destination / "manifest.json", manifest)
    assert audit_run(destination)["valid"]
    return destination


def test_public_rendering_is_lossless_and_preserves_duplicate_card_and_target_slots():
    raw = test_evidence.combat_message()
    combat = raw["game_state"]["combat_state"]
    combat["hand"] *= 2
    combat["monsters"] *= 2
    combat["draw_pile"] = copy.deepcopy(combat["hand"])
    decision = decision_from_message(raw, session_id="private-session", sequence=9)
    compact = demos.public_input(decision)
    assert compact["choices"] == [
        ["play", 0, 0],
        ["play", 0, 1],
        ["play", 1, 0],
        ["play", 1, 1],
        ["end", None, None],
    ]
    assert compact["observation"]["combat_state"]["hand"] == [0, 0]
    restored = copy.deepcopy(compact["observation"])
    for owner, pile in [
        (restored, "deck"),
        *(
            (restored["combat_state"], name)
            for name in ("hand", "draw_pile", "discard_pile", "exhaust_pile")
        ),
    ]:
        owner[pile] = [compact["cards"][index] for index in owner[pile]]
    assert restored == decision.to_dict()["observation"]
    prompt = demos.render_prompt(decision)
    assert "private-session" not in prompt and "private-card-id" not in prompt
    assert "move_id" not in prompt and '"seed"' not in prompt
    second = decision_from_message(raw, session_id="another-session", sequence=31)
    assert demos.render_prompt(second) == prompt


def test_export_keeps_provenance_outside_model_text_and_hashes_all_outputs(tmp_path, run):
    output = tmp_path / "dataset"
    result = demos.export_demonstrations(output, [source(run)], purpose="smoke")
    assert result["rows"] == {"train": 1, "validation": 0, "test": 0}
    (example,) = lines(output / "train.jsonl")
    (origin,) = lines(output / "origins.jsonl")
    assert set(example) == {"prompt", "completion"}
    assert example["completion"] == '{"a":0}'
    assert all(
        value not in example["prompt"]
        for value in (
            "session-0",
            "ABC",
            "scenario_id",
            "trace_sha256",
            "private-card-id",
            "move_id",
        )
    )
    assert origin["session_id"] == "session-0"
    assert origin["selected_action"]["command"] == "play 1 0"
    assert origin["outcome"] == "won"
    for name, expected in result["files"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
    assert result["sources"][0]["teacher_information"] == "verified_public_builtin"


def test_duplicate_examples_remain_with_all_origin_records(tmp_path, run):
    other = renamed_copy(run, tmp_path / "other")
    output = tmp_path / "dataset"
    manifest = demos.export_demonstrations(output, [source(run), source(other)], purpose="smoke")
    assert manifest["rows"]["train"] == 2
    assert manifest["unique_examples"] == manifest["duplicate_rows"] == 1
    origins = lines(output / "origins.jsonl")
    assert origins[0]["example_sha256"] == origins[1]["example_sha256"]
    assert origins[0]["session_id"] != origins[1]["session_id"]
    assert origins[0]["origin_run_sha256"] != origins[1]["origin_run_sha256"]


@pytest.mark.parametrize(
    "seed,hp,expected",
    [
        ("ABC", 79, "scenario_seed_family"),
        ("DEF", 80, "public_start_family"),
    ],
)
def test_split_leakage_rejected_even_after_run_and_session_are_renamed(
    tmp_path, run, seed, hp, expected
):
    other = renamed_copy(run, tmp_path / "other", seed=seed, hp=hp)
    output = tmp_path / "dataset"
    with pytest.raises(EvidenceError, match=f"Cross-split {expected} leakage"):
        demos.export_demonstrations(
            output, [source(run), source(other, "validation")], purpose="supervised_finetuning"
        )
    assert not output.exists()


def test_distinct_environment_seeds_and_starts_can_share_encounter_type_across_splits(
    tmp_path, run
):
    other = renamed_copy(run, tmp_path / "other", seed="DEF", hp=79)
    result = demos.export_demonstrations(
        tmp_path / "dataset",
        [source(run), source(other, "validation")],
        purpose="supervised_finetuning",
    )
    assert result["rows"] == {"train": 1, "validation": 1, "test": 0}
    assert result["scenario_seed_families"] == result["public_start_families"] == 2


@pytest.mark.parametrize("damage", ["hash", "privileged", "role", "action", "purpose"])
def test_unverified_teacher_claims_are_rejected_before_writing(tmp_path, run, damage):
    declaration = source(run)
    manifest = read(run / "manifest.json")
    if damage == "hash":
        manifest["source_files"]["src/spire/policies.py"] = "0" * 64
    elif damage == "privileged":
        declaration = source(run, information="privileged")
    elif damage == "role":
        declaration = source(run, role="search_oracle")
    elif damage == "action":
        # This is a legal, terminal-linked choice, but not this known heuristic's choice.
        events = test_evidence.events(run / "episode-0000")
        selected = events[5]["decision"]["candidates"][-1]
        events[5]["selected_action_id"] = selected["id"]
        events[6].update(action_id=selected["id"], command=selected["command"])
        events[7]["previous_action_id"] = selected["id"]
        events[8]["action_id"] = selected["id"]
        test_evidence.write_events(run / "episode-0000", events)
    else:
        manifest["purpose"] = "final_test"
    write(run / "manifest.json", manifest)
    output = tmp_path / "dataset"
    with pytest.raises(EvidenceError):
        demos.export_demonstrations(output, [declaration], purpose="smoke")
    assert not output.exists()


def test_unknown_teacher_code_rejected_even_when_manifest_hash_is_updated(
    tmp_path, run, monkeypatch
):
    original = demos._source_bytes
    altered = original(read(run / "manifest.json")["source_revision"], "src/spire/policies.py")
    altered += b"\nprivate_game_seed = 123\n"
    manifest = read(run / "manifest.json")
    manifest["source_files"]["src/spire/policies.py"] = hashlib.sha256(altered).hexdigest()
    write(run / "manifest.json", manifest)
    monkeypatch.setattr(
        demos,
        "_source_bytes",
        lambda revision, filename: (
            altered if filename.endswith("policies.py") else original(revision, filename)
        ),
    )
    with pytest.raises(EvidenceError, match="Unknown public teacher implementation"):
        demos.export_demonstrations(tmp_path / "dataset", [source(run)], purpose="smoke")


@pytest.mark.parametrize("status", ["interrupted", "stopped"])
def test_incomplete_origins_cannot_be_partially_exported(tmp_path, run, status):
    manifest = read(run / "manifest.json")
    manifest["status"] = status
    write(run / "manifest.json", manifest)
    assert audit_run(run)["valid"]
    with pytest.raises(EvidenceError, match="Only complete originating runs"):
        demos.export_demonstrations(tmp_path / "dataset", [source(run)], purpose="smoke")


def evaluation_source(run, purpose="development"):
    manifest = read(run / "manifest.json")
    manifest["config"]["expected_start_sha256"] = manifest["episodes"][0]["combat_start_sha256"]
    write(run / "manifest.json", manifest)
    suite = {
        "schema_version": 1,
        "id": "fixture",
        "purpose": purpose,
        **{
            key: manifest["config"][key]
            for key in ("game_seed", "policy_seed", "episodes", "expected_start_sha256")
        },
    }
    write(run / "suite.json", suite)
    record = {
        "schema_version": 1,
        "valid": True,
        "suite": suite,
        "suite_sha256": hashlib.sha256((run / "suite.json").read_bytes()).hexdigest(),
        "policy_artifact": {
            "type": "builtin",
            "name": "heuristic",
            "source_revision": manifest["source_revision"],
            "policy_source_sha256": manifest["source_files"]["src/spire/policies.py"],
        },
    }
    write(run / "evaluation.json", record)
    return record


def test_development_evaluation_reuse_is_declared_but_final_evaluation_cannot_train(tmp_path, run):
    evaluation_source(run)
    result = demos.export_demonstrations(tmp_path / "development", [source(run)], purpose="smoke")
    assert result["sources"][0]["development_reuse"] is True
    assert result["sources"][0]["original_purpose"] == "development"
    assert result["development_reuse"] is True
    assert result["research_scope"] == "diagnostic_development"
    assert list((tmp_path / "development" / "source_suites").glob("*.json"))
    evaluation_source(run, "final_test")
    with pytest.raises(EvidenceError, match="Held-out evaluation origins"):
        demos.export_demonstrations(tmp_path / "rejected", [source(run)], purpose="smoke")


@pytest.mark.parametrize("key", ["game_seed", "policy_seed", "episodes", "expected_start_sha256"])
def test_mismatched_evaluation_declaration_rejected(tmp_path, run, key):
    record = evaluation_source(run)
    record["suite"][key] = "different" if type(record["suite"][key]) is str else 99
    write(run / "evaluation.json", record)
    with pytest.raises(EvidenceError, match=f"Evaluation suite {key} differs"):
        demos.export_demonstrations(tmp_path / "dataset", [source(run)], purpose="smoke")


@pytest.mark.parametrize("damage", ["missing", "changed", "hash", "artifact", "actual_start"])
def test_evaluation_requires_preserved_suite_and_teacher_identity(tmp_path, run, damage):
    record = evaluation_source(run)
    if damage == "missing":
        (run / "suite.json").unlink()
    elif damage == "changed":
        (run / "suite.json").write_text("{}")
    elif damage == "hash":
        record["suite_sha256"] = "0" * 64
    elif damage == "artifact":
        record["policy_artifact"]["name"] = "oracle"
    else:
        record["suite"]["expected_start_sha256"] = "0" * 64
        manifest = read(run / "manifest.json")
        manifest["config"]["expected_start_sha256"] = "0" * 64
        write(run / "manifest.json", manifest)
    write(run / "evaluation.json", record)
    with pytest.raises(EvidenceError):
        demos.export_demonstrations(tmp_path / "dataset", [source(run)], purpose="smoke")


def test_duplicate_origin_cannot_be_counted_twice(tmp_path, run):
    with pytest.raises(EvidenceError, match="Duplicate originating run"):
        demos.export_demonstrations(
            tmp_path / "dataset", [source(run), source(run)], purpose="smoke"
        )


def test_source_changed_during_export_is_rejected(tmp_path, run, monkeypatch):
    original = demos.render_prompt

    def mutate(decision):
        (run / "environment.json").write_text('{"changed":true}')
        return original(decision)

    monkeypatch.setattr(demos, "render_prompt", mutate)
    with pytest.raises(EvidenceError, match="Source evidence changed"):
        demos.export_demonstrations(tmp_path / "dataset", [source(run)], purpose="smoke")
    assert not (tmp_path / "dataset").exists()


def test_random_teacher_is_replayed_with_recorded_episode_seed(tmp_path, run):
    manifest = read(run / "manifest.json")
    manifest["config"].update(policy="random", policy_seed=1)
    write(run / "manifest.json", manifest)
    test_evidence.set_result(run, policy="random", policy_seed=1)
    result = demos.export_demonstrations(
        tmp_path / "dataset", [source(run, role="random")], purpose="smoke"
    )
    assert result["rows"]["train"] == 1


def test_formatter_rejects_extra_hidden_fields_even_in_handmade_decision():
    original = decision_from_message(test_evidence.combat_message(), session_id="x", sequence=1)
    observation = original.to_dict()["observation"]
    observation["seed"] = "PRIVATE"
    forged = Decision(original.id, observation, original.candidates)
    with pytest.raises(EvidenceError, match="Unrecognized public observation"):
        demos.render_prompt(forged)


@pytest.mark.parametrize(
    "text",
    [
        '{"a":true}',
        '{"a":0.0}',
        '{"a":-1}',
        '{"a":100}',
        '{"a":"0"}',
        '{"a":0,"reason":"x"}',
        '{"a":0,"a":1}',
        "[0]",
        "{}",
        'action: {"a":0}',
        '```json\n{"a":0}\n```',
        '{"a":0}{"a":1}',
    ],
)
def test_completion_parser_rejects_repairable_or_ambiguous_answers(text):
    from spire.protocol import IllegalActionError

    decision = decision_from_message(test_evidence.combat_message(), session_id="x", sequence=1)
    with pytest.raises(IllegalActionError):
        demos.parse_completion(decision, text)


def test_parser_returns_exact_bound_candidate_and_stale_send_is_still_rejected():
    from spire.protocol import StaleActionError, validate_action

    raw = test_evidence.combat_message()
    old = decision_from_message(raw, session_id="x", sequence=1)
    current = decision_from_message(raw, session_id="x", sequence=2)
    action = demos.parse_completion(old, ' {"a":0}\n')
    assert action is old.candidates[0]
    with pytest.raises(StaleActionError):
        validate_action(current, action)


def test_deleted_evaluation_record_cannot_be_reclassified_as_plain_rollout(tmp_path, run):
    evaluation_source(run)
    manifest = read(run / "manifest.json")
    manifest["command"] = ["python", "-m", "spire", "evaluate"]
    write(run / "manifest.json", manifest)
    (run / "evaluation.json").unlink()
    with pytest.raises(EvidenceError, match="Originating evaluation record is missing"):
        demos.export_demonstrations(tmp_path / "dataset", [source(run)], purpose="smoke")


@pytest.mark.parametrize("where", ["record", "suite"])
def test_boolean_is_not_evaluation_schema_version(tmp_path, run, where):
    record = evaluation_source(run)
    (record if where == "record" else record["suite"])["schema_version"] = True
    write(run / "evaluation.json", record)
    with pytest.raises(EvidenceError, match="Unsupported evaluation .* schema"):
        demos.export_demonstrations(tmp_path / "dataset", [source(run)], purpose="smoke")


POLICY_FAILURE_DECLARATION = b'''
class PolicyFailure(ProtocolError):
    """A policy output/context failure before any command was selected."""

    def __init__(self, message: str, *, failure: dict):
        super().__init__(message)
        self.failure = failure
'''


@pytest.mark.parametrize("damage", [None, "implementation", "other_code", "duplicate"])
def test_only_exact_independent_policy_failure_class_is_compatible(
    tmp_path, run, monkeypatch, damage
):
    original = demos._source_bytes
    manifest = read(run / "manifest.json")
    saved = original(manifest["source_revision"], "src/spire/protocol.py")
    # This fixture also works after the new exception is integrated in protocol.py.
    saved = saved.replace(POLICY_FAILURE_DECLARATION, b"")
    addition = POLICY_FAILURE_DECLARATION
    if damage == "implementation":
        addition = addition.replace(b"self.failure = failure", b"self.failure = {}")
    elif damage == "other_code":
        addition += b"\nprivate_game_seed = 123\n"
    elif damage == "duplicate":
        addition *= 2
    saved += addition
    manifest["source_files"]["src/spire/protocol.py"] = hashlib.sha256(saved).hexdigest()
    write(run / "manifest.json", manifest)
    monkeypatch.setattr(
        demos,
        "_source_bytes",
        lambda revision, filename: (
            saved if filename.endswith("protocol.py") else original(revision, filename)
        ),
    )
    if damage is None:
        result = demos.export_demonstrations(tmp_path / "dataset", [source(run)], purpose="smoke")
        assert result["rows"]["train"] == 1
    else:
        with pytest.raises(EvidenceError, match="Unknown"):
            demos.export_demonstrations(tmp_path / "dataset", [source(run)], purpose="smoke")


def policy_failure_after_action(run):
    """Keep one acknowledged public action before an invalid model completion."""
    test_evidence.make_policy_failure(run, after_action=True)


@pytest.mark.parametrize("after_action", [False, True])
def test_policy_failure_origins_never_become_demonstrations(tmp_path, run, after_action):
    from spire.combat.evidence import load_transitions

    if after_action:
        policy_failure_after_action(run)
    else:
        test_evidence.make_policy_failure(run)
    assert audit_run(run)["valid"]
    assert len(load_transitions(run)) == int(after_action)
    with pytest.raises(EvidenceError, match="Only complete originating runs"):
        demos.export_demonstrations(tmp_path / "dataset", [source(run)], purpose="smoke")


def non_heuristic_behavior(run):
    """Record a legal random-policy choice that differs from the heuristic's choice."""
    manifest = read(run / "manifest.json")
    manifest["config"].update(policy="random", policy_seed=7)
    write(run / "manifest.json", manifest)
    test_evidence.set_result(run, policy="random", policy_seed=7)
    events = test_evidence.events(run / "episode-0000")
    selected = events[5]["decision"]["candidates"][-1]
    events[5]["selected_action_id"] = selected["id"]
    events[6].update(action_id=selected["id"], command=selected["command"])
    events[7]["previous_action_id"] = selected["id"]
    events[8]["action_id"] = selected["id"]
    test_evidence.write_events(run / "episode-0000", events)
    assert audit_run(run)["valid"]
    return selected


def test_relabel_uses_public_heuristic_label_and_keeps_behavior_in_metadata(tmp_path, run):
    behavior = non_heuristic_behavior(run)
    result = demos.export_demonstrations(
        tmp_path / "dataset", [source(run, role=demos.RELABEL)], purpose="supervised_finetuning"
    )
    assert result["sources"][0]["teacher_information"] == "public_builtin_relabel"
    assert result["sources"][0]["behavior_policy"] == "random"
    assert lines(tmp_path / "dataset" / "train.jsonl")[0]["completion"] == '{"a":0}'
    origin = lines(tmp_path / "dataset" / "origins.jsonl")[0]
    assert origin["behavior_policy"] == "random"
    assert origin["behavior_action"]["id"] == behavior["id"] != origin["selected_action"]["id"]
    snapshots = {path.read_bytes() for path in (tmp_path / "dataset/teacher_sources").iterdir()}
    root = REPO_ROOT
    assert (root / "src/spire/policies.py").read_bytes() in snapshots


@pytest.mark.parametrize(
    "status",
    [
        " M src/spire/rollout.py\n",
        "?? scripts/new.py\n",
        " M uv.lock\n",
        "R  docs/a.md -> src/spire/protocol.py\n",
        '?? "src/spire/a b.py"\n',
        None,
    ],
)
def test_relabel_requires_committed_implementation(tmp_path, run, status):
    manifest = read(run / "manifest.json")
    manifest["source_status"] = status
    write(run / "manifest.json", manifest)
    with pytest.raises(EvidenceError, match="source status|committed implementation"):
        demos.export_demonstrations(
            tmp_path / "dataset", [source(run, role=demos.RELABEL)], purpose="smoke"
        )


def test_relabel_allows_documentation_only_changes(tmp_path, run):
    manifest = read(run / "manifest.json")
    manifest["source_status"] = " M docs/state.md\n?? docs/results/new.json\n"
    write(run / "manifest.json", manifest)
    result = demos.export_demonstrations(
        tmp_path / "dataset", [source(run, role=demos.RELABEL)], purpose="smoke"
    )
    assert result["rows"]["train"] == 1


def test_relabel_rejects_unknown_observation_code(tmp_path, run, monkeypatch):
    original = demos._source_bytes
    altered = original(read(run / "manifest.json")["source_revision"], "src/spire/protocol.py")
    altered += b"\nPRIVATE_DRAW_ORDER = True\n"
    manifest = read(run / "manifest.json")
    manifest["source_files"]["src/spire/protocol.py"] = hashlib.sha256(altered).hexdigest()
    write(run / "manifest.json", manifest)
    monkeypatch.setattr(
        demos,
        "_source_bytes",
        lambda revision, filename: (
            altered if filename.endswith("protocol.py") else original(revision, filename)
        ),
    )
    with pytest.raises(EvidenceError, match="Unknown public observation implementation"):
        demos.export_demonstrations(
            tmp_path / "dataset", [source(run, role=demos.RELABEL)], purpose="smoke"
        )


def test_offline_evaluation_exports_only_a_test_split(tmp_path, run):
    with pytest.raises(EvidenceError, match="one test split"):
        demos.export_demonstrations(
            tmp_path / "train", [source(run, role=demos.RELABEL)], purpose="offline_evaluation"
        )
    result = demos.export_demonstrations(
        tmp_path / "test",
        [source(run, split="test", role=demos.RELABEL)],
        purpose="offline_evaluation",
    )
    assert result["rows"] == {"train": 0, "validation": 0, "test": 1}
