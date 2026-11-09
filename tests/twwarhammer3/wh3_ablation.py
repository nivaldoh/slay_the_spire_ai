"""Ablation diffs for scripted witnesses: run a witness and one of its ablations on the same
observations and check that their orders differ only where the ablation says they may.

Shared infrastructure S8 of the 2026-11-08 siege evaluation plan (portfolio.md in
runs/siege-evals-20261108). Each policy is made fresh and decides on its own copy of what
play.public lets a controller read of every observation (no ``evaluation``, ``final``, ``setup``
or ``native``). It then gets an acknowledgement in which every order applied, with the fields of
a recorded ack (request, based_on, applied_ms, and index, unit, ok and queued per order). Offline
only: this shows what a script orders, not what the engine does with it.
"""

from copy import deepcopy

from twwarhammer3.battle import play

RENAMED_JOB = "ablation-check-renamed-job"


def run(make_policy, observations):
    """The orders a fresh policy gives at each observation, every order acknowledged as applied."""
    policy, decisions = make_policy(), []
    for request, observation in enumerate(observations, 1):
        orders = deepcopy(policy.decide(play.public(deepcopy(observation), {})))
        decisions.append(orders)
        ack = {"request": f"ablation-r{request}", "based_on": observation.get("seq", request),
               "applied_ms": observation.get("time_ms", 0),
               "results": [{"index": index, "unit": order.get("unit"), "ok": True,
                            "queued": False} for index, order in enumerate(orders, 1)]}
        policy.acknowledge(ack, {"think_s": 0.0, "roundtrip_s": 0.0, "delay_ms": 0})
    return decisions


def assert_ablation(make_witness, make_ablation, observations, *, units=(), rules=None):
    """Assert that at every observation the ablation gives the witness's orders, apart from
    orders for ``units`` (unit ids) and orders a rule in ``rules`` selects ({name: test(
    observation, order) -> bool}); and that neither policy's orders change when only the
    observation's ``job`` changes. With anything exempt, the exempt orders must differ at least
    once. Returns the indices of the observations where the two policies' orders differ."""
    rules = rules or {}
    exempt = set(units)

    def kept(observation, orders):
        return [order for order in orders if order.get("unit") not in exempt
                and not any(test(observation, order) for test in rules.values())]

    witness = run(make_witness, observations)
    ablation = run(make_ablation, observations)
    for index, observation in enumerate(observations):
        if kept(observation, witness[index]) != kept(observation, ablation[index]):
            raise AssertionError(
                f"observation {index}: the ablation changed orders outside units"
                f" {sorted(exempt)} and rules {sorted(rules)}:\n witness  {witness[index]}\n"
                f" ablation {ablation[index]}")
    changed = [index for index in range(len(observations)) if witness[index] != ablation[index]]
    # JUDGEMENT?: Unwired ablation — Claude, 2026-11-08: an ablation that names units or rules
    # must change some order. Allowing no change would pass an unwired arm flag; the arm-wiring
    # checks of the witness modules rest on this.
    if (exempt or rules) and not changed:
        raise AssertionError("the ablation never changed an order: is its rule wired?")
    renamed = []
    for observation in observations:
        if observation.get("job") == RENAMED_JOB:
            raise ValueError("an observation already carries the renamed job")
        renamed.append({**observation, "job": RENAMED_JOB})
    for name, make, orders in (("witness", make_witness, witness),
                               ("ablation", make_ablation, ablation)):
        again = run(make, renamed)
        for index, (before, after) in enumerate(zip(orders, again, strict=True)):
            if before != after:
                raise AssertionError(f"observation {index}: the {name}'s orders changed when only"
                                     f" the job changed:\n before {before}\n after  {after}")
    return changed
