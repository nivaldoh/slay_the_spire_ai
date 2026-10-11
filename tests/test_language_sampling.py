"""Seeded candidate sampling is reproducible from recorded draws and public prompts."""

import json
import math

import pytest
import test_evidence

from spire import language_sampling as sampling
from spire.evidence import audit_run
from spire.protocol import Action, Decision

run = test_evidence.run


def log(values):
    return [math.log(value) for value in values]


@pytest.mark.parametrize(
    ("draw", "index"), [(0.0, 0), (0.199, 0), (0.2, 1), (0.699, 1), (0.7, 2), (0.999, 2)]
)
def test_inverse_cdf_follows_candidate_order(draw, index):
    assert sampling.sample_index(log([0.2, 0.5, 0.3]), draw) == index


@pytest.mark.parametrize("draw", [-0.1, 1.0])
def test_draw_must_be_unit_interval(draw):
    with pytest.raises(ValueError):
        sampling.sample_index(log([1.0]), draw)


def test_temperature_normalizes_and_flattens_scores():
    cold = sampling.normalized([-1.0, -3.0], 1.0)
    hot = sampling.normalized([-1.0, -3.0], 2.0)
    for values in (cold, hot):
        assert math.isclose(sum(math.exp(value) for value in values), 1.0)
    assert math.exp(hot[0]) < math.exp(cold[0])


def first_decision(directory):
    event = next(e for e in test_evidence.events(directory) if e["kind"] == "decision")
    item = event["decision"]
    decision = Decision(
        item["id"], item["observation"], tuple(Action(**a) for a in item["candidates"])
    )
    return event, decision


def sampled_run(run, scores):
    """Rewrite the fixture's recorded choice as a seeded sampled language decision."""
    directory = run / "episode-0000"
    event, decision = first_decision(directory)
    sampler = sampling.CandidateSampler(
        lambda _: (scores, 700), seed=11, temperature=1.0, model_sha256="b" * 64
    )
    chosen = sampler.choose(decision)
    assert chosen.id == event["selected_action_id"], "fixture scores must select the recording"
    trace = test_evidence.events(directory)
    for item in trace:
        if item["kind"] == "decision":
            item["behavior"] = sampler.choice_metadata(decision.id)
    test_evidence.write_events(directory, trace)
    manifest = json.loads((run / "manifest.json").read_text())
    manifest["config"]["policy"] = "language_sample"
    (run / "manifest.json").write_text(json.dumps(manifest))
    test_evidence.set_result(run, policy="language_sample")
    return directory


def recorded_scores(run):
    _, decision = first_decision(run / "episode-0000")
    event = next(e for e in test_evidence.events(run / "episode-0000") if e["kind"] == "decision")
    index = [c.id for c in decision.candidates].index(event["selected_action_id"])
    return [0.0 if i == index else -50.0 for i in range(len(decision.candidates))]


def test_sampled_language_decisions_audit_from_recorded_draws(run):
    sampled_run(run, recorded_scores(run))
    assert audit_run(run)["valid"]


@pytest.mark.parametrize(
    "damage", ["draw", "unnormalized", "index", "prompt", "missing", "temperature"]
)
def test_tampered_sampling_evidence_is_rejected(run, damage):
    directory = sampled_run(run, recorded_scores(run))
    trace = test_evidence.events(directory)
    behavior = next(e for e in trace if e["kind"] == "decision")["behavior"]
    if damage == "draw":
        # Move the draw past all mass on the recorded choice.
        behavior["candidate_log_probs"] = sampling.normalized(
            [0.0] * len(behavior["candidate_log_probs"]), 1.0
        )
        behavior["draw"] = 0.999999 if behavior["selected_index"] == 0 else 0.0
    elif damage == "unnormalized":
        behavior["candidate_log_probs"] = [value - 1.0 for value in behavior["candidate_log_probs"]]
    elif damage == "index":
        behavior["selected_index"] += 1
    elif damage == "prompt":
        behavior["prompt_sha256"] = "0" * 64
    elif damage == "missing":
        del behavior["draw"]
    else:
        behavior["temperature"] = 0
    test_evidence.write_events(directory, trace)
    assert not audit_run(run)["valid"]


def test_sampler_seed_reproduces_draws_and_rejects_mismatched_scores(run):
    _, decision = first_decision(run / "episode-0000")
    width = len(decision.candidates)
    choices = []
    for _ in range(2):
        sampler = sampling.CandidateSampler(
            lambda _: ([0.0] * width, 700), seed=5, temperature=1.0, model_sha256="c" * 64
        )
        sampler.choose(decision)
        choices.append(sampler.choice_metadata(decision.id))
    assert choices[0]["draw"] == choices[1]["draw"]
    broken = sampling.CandidateSampler(
        lambda _: ([0.0] * (width + 1), 700), seed=5, temperature=1.0, model_sha256="c" * 64
    )
    with pytest.raises(Exception, match="Candidate scores differ"):
        broken.choose(decision)
