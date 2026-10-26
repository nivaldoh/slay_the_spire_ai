"""Checkpoint RL, model side (checkpoint-rl-plan.md, stage 3): the first method against hand
calculations, the method-agnostic tests on a CPU toy model with the mapping control, tasks,
label transforms, evaluation metrics, comparison, the GPU lease and recount.

The numerical tests need the llm extra (torch, transformers, peft) and skip without it.
"""
import json
import math
import subprocess
import sys
import time

import pytest

from gameai.provenance import REPO_ROOT
from twwarhammer3.battle import candidates as cand
from twwarhammer3.battle import rl

CYCLES = ([1, 2, 0], [1, 2, 3, 4, 0])


def toy_task(token: int, rewards: list[int], split="train") -> dict:
    listed = [{"id": f"c{i}", "orders": [], "description": f"choice {i}"}
              for i in range(len(rewards))]
    return rl.make_task({"token": token}, listed, rewards, split, {"root": f"r{token}"}, 0)


class ToyScorer(rl.CandidateScorer):
    """The prompt is one context token; displayed slot k's completion is the token of the
    canonical candidate p[k] (written out here, not through slot_to_candidate) then EOS. Its
    distribution over candidates is the same under every permutation."""

    def __init__(self, model):
        super().__init__(model, None, temperature=1.0, token_cap=10)

    def encode(self, task, permutation):
        return ([task["context"]["token"]], [[10 + permutation[k], 31]
                                              for k in range(len(permutation))], "")


def true_probs(scorer, task, permutation):
    """Candidate probabilities read with the literal p[k] mapping."""
    import torch

    with torch.no_grad():
        slots = scorer.slot_log_probs(task, permutation).exp().tolist()
    return [slots[permutation.index(c)] for c in range(len(permutation))]


@pytest.fixture
def toy():
    torch = pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")
    peft = pytest.importorskip("peft")

    def make(lr=5e-2, sgd=False):
        torch.manual_seed(0)
        # The Spire RL toy's shape. Its default 0.02 initialisation caps the logit spread at
        # about 0.6 (RMSNorm bounds the hidden state, the tied embeddings are frozen), so no
        # adapter could fit a choice: 0.5 leaves room.
        config = transformers.Qwen3Config(vocab_size=32, hidden_size=16, intermediate_size=32,
                                          num_hidden_layers=1, num_attention_heads=2,
                                          num_key_value_heads=1, head_dim=8,
                                          initializer_range=0.5)
        model = peft.get_peft_model(transformers.Qwen3ForCausalLM(config), peft.LoraConfig(
            r=2, lora_alpha=4, target_modules=["q_proj", "v_proj"], init_lora_weights=False))
        model.eval()
        trainable = [p for p in model.parameters() if p.requires_grad]
        optimizer = (torch.optim.SGD(trainable, lr=lr) if sgd
                     else torch.optim.AdamW(trainable, lr=lr, weight_decay=0.0))
        return ToyScorer(model), optimizer
    return make


def steps(method, scorer, optimizer, tasks, permutation, count):
    records = []
    for _ in range(count):
        records.append(method(scorer, optimizer, tasks,
                              {t["hash"]: [permutation] for t in tasks}, {}))
    return records


def mapping_mutant(monkeypatch):
    monkeypatch.setattr(rl, "slot_to_candidate", lambda p, k: p.index(k))


@pytest.mark.parametrize("name", sorted(rl.METHODS))
@pytest.mark.parametrize("cycle", CYCLES)
def test_direction_a_reward_raises_its_candidate_and_reversed_rewards_lower_it(toy, name, cycle):
    method, n = rl.METHODS[name], len(cycle)
    rewarded = toy_task(3, [1] + [0] * (n - 1))
    reversed_ = toy_task(3, [0] + [1] * (n - 1))
    for task, sign in ((rewarded, 1), (reversed_, -1)):
        scorer, optimizer = toy(lr=1e-2, sgd=True)
        before = true_probs(scorer, task, cycle)[0]
        steps(method, scorer, optimizer, [task], cycle, 1)
        assert sign * (true_probs(scorer, task, cycle)[0] - before) > 0


