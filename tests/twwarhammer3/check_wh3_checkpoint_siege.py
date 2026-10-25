"""Repeatable siege checkpoint check, without paid model calls (15 game launches).

uv run --locked python tests/twwarhammer3/check_wh3_checkpoint_siege.py \\
    --output runs/twwarhammer3/siege-NAME
uv run --locked python tests/twwarhammer3/check_wh3_checkpoint_siege.py --recount EXISTING_OUTPUT

For each saved state: two restores receive the source's later inputs; a third receives an
extra Gelt move 100 ticks after handover. Every planned tick and reading must be present;
the identical restores must match live readings exactly, and the extra order
must cause later divergence. Raw cached infocard differences remain separate diagnostics.
Witnesses require actual spells, unit states, siege equipment and field-state changes.
Cached infocard text is diagnostic. Armour is checked on the tested spell target;
all other fields compare exactly.
Source-only inputs build field towers; tick-1 scripts transfer ownership through the API
without testing normal capturing. Recount reads evidence only and never rewrites its verdict.
Walk/run speed readings are engine capabilities, not instantaneous movement velocity.
"""
import argparse
import copy
import json
import math
import shutil
from collections import Counter
from pathlib import Path

import check_wh3_checkpoint as land
from checkpoint_siege.lobby import make_lobby_steps

from gameai.provenance import sha256, write_json
from twwarhammer3.battle import checkpoint, setup
from twwarhammer3.engine import runtime
from twwarhammer3.protocol import ProtocolError

FIXTURES = Path(__file__).with_name("checkpoint_siege")
STOP, EVERY = 2400, 50
SPELL = "wh_main_spell_metal_glittering_robe"
GELT = "wh_main_emp_cha_balthasar_gelt_1"
SWORDS, GUNS = "wh_main_emp_inf_swordsmen", "wh_main_emp_inf_handgunners"
CAVALRY, CANNON = "wh_main_emp_cav_empire_knights", "wh_main_emp_art_great_cannon"
FRIENDLY_TYPES = {GELT, SWORDS, GUNS, CAVALRY, CANNON}
# JUDGEMENT: Codex, 2026-10-25: these three fixtures exercise the owner's requested siege
# states. Other maps, armies and equipment combinations would extend the verified scope;
# a passing result establishes these declared cases only.
CASES = {
    "helmgart-defender": {"map": "battle_preset_wh2_dlc13_minor_settlement_empire_fort",
                          "attacker": "enemy", "rams": 1, "towers": 1, "field": False},
    "capital-attacker": {"map": "battle_preset_major_a_emp",
                         "attacker": "player", "rams": 2, "towers": 0, "field": False},
    "helmgart-field": {"map": "battle_preset_wh2_dlc13_minor_settlement_empire_fort",
                       "attacker": "enemy", "rams": 1, "towers": 2, "field": True},
}


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def source_plan(name: str, case: dict) -> dict:
    scenario = copy.deepcopy(setup.scenarios()["emp5-emp5"])
    scenario.update(name=name, battle_type="siege", map=case["map"], attacker=case["attacker"])
    scenario["player"]["units"][0] = "wh_main_emp_cha_balthasar_gelt_0"
    scenario["player"]["mounts"] = {"0": GELT}
    for side in ("player", "enemy"):
        scenario[side]["units"] += [SWORDS] * 3
    scenario["expect"] = {**setup.scenarios()["chd-reserve-grn-siege"]["expect"],
                          "funds_amount": 20000, "player_defends": case["attacker"] == "enemy"}
    script = land.SCRIPT.replace("a:units():item(2)", "a:units():item(6)")
    script = script[:script.rindex("return ")] + fixture("assault.lua")
    attack_side = "1" if case["attacker"] == "player" else "2"
    lua_at = [{"tick": 1, "label": "battle_script",
               "lua": script.replace("ATTACK_SIDE", attack_side)},
              {"tick": 300, "label": "cast_glittering_robe", "lua": fixture("cast.lua")}]
    if case["field"]:
        lua_at += [{"tick": 1, "label": "field_setup", "lua": fixture("field.lua").replace(
            "ATTACK_SIDE", attack_side).replace("TRANSFER_OWNERSHIP", "true")},
            {"tick": 1, "label": "gate_exit", "lua": fixture("gate_exit.lua").replace(
                "ATTACK_SIDE", attack_side)},
            {"tick": 100, "label": "build_field_towers", "lua": fixture("build.lua")}]
    if case == CASES["capital-attacker"]:
        lua_at.append({"tick": 200, "label": "cannon_ground_fire",
                       "lua": fixture("ground_fire.lua")})
    reading = ("local battle = (function()\n" + land.READING + "\nend)()\n"
               + "battle = twwarhammer3_json.decode(battle)\n" + fixture("live_units.lua") + "\n"
               + "local siege = (function()\n" + fixture("reading.lua") + "\nend)()\n"
               + "return twwarhammer3_json.encode({battle=battle, "
               + "siege=twwarhammer3_json.decode(siege)})")
    ticks = (2200,) if case["field"] else (1100,)
    return {"scenario": scenario, "stop_tick": STOP, "lua_at": lua_at,
            "lobby_steps": make_lobby_steps(case["rams"], case["towers"], int(attack_side)-1),
            "readings": {"every": EVERY, "lua": reading},
            "save_at": [{"tick": t, "name": name + "-" + str(t)} for t in ticks]}


