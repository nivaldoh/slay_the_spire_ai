"""Materialize B's private intervention separately from the public battle state.

Reference: SMACv2 smacv2/env/starcraft2/wrapper.py, reset (577ab5a): draw an
explicit configuration before running the environment. No reset retries or stepped time.
The intervention seed reproduces selection only, never the engine trajectory.

Version 3, kind ``waves`` (the 2026-11-08 siege defence design, cth-emp-siege-a-v1), has no draw:
``{"version": 3, "kind": "waves", "groups": [{"slots", "types", "release_ms"}, ...],
"release_on_damage"}``. Each group's one-based enemy ``deployment`` slots, with the type each
slot must place, are held at their placements and handed to native AI at ``release_ms`` of
battle time, or at once when that group is damaged (``setup_waves``/``tick_waves`` in the
battle Lua). Units bind by deployment slot and type, never by roster index.
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
TRIGGER_MS, V1_RELEASE_MS = 45000, 165000
# JUDGEMENT: Reserve route completion — Codex, 2026-11-05: v2 releases a committed
# reserve within 25 m of its final region, when unavailable, or at 360 s; others hold
# to the bound. A fixed guessed duration differs; v1's outside routes were incomplete at 165 s.
ARRIVAL_M, HARD_RELEASE_MS = 25, 360000
# JUDGEMENT: Waves briefing — Claude, 2026-11-08 (design, Public briefing): this one sentence, no
# times, groups or trigger; a prompt shows it after llm.py render_prompt's "Reserve briefing:" label
# (line 415). Silence, the times or another label inform a model otherwise; its results rest on it.
WAVES_BRIEFING = ("The attacking army is drawn up in several divisions, which may attack at "
                  "different times.")


def briefing(scenario):
    """Public rules and an explicit foreknowledge control, never the private draw wholesale.
    A waves profile shows only WAVES_BRIEFING."""
    draw = scenario["reserve"]
    if draw.get("kind") == "waves":
        return WAVES_BRIEFING
    release = {"bound_ms": V1_RELEASE_MS if draw["version"] == 1 else HARD_RELEASE_MS}
    if draw["version"] == 2:
        release.update(arrival_m=ARRIVAL_M, unavailable=True)
    result = {"version": 1, "rules": {
        "unit_type": "wh_main_emp_inf_swordsmen", "controlled_regiments": 2,
        "catalogue": [{"region": region, "side": side, "count": count}
                      for region, side, count in CATALOGUE],
        "trigger_ms": TRIGGER_MS, "release": release,
        "uncommitted": "held until bound, including routing and rally",
        "after_release": "native AI; future targets and trajectory are not prescribed"}}
    # JUDGEMENT: Foreknowledge disclosure — Codex, 2026-11-05: announced arm exposes the
    # realized region/side/count/ground route and timing, not seed or runtime state. A
    # narrower announcement changes the information contrast; no adaptation claim follows.
    if scenario.get("reserve_information") == "announced":
        result["commitment"] = {key: deepcopy(draw[key])
                                for key in ("region", "side", "count", "route", "trigger_ms")}
    return result


def waves(scenario):
    """The checked waves profile, unchanged. Refuses a group without slots, a slot held twice,
    a slot past ``deployment.enemy``, a slot whose placement is not the type its group declares,
    and release times that are negative or out of order."""
    profile = scenario["reserve"]
    groups = profile.get("groups")
    if (set(profile) != {"version", "kind", "groups", "release_on_damage"}
            or profile["version"] != 3 or type(profile["release_on_damage"]) is not bool
            or not isinstance(groups, list) or not groups or scenario.get("custom")):
        raise ValueError("unsupported waves profile")
    placements = (scenario.get("deployment") or {}).get("enemy") or []
    held, previous = set(), 0
    for number, group in enumerate(groups, 1):
        if not isinstance(group, dict) or set(group) != {"slots", "types", "release_ms"}:
            raise ValueError(f"waves group {number} needs slots, their types and release_ms")
        slots, kinds, release = group["slots"], group["types"], group["release_ms"]
        if (not isinstance(slots, list) or not slots or not isinstance(kinds, list)
                or len(kinds) != len(slots)):
            raise ValueError(f"waves group {number} needs one declared type per slot")
        if type(release) is not int or release < previous:
            raise ValueError("waves release times must be whole milliseconds, 0 or more, in"
                             " group order")
        previous = release
        for slot, kind in zip(slots, kinds, strict=True):
            if type(slot) is not int or not 1 <= slot <= len(placements):
                raise ValueError(f"waves group {number} slot {slot!r} is not an enemy"
                                 " deployment slot")
            if slot in held:
                raise ValueError(f"waves slot {slot} is in two groups")
            held.add(slot)
            if placements[slot - 1].get("type") != kind:
                raise ValueError(f"waves group {number} slot {slot} places"
                                 f" {placements[slot - 1].get('type')}, not {kind}")
    return deepcopy(profile)


def materialize(scenario, *, seed=None):
    """A fresh episode's evaluator-only configuration, with an independent 128-bit seed.
    A waves profile has no draw: it is returned unchanged and takes no seed."""
    profile = scenario["reserve"]
    if profile.get("kind") == "waves":
        if seed is not None:
            raise ValueError("a waves profile has no random draw; reserve_seed does not apply")
        return waves(scenario)
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
            "count": count, "trigger_ms": TRIGGER_MS,
            "release_ms": V1_RELEASE_MS if profile["version"] == 1 else HARD_RELEASE_MS,
            "route": route,
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
    if scenario["reserve"].get("kind") == "waves":
        return check_waves(scenario, observation)
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


def check_waves(scenario, observation):
    """The mod's waves evidence (``evaluation.reserve``): the profile it ran, each held unit's
    group, slot, type and enemy id, and each group's release. Refuses a failed setup, a
    profile other than the scenario's, a mod error, units in another order, slot or type than
    the profile declares, an id held twice or whose roster type differs, a failed release, a
    group released twice, and a release before its time that damage did not cause."""
    expected = scenario["reserve"]
    setup = (observation.get("setup") or {}).get("reserve")
    evidence = (observation.get("evaluation") or {}).get("reserve") or {}
    if setup is not None and setup.get("ok") is not True:
        raise ProtocolError(f"reserve setup failed: {setup}")
    if evidence.get("config") != expected or evidence.get("error"):
        raise ProtocolError(f"reserve configuration/effect failure: {evidence.get('error')}")
    declared = [(number, slot, kind) for number, group in enumerate(expected["groups"], 1)
                for slot, kind in zip(group["slots"], group["types"], strict=True)]
    units = evidence.get("units") or []
    roster = {u.get("id"): u.get("type") for u in observation.get("enemy_roster", [])}
    if ([(u.get("group"), u.get("slot"), u.get("type")) for u in units] != declared
            or len({u.get("id") for u in units}) != len(units)
            or any(not u.get("id") or roster.get(u["id"]) != u["type"] for u in units)):
        raise ProtocolError("reserve identity binding failed")
    released = set()
    for release in evidence.get("releases") or []:
        number = release.get("group")
        if release.get("ok") is not True:
            raise ProtocolError(f"reserve release failed: {release.get('error')}")
        if number in released or not isinstance(number, int) or not (
                1 <= number <= len(expected["groups"])):
            raise ProtocolError(f"reserve release of group {number!r} is not one release")
        released.add(number)
        due = expected["groups"][number - 1]["release_ms"]
        if not (release.get("reason") == "time" and release.get("released_ms", -1) >= due
                or release.get("reason") == "damage" and expected["release_on_damage"]):
            raise ProtocolError(f"reserve group {number} released as {release.get('reason')!r}"
                                f" at {release.get('released_ms')} ms")
    return evidence