@pytest.mark.parametrize("name", sorted(rl.METHODS))
def test_no_signal_changes_neither_the_adapter_nor_the_optimizer(toy, name):
    import torch

    method = rl.METHODS[name]
    scorer, optimizer = toy()
    steps(method, scorer, optimizer, [toy_task(3, [1, 0, 0])], CYCLES[0], 1)
    adapter = rl.tensor_hash(scorer.adapter_state())
    moments = {i: {k: v.clone() for k, v in s.items() if torch.is_tensor(v)}
               for i, s in optimizer.state.items()}
    record = steps(method, scorer, optimizer, [toy_task(3, [1, 1, 1])], CYCLES[0], 1)[0]
    assert record["updated"] is False and record["adapter_after"] == adapter
    assert rl.tensor_hash(scorer.adapter_state()) == adapter
    for i, s in optimizer.state.items():
        assert all(torch.equal(moments[i][k], v) for k, v in s.items() if torch.is_tensor(v))


@pytest.mark.parametrize("name", sorted(rl.METHODS))
@pytest.mark.parametrize("cycle", CYCLES)
def test_overfit_one_task_reaches_095_within_200_steps(toy, name, cycle):
    method, n = rl.METHODS[name], len(cycle)
    task = toy_task(3, [0] * (n - 1) + [1])
    scorer, optimizer = toy()
    for _ in range(200):
        steps(method, scorer, optimizer, [task], cycle, 1)
        if true_probs(scorer, task, cycle)[-1] >= 0.95:
            break
    assert true_probs(scorer, task, cycle)[-1] >= 0.95


@pytest.mark.parametrize("name", sorted(rl.METHODS))
def test_first_order_predictions_agree_in_sign_with_measured_changes(toy, name):
    task = toy_task(3, [0, 0, 1])
    scorer, optimizer = toy(lr=1e-2, sgd=True)
    records = steps(rl.METHODS[name], scorer, optimizer, [task], CYCLES[0], 30)
    checked = [r for r in records if abs(r["predicted_change"]) > 1e-6]
    assert len(checked) == 30 and all(
        (r["predicted_change"] > 0) == (r["measured_change"] > 0) for r in checked)


@pytest.mark.parametrize("cycle", CYCLES)
def test_mapping_control_an_index_mistake_credits_another_candidate_and_never_fits(
        toy, monkeypatch, cycle):
    mapping_mutant(monkeypatch)
    n = len(cycle)
    task = toy_task(3, [1] + [0] * (n - 1))
    credited = cycle[cycle[0]]  # the p.index(k) error credits p∘p of the rewarded candidate
    scorer, optimizer = toy(lr=1e-2, sgd=True)
    before = true_probs(scorer, task, cycle)
    steps(rl.exact_table_step, scorer, optimizer, [task], cycle, 1)
    assert true_probs(scorer, task, cycle)[credited] > before[credited]
    scorer, optimizer = toy()
    start = true_probs(scorer, task, cycle)[0]
    steps(rl.exact_table_step, scorer, optimizer, [task], cycle, 200)
    after = true_probs(scorer, task, cycle)
    assert after[0] < min(0.95, start) and after[credited] > 0.9


@pytest.mark.parametrize("name", sorted(rl.METHODS))
def test_state_dependence_each_context_learns_its_own_winner(toy, name):
    method = rl.METHODS[name]
    for exchanged in (False, True):
        tasks = [toy_task(3, [0, 1, 0] if exchanged else [1, 0, 0]),
                 toy_task(4, [1, 0, 0] if exchanged else [0, 1, 0])]
        scorer, optimizer = toy()
        for update in range(150):
            permutations = {t["hash"]: cand.training_orderings(3, t["hash"], update, 2,
                                                               t["eval_orderings"])
                            for t in tasks}
            method(scorer, optimizer, tasks, permutations, {})
        for task in tasks:
            for permutation in task["eval_orderings"]:
                probs = true_probs(scorer, task, permutation)
                assert task["rewards"][max(range(3), key=probs.__getitem__)] == 1


class ScalarScorer:
    """Slot k scores theta[p[k]]: the exact objective's gradient is hand-computable."""

    def __init__(self, theta):
        import torch

        self.model = torch.nn.Module()
        self.model.theta = torch.nn.Parameter(torch.tensor(theta, dtype=torch.float64))

    def adapter_state(self):
        return {"theta": self.model.theta.detach().clone()}

    def slot_log_probs(self, task, permutation):
        import torch

        scores = torch.stack([self.model.theta[permutation[k]] for k in range(len(permutation))])
        return torch.log_softmax(scores, dim=0)