def agent_code(original: str, open_name: str | None) -> str:
    if open_name is None:
        return original
    marker = "value: evaluate(r.lua, 'checkpoint_reading')"
    assert original.count(marker) == 1, "checkpoint reading hook changed"
    return (original.replace(marker, "value: {...evaluate(r.lua, 'checkpoint_reading'), "
                             "native_gates: gateStates()}")
            + "\n" + fixture("gate_observer.js").replace("GATE_OPEN_NAME", json.dumps(open_name)))


def restore_plan(source: dict, record: dict, changed: bool) -> dict:
    tick = record["tick"]
    lua_at = [r for r in source["lua_at"] if r["tick"] == 1 or r["tick"] > tick]
    if changed:
        lua_at.append({"tick": tick + 100, "label": "changed_flyer_move", "lua": r'''
local a=bm:alliances():item(1):armies():item(1); local u=a:units():item(1)
assert(u:type()=='wh_main_emp_cha_balthasar_gelt_1',u:type())
local p=u:position(); local c=a:create_unit_controller(); c:add_units(u); c:take_control()
c:goto_location(v(p:get_x()+40,p:get_y(),p:get_z()),true)
checkpoint_controllers=checkpoint_controllers or {}
checkpoint_controllers[#checkpoint_controllers+1]=c
return twwarhammer3_json.encode({ms=bm.battle:time_elapsed_ms()})
'''})
    return {"checkpoint": record, "stop_tick": STOP, "readings": source["readings"],
            "lua_at": lua_at}


def armour(unit: dict) -> float | None:
    for stat in unit.get("stats", "").split(";"):
        if stat.startswith("stat_armour="):
            return float(stat.split("=", 1)[1].split("/", 1)[0])
    return None


def spell_active(unit: dict) -> bool:
    return any(effect.split("|", 1)[0] == SPELL for effect in unit.get("effects", "").split(";"))


def spell_witnesses(values: dict[int, dict]) -> dict:
    """Require the named buff on its target, a stat change, then a return to baseline."""
    first = values[min(values)]["battle"]["units"] if values else []
    initial = next((u for u in first if u.get("side") == 1 and u.get("index") == 2), {})
    target_id = initial.get("id")
    target = [(t, next((u for u in v["battle"]["units"]
                       if target_id is not None and u.get("id") == target_id), {}))
              for t, v in sorted(values.items())]
    active = [(t, u) for t, u in target if spell_active(u)]
    baseline = armour(target[0][1]) if target else None
    expired = [(t, u) for t, u in target if active and t > active[-1][0]
               and not spell_active(u) and armour(u) == baseline]
    checks = {"active": bool(active),
              "armour_changed": baseline is not None and any(
                  armour(u) is not None and armour(u) > baseline for _, u in active),
              "expired": bool(expired)}
    return {"checks": checks, "pass": all(checks.values()), "target_id": target_id,
            "baseline_armour": baseline,
            "active_ticks": [t for t, _ in active],
            "first_expired_tick": expired[0][0] if expired else None}


