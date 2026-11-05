"""Materialize B's private intervention separately from the public battle state.

Reference: SMACv2 smacv2/env/starcraft2/wrapper.py, reset (577ab5a): draw an
explicit configuration before running the environment. No reset retries or stepped time.
The intervention seed reproduces selection only, never the engine trajectory.
"""

import random
import secrets
from copy import deepcopy

from twwarhammer3.protocol import ProtocolError

# JUDGEMENT: Reserve development catalogue — Codex, 2026-11-05: eight combinations of
# region, side and one/two committed swordsmen, 45 s trigger and 165 s release to native AI.
# Other counts/times/routes change the response problem; adaptation remains unverified.
CATALOGUE = tuple((region, side, count) for region in ("centre", "outside")
                  for side in ("north", "south") for count in (1, 2))
# JUDGEMENT: Reserve route completion — Codex, 2026-11-05: v2 releases a committed
# reserve within 25 m of its final region, when unavailable, or at 360 s; others hold
# to the bound. A fixed guessed duration differs; v1's outside routes were incomplete at 165 s.
ARRIVAL_M, HARD_RELEASE_MS = 25, 360000


def materialize(scenario, *, seed=None):
    """A fresh episode's evaluator-only configuration, with an independent 128-bit seed."""
    profile = scenario["reserve"]
    if profile not in ({"version": 1, "slots": [7, 8]}, {"version": 2, "slots": [7, 8]}):
        raise ValueError("unsupported reserve profile")
    placements = scenario["deployment"]["enemy"]
    if any(placements[slot - 1]["type"] != "wh_main_emp_inf_swordsmen"
           for slot in profile["slots"]):
        raise ValueError("reserve slots must bind the declared swordsmen")
    seed = secrets.randbits(128) if seed is None else seed
    region, side, count = random.Random(seed).choice(CATALOGUE)
    z = -225 if side == "north" else -275
    route = [{"x": 115, "z": z}]
    if region == "outside":
        z = -55 if side == "north" else -465
        route = [{"x": 355, "z": z}, {"x": -25, "z": z}]
    return {**deepcopy(profile), "seed": str(seed), "region": region, "side": side,
            "count": count, "trigger_ms": 45000,
            "release_ms": 165000 if profile["version"] == 1 else HARD_RELEASE_MS, "route": route,
            **({"arrival_m": ARRIVAL_M} if profile["version"] == 2 else {})}


def sequence(scenario, count, *, seed=None):
    """An optional private sequence seed reproduces draws, independently of other RNGs.

    Default attempts still use separate OS-entropy seeds. An explicit root seed is for
    construction and matched continuations; it does not reproduce engine trajectories.
    """
    if seed is not None and (type(seed) is not int or seed < 0):
        raise ValueError("reserve sequence seed must be a nonnegative integer")
    rng = random.Random(seed) if seed is not None else None
    return [materialize(scenario, seed=rng.getrandbits(128) if rng else None)
            for _ in range(count)]


def episode_scenario(scenario, draw):
    """Do not mutate the base declaration or another attempt's saved draw."""
    return {**deepcopy(scenario), "reserve": deepcopy(draw)}


def check(scenario, observation):
    """Broken interventions are infrastructure evidence, never silent gameplay losses."""
    expected = scenario["reserve"]
    setup = observation.get("setup", {}).get("reserve")
    evidence = (observation.get("evaluation") or {}).get("reserve") or {}
    if setup is not None and setup.get("ok") is not True:
        raise ProtocolError(f"reserve setup failed: {setup}")
    if evidence.get("config") != expected or evidence.get("error"):
        raise ProtocolError(f"reserve configuration/effect failure: {evidence.get('error')}")
    units = evidence.get("units", [])
    roster = {u.get("id"): u.get("type") for u in observation.get("enemy_roster", [])}
    if (len(units) != len(expected["slots"])
            or [u.get("slot") for u in units] != expected["slots"]
            or len({u.get("id") for u in units}) != len(units)
            or any(not u.get("id") or u.get("type") != "wh_main_emp_inf_swordsmen"
                   or roster.get(u["id"]) != u["type"]
                   for u in units)):
        raise ProtocolError("reserve identity binding failed")
    if any(order.get("ok") is not True for order in (
            *evidence.get("orders", []), *evidence.get("releases", []))):
        raise ProtocolError("reserve route submission failed")
    return evidence