@pytest.mark.parametrize("permutations", [[[1, 2, 0]], [[1, 2, 0], [0, 2, 1], [1, 0, 2]]])
def test_exact_table_gradient_and_loss_equal_a_hand_computation(permutations):
    torch = pytest.importorskip("torch")
    theta, rewards = [0.3, -0.2, 0.5], [1, 0, 1]
    scorer = ScalarScorer(theta)
    optimizer = torch.optim.SGD(scorer.model.parameters(), lr=1e-3)
    task = toy_task(3, rewards)
    record = rl.exact_table_step(scorer, optimizer, [task], {task["hash"]: permutations}, {})
    total = sum(math.exp(t) for t in theta)
    pi = [math.exp(t) / total for t in theta]
    mean = sum(p * r for p, r in zip(pi, rewards))
    gradient = [-p * (r - mean) for p, r in zip(pi, rewards)]
    change = (scorer.model.theta.detach() - torch.tensor(theta, dtype=torch.float64)).tolist()
    assert [-c / 1e-3 for c in change] == pytest.approx(gradient, rel=1e-9)
    assert record["loss"] == pytest.approx(-mean, rel=1e-12)
    flat = toy_task(3, [0, 0, 0])
    before = scorer.model.theta.detach().clone()
    record = rl.exact_table_step(scorer, optimizer, [flat], {flat["hash"]: permutations}, {})
    assert record["updated"] is False and torch.equal(scorer.model.theta.detach(), before)


def test_rendering_prints_the_nearest_enemy_and_each_slots_candidate_line():
    context = {"time_ms": 120100, "remaining_ms": 900000, "friendly": [
        {"id": "f1", "type": "spear", "class": "infantry", "men": 90, "men0": 90, "hp": 1,
         "ammo": 0, "x": 0, "z": 0, "state": []}],
        "enemy": [{"id": "e1", "type": "orc", "class": "infantry", "men": 80, "men0": 90,
                   "x": 30.4, "z": 40, "state": ["moving"]}]}
    listed = [{"id": f"c{i}", "orders": [], "description": f"line of candidate {i}"}
              for i in range(5)]
    rendered = rl.render_context(context, listed, [1, 2, 3, 4, 0])
    assert "nearest enemy e1 at 50 m" in rendered
    lines = rl.choice_lines(rendered)
    assert lines == {k: f"line of candidate {[1, 2, 3, 4, 0][k]}" for k in range(5)}
    assert lines != {k: f"line of candidate {[1, 2, 3, 4, 0].index(k)}" for k in range(5)}


def table(tmp_path, rewards=(1, 0, 1), refused=("c3",), root="root-a"):
    listed = [{"id": f"c{i}", "orders": [], "description": f"d{i}"} for i in range(3)]
    rung = {"root": root, "tick": 2100, "context": {"time_ms": 1}, "candidates": listed,
            "rewards": list(rewards), "refused": list(refused), "launches": 6}
    path = tmp_path / f"{root}-table.json"
    path.write_text(json.dumps({"name": "a", "rungs": [rung]}))
    return path


def test_tasks_carry_their_table_exactly_and_transforms_touch_training_rewards_only(tmp_path):
    task = rl.tasks_from_table(table(tmp_path), {"root-a": "train"})[0]
    assert task["rewards"] == [1, 0, 1] and [c["id"] for c in task["candidates"]] == [
        "c0", "c1", "c2"] and task["mapping"] == cand.mapping_hash(task["candidates"])
    assert task["cost"] == 6 and len(task["eval_orderings"]) == 3
    held = rl.tasks_from_table(table(tmp_path, root="root-b"), {"root-b": "held_out"})[0]
    one = rl.task_set("s", [task, held])
    assert rl.task_set("s", [held, task])["hash"] == one["hash"]
    deranged = rl.transform([task, held], "derange_first_loser")
    assert deranged[0]["rewards"] == [0, 1, 0] and deranged[1] == held
    assert deranged[0]["provenance"]["transform"]["kind"] == "derange_first_loser"
    assert rl.task_set("s", deranged)["hash"] != one["hash"]
    clash = rl.tasks_from_table(table(tmp_path, root="root-a", rewards=(0, 1, 1)),
                                {"root-a": "held_out"})[0]
    with pytest.raises(ValueError, match="two splits"):
        rl.task_set("s", [task, clash])
    flat = rl.tasks_from_table(table(tmp_path, root="root-c", rewards=(1, 1, 1)),
                               {"root-c": "train"})
    assert flat == []