def restore_spell_witness(source: dict[int, dict], restored: dict[int, dict], tick: int,
                          require_expiry: bool = True) -> dict:
    """Match the tested target at handover; witness active-buff expiry on identical restores."""
    reference = spell_witnesses(source)
    uid = reference["target_id"]

    def target(values, at):
        return next((u for u in values.get(at, {}).get("battle", {}).get("units", [])
                     if uid is not None and u.get("id") == uid), {})

    original, actual = target(source, tick), target(restored, tick)
    before, after = armour(original), armour(actual)
    active = spell_active(original)
    checks = {"source_spell_witness": reference["pass"],
              "target_present": bool(original and actual),
              "checkpoint_effects": actual.get("effects") == original.get("effects"),
              "checkpoint_armour": before is not None and math.isfinite(before) and after == before}
    expiry_ticks = []
    if active:
        checks["active_checkpoint_armour_increased"] = (
            reference["baseline_armour"] is not None and before is not None
            and before > reference["baseline_armour"] and spell_active(actual))
        if require_expiry:
            first_expired = reference["first_expired_tick"]
            expiry_ticks = [t for t in sorted(restored) if first_expired is not None
                            and t >= first_expired and target(restored, t)
                            and not spell_active(target(restored, t))
                            and armour(target(restored, t)) == reference["baseline_armour"]]
            checks["expiry_and_baseline_armour"] = bool(expiry_ticks)
    else:
        checks["spell_absent_at_checkpoint"] = not spell_active(actual)
    return {"checks": checks, "pass": all(checks.values()), "target_id": uid,
            "checkpoint_effect_active": active, "source_checkpoint_armour": before,
            "restore_checkpoint_armour": after,
            "first_expired_witness_tick": expiry_ticks[0] if expiry_ticks else None}


def checkpoint_witnesses(values: dict[int, dict], tick: int, case: dict, state: str) -> dict:
    """Use checkpoint state and its prior unit readings, excluding later events."""
    initial = {u["id"]: u for u in values[min(values)]["battle"]["units"]}
    units = [u for t, value in values.items() if t <= tick for u in value["battle"]["units"]]
    current = values[tick]
    siege = current["siege"]
    checks = {
        "spent_ammo": any(u["id"] in initial and u.get("ammo", 0) < initial[u["id"]].get(
            "ammo", 0) for u in units),
        "damaged_units": any(u.get("hp", 1) < 1 for u in units),
        "living_friendly_types_at_checkpoint": FRIENDLY_TYPES <= {
            u["type"] for u in current["battle"]["units"] if u["side"] == 1
            and u.get("men", 0) > 0 and u.get("hp", 0) > 0},
    }
    if case == CASES["helmgart-defender"] or case["field"]:
        checks["climbing_at_checkpoint"] = any(u["climbing"] for u in siege["climbing"])
    if case["field"] and state == "late":
        checks["destroyed_gate_at_checkpoint"] = any(
            g["gate_hp"] == 0 and g["gate_max_hp"] > 0 for g in siege["gates"])
        checks["native_destroyed_gate_at_checkpoint"] = any(
            g["hp"] == 0 and g["max_hp"] > 0 for g in current.get("native_gates", []))
    return checks


def witnesses(values: dict[int, dict], tick: int, case: dict, state: str,
              source_events: list[dict] | None = None) -> dict:
    expected_states = ("gate-open", "late") if case["field"] else ("post-spell",)
    if state not in expected_states:
        raise ValueError(f"expected one of {expected_states}, got {state}")
    first = values[min(values)]
    current = values[tick]
    battle, siege = current["battle"], current["siege"]
    requested = Counter({"emp_battering_ram": case["rams"], "emp_siege_tower_15m": case["towers"]})
    equipment = Counter(e["key"] for e in siege["assault_equipment"])
    categories = Counter(v["category"] for v in siege["vehicles"])
    spell = spell_witnesses(values)
    script = values[max(values)]["battle"].get("script", {})
    checks = {
        "mode": all(v["battle"].get("mode") == "settlement_standard" for v in values.values()),
        "role": all(v["battle"].get("attacker") is (case["attacker"] == "player")
                    for v in values.values()),
        "equipment_keys_and_counts": equipment == requested,
        "spawned_vehicle_counts": categories == Counter(
            {"battering_ram": case["rams"], "siege_tower": case["towers"]}),
        "friendly_types": FRIENDLY_TYPES
            <= {u["type"] for u in first["battle"]["units"] if u["side"] == 1},
        "living_friendly_numeric_readings": all(
            type(u.get(field)) in (int, float) and math.isfinite(u[field])
            for u in battle["units"] if u["side"] == 1
            and u["type"] in FRIENDLY_TYPES
            and u.get("men") != 0 and u.get("hp") != 0
            for field in ("slow_speed", "fast_speed", "morale_percent")),
        "flying": any(u["type"] == GELT and u.get("flying") is True for u in battle["units"]),
        "spell": spell["pass"],
        "script_timers_random_and_order": script.get("fires", 0) > 0
            and len(script.get("draws", [])) == script.get("fires")
            and len(script.get("times", [])) == script.get("fires")
            and any(order.get("ok") is True for order in script.get("orders", [])),
        "capture_and_supply_readings": bool(siege["captures"]) and len(siege["armies"]) == 2
            and all(type(a.get("supplies")) in (int, float) for a in siege["armies"]),
    }
    checks.update(checkpoint_witnesses(values, tick, case, state))
    if state == "post-spell":
        checks["spell_expired_at_checkpoint"] = bool(spell["first_expired_tick"]
                                                     and spell["first_expired_tick"] <= tick)
    if case == CASES["helmgart-defender"]:
        checks["damaged_gate_at_checkpoint"] = any(
            0 < g["gate_hp"] < g["gate_max_hp"] for g in siege["gates"])
    observations = {"spell": spell, "equipment": dict(equipment),
                    "gates": siege["gates"], "captures": siege["captures"],
                    "supplies": [{k: a[k] for k in ("id", "alliance", "supplies")}
                                 for a in siege["armies"]]}
    if case["field"]:
        actions = [action for v in values.values() for action in v["siege"].get("actions", [])]
        builds = {a.get("slot"): a for event in source_events or []
                  if event.get("event") == "lua" and event.get("label") == "build_field_towers"
                  and event.get("tick") == 100 and event["tick"] <= tick
                  for a in event["value"].get("actions", [])
                  if a.get("event") == "build_tower"}
        checks["two_tower_builds_spent_supplies"] = set(builds) == {0, 1} and all(
            a.get("ok") is True and a.get("option") == slot
            and a.get("cost") == {0: 1400, 1: 500}[slot]
            and a["supplies_before"] - a["supplies_after"] == a["cost"]
            for slot, a in builds.items())
        checks["fixture_actions_succeeded"] = bool(actions) and all(
            a.get("ok") is True for a in actions)
        defender = next(a for a in siege["armies"] if a["alliance"] == 0)
        if state == "gate-open":
            checks["intact_open_gate"] = any(
                g["hp"] > 0 and g["state"] != 0 for g in current.get("native_gates", []))
            checks["construction_in_progress"] = sum(
                s["constructing"] and s["construction_s"] > 0 for s in defender["slots"]) >= 2
        if state == "late":
            major = [p for p in siege["captures"] if p["key"].startswith("major_key_building")]
            minor = [p for p in siege["captures"] if p["key"] == "minor_point_supplies"]
            checks["key_and_minor_held_by_attacker"] = (bool(major) and all(
                p["holder_alliance"] == 1 for p in major)
                and {0, 1} <= {p["holder_alliance"] for p in minor})
            completed = {s["index"] for t, v in values.items() if t <= tick
                         for a in v["siege"]["armies"]
                         if a["alliance"] == 0 for s in a["slots"]
                         if s["index"] in (0, 1) and s["any_enabled"] is True
                         and not s["constructing"] and s["current_index"] == s["index"]
                         and s["enabled_index"] == s["index"]}
            checks["both_field_towers_completed_in_history"] = completed == {0, 1}
        observations.update(actions=list(builds.values()), native_gates=current.get("native_gates"))
    return {"checks": checks, "observations": observations, "pass": all(checks.values())}