def scored_rows(task, bias_slot=0, strength=3.0):
    """Slot-indexed scores from a fake scorer biased to one displayed slot."""
    rows = []
    for permutation in task["eval_orderings"]:
        logits = [strength if k == bias_slot else 0.0 for k in range(len(permutation))]
        total = math.log(sum(math.exp(v) for v in logits))
        rows.append({"permutation": permutation, "slot_log_probs": [v - total for v in logits],
                     "argmax_slot": bias_slot,
                     "argmax_candidate": cand.slot_to_candidate(permutation, bias_slot),
                     "argmax_line": ""})
    return rows


@pytest.mark.parametrize("cycle", CYCLES)
def test_metrics_equal_hand_values_for_a_slot_biased_scorer(cycle):
    n = len(cycle)
    task = toy_task(3, [0] * (n - 1) + [1])
    task["eval_orderings"] = [cycle]
    m = rl.metrics([task], {task["hash"]: scored_rows(task)})
    winner_slot_prob = 1 / (1 + (n - 1) * math.exp(-3.0))
    # Slot 0 shows candidate cycle[0] = 1: a loser, so the mass is a non-top slot's share.
    other = math.exp(-3.0) * winner_slot_prob
    t = m["tasks"][task["hash"]]
    assert t["mass"] == pytest.approx(other) and t["argmax_accuracy"] == 0
    assert t["index0"] == 0 and t["uniform"] == pytest.approx(1 / n)
    assert m["splits"]["train"]["argmax_accuracy_by_index"] == [0]
    shifted = scored_rows(task, bias_slot=cycle.index(n - 1))
    t = rl.metrics([task], {task["hash"]: shifted})["tasks"][task["hash"]]
    assert t["argmax_accuracy"] == 1 and t["mass"] == pytest.approx(winner_slot_prob)


def test_compare_refuses_evaluations_that_differ_in_a_listed_field(tmp_path):
    base = {"task_set": "t", "start_adapter": "a/adapter-0000.json", "rendering_version": 1,
            "candidates_version": 1, "temperature": 1.0, "k_eval": {"x": 3},
            "permutation_rule": "r", "token_cap": 1536, "evaluation_version": 1, "updates": 3,
            "training": {"launches": 0}, "method": "exact_table@1", "kl_from_start": 0.1,
            "adapter": "a/adapter-final.json", "metrics": {"splits": {"held_out": {
                "argmax_accuracy_min": .9, "argmax_accuracy_max": 1, "mass": .9, "uniform": .2,
                "index0": .2, "majority_class": .5}}}}
    paths = []
    for name, change in (("a", {}), ("b", {}), ("c", {"token_cap": 1024})):
        path = tmp_path / name / "eval.json"
        path.parent.mkdir()
        path.write_text(json.dumps({**base, **change}))
        paths.append(path)
    assert "exact_table@1" in rl.compare(paths[:2], "held_out")
    with pytest.raises(ValueError, match="token_cap"):
        rl.compare(paths, "held_out")