def compare_runs(source: list[dict], restore: list[dict]) -> dict:
    """Keep the raw comparison; compare live fields independently of infocard text.

    Owner, 2026-10-25: use live engine values, with cached infocard differences reported
    separately. Only battle.units[*].stats is excluded. Armour witnesses are checked on the
    stable spell target, rather than treating cached armour as a live getter for every unit.
    """
    missing_live = []

    def observed(rows, label):
        result = []
        for row in rows:
            if row.get("event") != "reading":
                result.append(row)
                continue
            value = copy.deepcopy(row["value"])
            for unit in value["battle"]["units"]:
                # Getters can be unavailable after a unit dies. Its recorded fields still
                # compare exactly; living units on both sides require every numeric getter.
                if unit.get("men", 0) > 0 and unit.get("hp", 0) > 0:
                    absent = [key for key in ("slow_speed", "fast_speed", "morale_percent")
                              if type(unit.get(key)) not in (int, float)
                              or not math.isfinite(unit[key])]
                    if absent:
                        missing_live.append({"run": label, "tick": row["tick"],
                                             "id": unit["id"], "fields": absent})
                unit.pop("stats", None)
            result.append({**row, "value": value})
        return result

    # Compare readings only where both runs supply one; completeness separately requires
    # the full planned source trace and every post-handover restore reading.
    source_readings = {r["tick"]: r["value"] for r in source if r.get("event") == "reading"}
    restore_readings = {r["tick"]: r["value"] for r in restore if r.get("event") == "reading"}
    shared = source_readings.keys() & restore_readings.keys()
    source_rows = [r for r in source if r.get("event") != "reading" or r["tick"] in shared]
    restore_rows = [r for r in restore if r.get("event") != "reading" or r["tick"] in shared]
    result = checkpoint.compare(observed(source_rows, "source"), observed(restore_rows, "restore"))
    cached = []
    for tick in sorted(shared):
        a = {u["id"]: u for u in source_readings[tick]["battle"]["units"]}
        b = {u["id"]: u for u in restore_readings[tick]["battle"]["units"]}
        differences = [{"id": uid, "source": a[uid].get("stats"), "restore": b[uid].get("stats")}
                       for uid in sorted(a.keys() & b.keys())
                       if a[uid].get("stats") != b[uid].get("stats")]
        if differences:
            cached.append({"tick": tick, "units": differences})
    result.update(strict_comparison=checkpoint.compare(source, restore), cached_stats=cached,
                  live_getters_complete=not missing_live, missing_live_getters=missing_live)
    return result


def fixture_declaration(plan: dict, case: dict) -> dict:
    scenario = plan.get("scenario", {})
    scenario = scenario if isinstance(scenario, dict) else {}
    checks = {"map": scenario.get("map") == case["map"],
              "role": scenario.get("attacker") == case["attacker"],
              "mode": scenario.get("battle_type") == "siege"}
    slot = 0 if case["attacker"] == "player" else 1
    for key, number in (("emp_battering_ram", case["rams"]),
                        ("emp_siege_tower_15m", case["towers"])):
        expression = (f"CustomBattleLobbyContext.PlayerSlotList.At({slot})."
                      f'SiegeEquipmentList.Count(Key == "{key}")')
        reads = [s for s in plan.get("lobby_steps", []) if s.get("expression") == expression]
        checks[key] = bool(reads) and reads[-1].get("required") is True and (
            reads[-1].get("expect") == number)
    return {"checks": checks, "pass": all(checks.values())}


def changed_order_recorded(rows: list[dict], tick: int) -> bool:
    return any(r.get("event") == "lua" and r.get("label") == "changed_flyer_move"
               and r.get("tick") == tick for r in rows)


def assess_case(source: Path, restores: list[Path], changed: Path, checkpoint_tick: int,
                changed_tick: int, case: str | dict, state: str) -> dict:
    """Assess canonical runs or existing probe paths without copying or altering evidence."""
    declaration = CASES[case] if isinstance(case, str) else case
    paths = [Path(source), *(Path(p) for p in restores), Path(changed)]
    if len({p.resolve() for p in paths}) != len(paths):
        raise ValueError("source and every restore must have distinct run directories")
    rows = [checkpoint.events(path) for path in paths]
    manifests = [json.loads((path / "manifest.json").read_text()) for path in paths]
    values = {r["tick"]: r["value"] for r in rows[0] if r.get("event") == "reading"}
    result = {"case": declaration, "state": state, "checkpoint_tick": checkpoint_tick,
              "changed_tick": changed_tick, "checker_sha256": sha256(Path(__file__)), "runs": []}
    for index, (path, events, manifest) in enumerate(zip(paths, rows, manifests)):
        complete = land.completeness(events, stop_tick=STOP, reading_every=EVERY,
                                     restored_at=checkpoint_tick if index else None)
        run = {"path": str(path.resolve()), "manifest_sha256": sha256(path / "manifest.json"),
               "events_sha256": sha256(path / "native/native.jsonl"),
               "source_revision": manifest["source_revision"],
               "agent_sha256": manifest["agent_sha256"], "complete": complete,
               "closed": manifest.get("closed") is True,
               "completed": manifest.get("completed") is True and "error" not in manifest}
        run["pass"] = complete["pass"] and run["closed"] and run["completed"]
        if index:
            comparison = compare_runs(rows[0], events)
            run["comparison"] = comparison
            restore_values = {r["tick"]: r["value"] for r in events if r.get("event") == "reading"}
            run["spell_witness"] = restore_spell_witness(
                values, restore_values, checkpoint_tick, require_expiry=index != len(paths)-1)
            restored = (comparison["restored_at"] == checkpoint_tick
                        and comparison["seed_matches"] is True)
            if index == len(paths)-1:
                same = (comparison["checksum_mismatches"] > 0
                        and changed_tick < comparison["first_mismatch"] <= STOP
                        and bool(comparison["readings_unequal"])
                        and all(t >= changed_tick for t in comparison["readings_unequal"])
                        and changed_order_recorded(events, changed_tick))
            else:
                same = comparison["checksum_mismatches"] == 0 and not comparison["readings_unequal"]
            run["pass"] = (run["pass"] and restored and same
                           and run["spell_witness"]["pass"]
                           and comparison["live_getters_complete"])
        result["runs"].append(run)
    result["two_restores"] = len(restores) == 2
    result["source_saved"] = any(e.get("event") == "saved" and e["tick"] == checkpoint_tick
                                  for e in rows[0])
    result["same_source_and_agent"] = all(
        m["source_files"] == manifests[0]["source_files"]
        and m["agent_sha256"] == manifests[0]["agent_sha256"] for m in manifests)
    result["fixture_declaration"] = fixture_declaration(manifests[0]["plan"], declaration)
    try:
        result["source_menu"] = {"pass": True, "readbacks": setup.check_menu(
            manifests[0]["plan"]["scenario"], paths[0])}
    except ProtocolError as error:
        result["source_menu"] = {"pass": False, "error": str(error)}
    if result["runs"][0]["complete"]["pass"]:
        result["witnesses"] = witnesses(values, checkpoint_tick, declaration, state, rows[0])
    else:
        result["witnesses"] = {"pass": False, "error": "source trace incomplete"}
    result["pass"] = (result["two_restores"] and result["source_saved"]
                      and result["fixture_declaration"]["pass"] and result["source_menu"]["pass"]
                      and result["same_source_and_agent"] and result["witnesses"]["pass"]
                      and all(run["pass"] for run in result["runs"]))
    return result