def test_a_second_process_cannot_take_a_held_gpu_lease_until_the_holder_dies(tmp_path):
    lock = tmp_path / "gpu.lock"
    hold = (f"from gameai.lm import gpu_lease; from pathlib import Path; import time\n"
            f"with gpu_lease(Path({str(lock)!r})):\n    print('held', flush=True)\n"
            f"    time.sleep(60)\n")
    take = (f"from gameai.lm import gpu_lease; from pathlib import Path\n"
            f"with gpu_lease(Path({str(lock)!r})):\n    print('taken')\n")
    holder = subprocess.Popen([sys.executable, "-c", hold], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "held"
        refused = subprocess.run([sys.executable, "-c", take], capture_output=True, text=True)
        assert refused.returncode != 0 and "owns the GPU lease" in refused.stderr
    finally:
        holder.kill()
        holder.wait()
    time.sleep(0.1)
    taken = subprocess.run([sys.executable, "-c", take], capture_output=True, text=True)
    assert taken.returncode == 0 and taken.stdout.strip() == "taken"


def test_model_phases_refuse_beside_a_running_game(monkeypatch):
    from twwarhammer3.engine import runtime

    monkeypatch.setattr(runtime, "running_pids", lambda: "1234")
    with pytest.raises(RuntimeError, match="beside the game"):
        rl.refuse_beside_game()
    monkeypatch.setattr(runtime, "running_pids", lambda: "")
    monkeypatch.setattr(rl, "committed_revision", lambda purpose, paths: (_ for _ in ()).throw(
        ValueError("Commit implementation changes before checkpoint RL")))
    with pytest.raises(ValueError, match="Commit"):
        rl.refuse_beside_game()


def test_recount_rederives_evaluation_metrics_and_notices_a_changed_record(tmp_path):
    task = toy_task(3, [0, 0, 1])
    held = toy_task(4, [0, 1, 0], split="held_out")
    tasks = rl.task_set("s", [task, held])
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(json.dumps(tasks))
    scored = {t["hash"]: scored_rows(t) for t in tasks["tasks"]}
    evaluation = {"task_set": tasks["hash"], "scored": scored, "updates": 0,
                  "start_adapter": str(tmp_path / "adapter-0000.json"), "kl_from_start": 0.0,
                  "metrics": rl.metrics(tasks["tasks"], scored)}
    path = tmp_path / "eval-adapter-0000-x.json"
    path.write_text(json.dumps(evaluation))
    assert rl.recount(path, tasks_path)["pass"]
    evaluation["metrics"]["splits"]["train"]["mass"] = 0.99
    path.write_text(json.dumps(evaluation))
    assert not rl.recount(path, tasks_path)["pass"]


JOBS = REPO_ROOT / "runs/twwarhammer3/battle"
TRAIN_JOB, HELD_JOB = ("bench-b29-rifle-orcs-floor-attack-20261018",
                       "bench-b45-savage10-glm-low-l1-20261020")


@pytest.fixture(scope="module")
def synthetic():
    if not (JOBS / TRAIN_JOB).exists() or not (JOBS / HELD_JOB).exists():
        pytest.skip("the recorded template jobs are absent")
    templates = {"train": [(TRAIN_JOB, o) for o in rl.template_observations(JOBS / TRAIN_JOB)],
                 "held_out": [(HELD_JOB, o) for o in rl.template_observations(JOBS / HELD_JOB)]}
    reference = templates["train"][0][1]
    tasks = rl.synthetic_tasks(templates, reference, seed=1, counts={"train": 60, "held_out": 30})
    return templates, reference, tasks


def numbers_out(text):
    import re
    return re.sub(r"-?\d+(\.\d+)?", "#", text)


def test_synthetic_contexts_differ_from_the_reference_only_in_positions(synthetic):
    templates, reference, tasks = synthetic
    assert (len(templates["train"]), len(templates["held_out"])) == (186, 152)
    base = rl.play.context_projection(rl.play.public(reference, {}))

    def paths(a, b, at=""):
        if isinstance(a, dict) and isinstance(b, dict):
            assert set(a) == set(b), at
            for key in a:
                yield from paths(a[key], b[key], f"{at}.{key}")
        elif isinstance(a, list) and isinstance(b, list):
            assert len(a) == len(b), at
            for i, (x, y) in enumerate(zip(a, b)):
                yield from paths(x, y, f"{at}[{i}]")
        elif a != b:
            yield at
    allowed = {f".{side}[{i}].{axis}" for side in ("friendly", "enemy") for i in range(2)
               for axis in ("x", "z")}
    for task in tasks:
        assert set(paths(base, task["context"])) <= allowed
        rendered = rl.render_context(task["context"], task["candidates"], [0, 1, 2, 3, 4][
            :len(task["candidates"])])
        guns = next(line for line in rendered.splitlines() if line.startswith("f2 "))
        printed = int(guns.rsplit("nearest enemy e1 at ", 1)[1].split(" m")[0])
        assert abs(printed - task["provenance"]["d"]) <= 1
        assert sum(task["rewards"]) == 1 and task["cost"] == 0
        winner = task["candidates"][task["rewards"].index(1)]["id"]
        assert winner == ("fall_back_f2" if task["provenance"]["d"] < 100 else "attack_nearest")


def test_the_two_classes_render_alike_except_for_numbers_and_no_value_is_split_specific(
        synthetic):
    templates, reference, tasks = synthetic
    base = rl.play.context_projection(rl.play.public(reference, {}))
    template = rl.play.context_projection(rl.play.public(templates["train"][5][1], {}))
    near = rl.synthetic_context(base, template, 60, 200)
    far = rl.synthetic_context(base, template, 160, 200)
    texts = []
    for context in (near, far):
        listed = rl.candidates(context)["candidates"]
        texts.append(rl.render_context(context, listed, list(range(len(listed)))))
    assert texts[0] != texts[1] and numbers_out(texts[0]) == numbers_out(texts[1])
    stripped = {split: {numbers_out(rl.render_context(t["context"], t["candidates"], list(
        range(len(t["candidates"]))))) for t in tasks if t["split"] == split}
        for split in ("train", "held_out")}
    assert stripped["train"] == stripped["held_out"]
    rl.validate_splits(tasks)


def test_no_held_out_draw_repeats_a_training_draw_on_a_nearby_template(synthetic):
    _, _, tasks = synthetic
    train = [t for t in tasks if t["split"] == "train"]
    for task in (t for t in tasks if t["split"] == "held_out"):
        key = (round(task["provenance"]["d"]), round(task["provenance"]["bearing"]))
        for other in train:
            same = (round(other["provenance"]["d"]), round(other["provenance"]["bearing"])) == key
            assert not (same and rl._displacement(other["context"], task["context"]) < 5)
    labels = [t["provenance"]["class"] for t in tasks]
    assert 0.3 < labels.count("near") / len(labels) < 0.7
    shuffled = rl.transform(tasks, "shuffle_classes", seed=7)
    assert [t for t in shuffled if t["split"] == "held_out"] == [
        t for t in tasks if t["split"] == "held_out"]
    assert any(a["rewards"] != b["rewards"] for a, b in zip(shuffled, tasks))


def test_update_records_chain_and_recount_refuses_a_run_that_saw_a_held_out_task(toy, tmp_path):
    scorer, optimizer = toy()
    tasks = [toy_task(3, [1, 0, 0]), toy_task(4, [0, 1, 0]), toy_task(5, [0, 0, 1])]
    held = toy_task(6, [1, 0, 0], split="held_out")
    value = rl.task_set("s", tasks + [held])
    set_path = tmp_path / "tasks.json"
    set_path.write_text(json.dumps(value))
    run = tmp_path / "run"
    run.mkdir()
    plan = {"method": "exact_table@1", "task_set": str(set_path), "batch_size": 2, "K": 2,
            "order_seed": 0, "max_updates": 4}
    (run / "plan.json").write_text(json.dumps(plan))
    records = rl.run_updates(scorer, optimizer, tasks, plan, run, value["hash"])
    assert [r["ordinal"] for r in records] == [0, 1, 2, 3]
    assert [len(r["tasks"]) for r in records] == [2, 1, 2, 1]
    assert {h for r in records[:2] for h in r["tasks"]} == {t["hash"] for t in tasks}
    for record in records:
        for task_hash, permutations in record["permutations"].items():
            task = next(t for t in tasks if t["hash"] == task_hash)
            assert len(permutations) == 2 and all(p not in task["eval_orderings"]
                                                  for p in permutations)
    (run / "adapter-final.json").write_text(json.dumps(
        {"adapter": {"tensors": records[-1]["adapter_after"]}}))
    assert rl.recount(run)["pass"]
    leaked = json.loads((run / "update-0002.json").read_text())
    leaked["tasks"].append(held["hash"])
    (run / "update-0002.json").write_text(json.dumps(leaked))
    assert rl.recount(run)["checks"]["no_held_out"] is False


def test_a_run_records_the_k_and_batch_size_it_trains_with():
    # Regression (2026-10-26): K 1 at the top level trained with K 1 while plan.json's settings
    # said K 4, so the evaluation config_hash of K 1 and K 4 runs was the same.
    one = rl.run_plan({"K": 1, "batch_size": 8}, "rev")
    assert (one["K"], one["batch_size"]) == (1, 8)
    assert (one["settings"]["K"], one["settings"]["batch_size"]) == (1, 8)
    four = rl.run_plan({}, "rev")
    assert four["settings"]["K"] == 4 == four["K"]
    assert rl.digest(one["settings"]) != rl.digest(four["settings"])