def checkpoint_states(directory: Path, case: dict) -> dict[str, int]:
    states = {"post-spell": 1100}
    if case["field"]:
        record = checkpoint.saved(directory / "source", directory.name + "-gate-open")
        states = {"gate-open": record["tick"], "late": 2200}
    return states


def source_witnesses(rows: list[dict], case: dict, states: dict[str, int]) -> dict:
    complete = land.completeness(rows, stop_tick=STOP, reading_every=EVERY)
    values = {r["tick"]: r["value"] for r in rows if r.get("event") == "reading"}
    checks = {state: {"tick": tick, **witnesses(values, tick, case, state, rows)}
              for state, tick in states.items()} if complete["pass"] else {}
    return {"complete": complete, "states": checks,
            "pass": complete["pass"] and all(result["pass"] for result in checks.values())}


def assess_directory(directory: Path, case: dict) -> dict:
    results = {}
    source = directory / "source"
    for state, tick in checkpoint_states(directory, case).items():
        state_dir = directory / state
        results[directory.name + "/" + state] = assess_case(
            source, [state_dir / "restore-a", state_dir / "restore-b"],
            state_dir / "changed", tick, tick + 100, case, state)
    return results


def report(results: dict, completed: list[str]) -> dict:
    return {"states": results, "completed_cases": completed, "all_cases": list(CASES),
            "pass": len(completed) == len(CASES) and all(r["pass"] for r in results.values())}


def assess(output: Path) -> dict:
    results, completed = {}, []
    for name, case in CASES.items():
        current = assess_directory(output / name, case)
        results.update(current)
        completed.append(name)
        if not all(r["pass"] for r in current.values()):
            break
    return report(results, completed)


def run_case(directory: Path, case: dict) -> None:
    directory.mkdir()
    plan = source_plan(directory.name, case)
    original = checkpoint.AGENT
    exact_agent = directory / "checkpoint_agent_used.js"
    exact_agent.write_text(agent_code(original.read_text(), directory.name + "-gate-open"
                                     if case["field"] else None))
    write_json(directory / "fixture.json", {"case": case, "plan": plan,
               "base_agent_sha256": sha256(original), "agent_sha256": sha256(exact_agent)})
    names = [s["name"] for s in plan["save_at"]]
    if case["field"]:
        names.insert(0, directory.name + "-gate-open")
    for name in names:
        if (runtime.user_dir() / "replays" / (name + ".replay")).exists():
            raise FileExistsError(f"replay {name} already exists")
    checkpoint.AGENT = exact_agent.resolve()
    try:
        checkpoint.run(plan, directory / "source")
        source_checks = source_witnesses(checkpoint.events(directory / "source"), case,
                                         checkpoint_states(directory, case))
        witness_path = directory / "source-witnesses.json"
        write_json(witness_path, source_checks)
        if not source_checks["pass"]:
            raise ProtocolError(f"source siege witnesses failed; see {witness_path}")
        for index, name in enumerate(names):
            record = checkpoint.saved(directory / "source", name)
            state = ("gate-open" if index == 0 else "late") if case["field"] else "post-spell"
            for run in ("restore-a", "restore-b", "changed"):
                checkpoint.run(restore_plan(plan, record, run == "changed"),
                               directory / state / run)
    finally:
        checkpoint.AGENT = original
        log = directory / "source/native/native.jsonl"
        saved_events = checkpoint.events(directory / "source") if log.exists() else []
        for saved in (e for e in saved_events if e.get("event") == "saved"):
            path = runtime.user_dir() / "replays" / (saved["name"] + ".replay")
            if path.exists():
                shutil.move(path, directory / path.name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--recount", type=Path)
    args = parser.parse_args()
    if args.recount:
        checks = assess(args.recount.resolve())
    else:
        output = args.output.resolve()
        output.mkdir(parents=True)
        results, completed = {}, []
        for name, case in CASES.items():
            run_case(output / name, case)
            current = assess_directory(output / name, case)
            results.update(current)
            completed.append(name)
            checks = report(results, completed)
            write_json(output / "checks.json", checks)
            if not all(r["pass"] for r in current.values()):
                break
    print(json.dumps(checks, indent=1))
    return 0 if checks["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
