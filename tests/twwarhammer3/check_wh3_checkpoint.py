"""Check battle checkpoints: a restored battle continues exactly like the battle it was saved from.

Four game launches (about 15 minutes), no paid model calls:

uv run --locked python tests/twwarhammer3/check_wh3_checkpoint.py \
    --output runs/twwarhammer3/checkpoint-check-NAME

1. Source: a small custom battle with a battle script installed at tick 1 (timers, Lua random
   draws, one order of its own after the checkpoint), orders at fixed ticks before and after
   tick 1200, a checkpoint saved at 1200 and readings every 100 ticks.
2-3. Two restores from the Replays menu, giving the same orders at the same ticks.
4. One restore whose first order after the checkpoint differs.

Pass: both restores match the source's native checksum on every tick and every reading
(positions, men, hit points, ammunition, morale, abilities, clock, the script's state), and
the changed restore diverges after its changed order. Agreed by the owner on 2026-10-25.
Owner, 2026-11-03: use live numeric morale/speed as in siege; raw cached stat-panel
differences remain diagnostics. All other readings still compare exactly.
Recount saved evidence without launching: --recount EXISTING_OUTPUT.
For the original strict rule only: --recount OLD_OUTPUT --legacy-raw-recount.
"""
import argparse
import copy
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path

from gameai.provenance import write_json
from twwarhammer3.battle import checkpoint
from twwarhammer3.engine import runtime

SCENARIO = "emp-handgunners-grn-savage-orcs"
CHECKPOINT, STOP, CHANGED_TICK = 1200, 2000, 1300
SCRIPT = r'''
checkpoint_script = {fires = 0, times = {}, draws = {}, orders = {}}
bm:repeat_callback(function()
  checkpoint_script.fires = checkpoint_script.fires + 1
  checkpoint_script.times[#checkpoint_script.times + 1] = bm.battle:time_elapsed_ms()
  checkpoint_script.draws[#checkpoint_script.draws + 1] = math.random(1000000)
end, 7300, "checkpoint_script_repeat")
bm:callback(function()
  local a = bm:alliances():item(1):armies():item(1)
  local ok = pcall(function()
    local c = a:create_unit_controller(); c:add_units(a:units():item(2)); c:take_control()
    c:change_behaviour_active("fire_at_will", false); checkpoint_script.controller = c end)
  local orders = checkpoint_script.orders
  orders[#orders + 1] = {ms = bm.battle:time_elapsed_ms(), ok = ok}
end, 160000, "checkpoint_script_order")
return twwarhammer3_json.encode({ms = bm.battle:time_elapsed_ms()})
'''
READING = checkpoint.READING_LUA


def move(tick, label, index, kind, x, z):
    return {"tick": tick, "label": label, "lua": f'''
local a = bm:alliances():item(1):armies():item(1); local u = a:units():item({index})
assert(u:type() == "{kind}", "wrong unit " .. u:type())
local p = v({x}, bm.battle:get_terrain_height({x}, {z}), {z})
local c = a:create_unit_controller(); c:add_units(u); c:take_control(); c:goto_location(p, false)
checkpoint_controllers = checkpoint_controllers or {{}}
checkpoint_controllers[#checkpoint_controllers + 1] = c
return twwarhammer3_json.encode({{ms = bm.battle:time_elapsed_ms()}})'''}


SPEAR, GUNS = "wh_main_emp_inf_spearmen_1", "wh_main_emp_inf_handgunners"
BEFORE = [move(400, "spearmen_east", 1, SPEAR, -240, 140),
          move(800, "guns_forward", 2, GUNS, -268, 160)]
AFTER = [move(CHANGED_TICK, "spearmen_meet_orcs", 1, SPEAR, -225, 115),
         move(1700, "guns_back", 2, GUNS, -275, 168)]
CHANGED = [move(CHANGED_TICK, "spearmen_back", 1, SPEAR, -245, 160), AFTER[1]]


def plans(output: Path) -> dict:
    name = output.name + "-1200"
    # Keep READING unchanged: the siege check imports it and adds the same live getters.
    live = (Path(__file__).with_name("checkpoint_siege") / "live_units.lua").read_text()
    reading = ("local battle = (function()\n" + READING + "\nend)()\n"
               + "battle = twwarhammer3_json.decode(battle)\n" + live
               + "\nreturn twwarhammer3_json.encode(battle)")
    readings = {"every": 100, "lua": reading}
    setup_lua = [{"tick": 1, "label": "battle_script", "lua": SCRIPT}]
    source = {"scenario": SCENARIO, "save_at": [{"tick": CHECKPOINT, "name": name}],
              "lua_at": setup_lua + BEFORE + AFTER, "readings": readings, "stop_tick": STOP}
    restore = {"lua_at": setup_lua + AFTER, "readings": readings, "stop_tick": STOP}
    return {"name": name, "source": source, "restore": restore,
            "changed": {**restore, "lua_at": setup_lua + CHANGED}}


def completeness(rows: list[dict], *, stop_tick: int, reading_every: int,
                 restored_at: int | None = None) -> dict:
    """Require the whole planned trace, including a clean completion.

    Restores suppress readings during the fast rebuild. The agent can report a few extra
    ticks while its controller shuts down; normal detachment after done is expected.
    """
    ticks = Counter(row["tick"] for row in rows if row.get("event") == "tick")
    readings = Counter(row["tick"] for row in rows if row.get("event") == "reading")
    expected_readings = set(range(reading_every, stop_tick + 1, reading_every))
    if restored_at is not None:
        expected_readings = {tick for tick in expected_readings if tick >= restored_at}
        expected_readings.add(restored_at)
    done = [(i, row) for i, row in enumerate(rows) if row.get("event") == "done"]
    done_index = done[0][0] if done else len(rows)
    errors = [row for i, row in enumerate(rows)
              if row.get("event") in ("error", "frida_error")
              or (row.get("event") == "detached"
                  and (i < done_index or row.get("reason") != "application-requested"))]
    result = {
        "missing_ticks": [tick for tick in range(1, stop_tick + 1) if not ticks[tick]],
        "duplicate_ticks": [tick for tick in range(1, stop_tick + 1) if ticks[tick] > 1],
        "missing_readings": sorted(tick for tick in expected_readings if not readings[tick]),
        "duplicate_readings": sorted(tick for tick in expected_readings if readings[tick] > 1),
        "done": len(done) == 1 and done[0][1]["tick"] == stop_tick,
        "errors": errors,
    }
    result["pass"] = (result["done"] and not errors
                      and not any(result[key] for key in ("missing_ticks", "duplicate_ticks",
                                                         "missing_readings", "duplicate_readings")))
    return result


def compare_live(source: list[dict], restore: list[dict]) -> dict:
    """Exact live readings, with cached stat panels retained as diagnostics.

    Owner, 2026-11-03: extend the existing siege live-value rule to Land.
    Follow the snapshot/comparison pattern in Farama-Foundation/Gymnasium v1.4.0,
    gymnasium/utils/env_checker.py; the reference rule here is siege.compare_runs.
    """
    missing_live = []

    def observed(rows, label):
        result = []
        for row in rows:
            if row.get("event") != "reading":
                result.append(row)
                continue
            value = copy.deepcopy(row["value"])
            if not value["units"]:
                missing_live.append({"run": label, "tick": row["tick"], "fields": ["units"]})
            for unit in value["units"]:
                # Dead units may lack getters; require explicit zero men/HP as evidence
                # of death. Missing state must not exempt a unit from numeric readings.
                known_dead = any(type(unit.get(field)) in (int, float)
                                 and unit[field] == 0 for field in ("men", "hp"))
                if not known_dead:
                    absent = [key for key in ("slow_speed", "fast_speed", "morale_percent")
                              if type(unit.get(key)) not in (int, float)
                              or not math.isfinite(unit[key])]
                    if absent:
                        missing_live.append({"run": label, "tick": row["tick"],
                                             "id": unit.get("id"), "fields": absent})
                unit.pop("stats", None)
            result.append({**row, "value": value})
        return result

    result = checkpoint.compare(observed(source, "source"), observed(restore, "restore"))
    a = {r["tick"]: r["value"] for r in source if r.get("event") == "reading"}
    b = {r["tick"]: r["value"] for r in restore if r.get("event") == "reading"}
    cached = []
    for tick in sorted(a.keys() & b.keys()):
        before = {u.get("id", i): u for i, u in enumerate(a[tick]["units"])}
        after = {u.get("id", i): u for i, u in enumerate(b[tick]["units"])}
        differences = [{"id": uid, "source": before[uid].get("stats"),
                        "restore": after[uid].get("stats")}
                       for uid in sorted(before.keys() & after.keys())
                       if before[uid].get("stats") != after[uid].get("stats")]
        if differences:
            cached.append({"tick": tick, "units": differences})
    result.update(strict_comparison=checkpoint.compare(source, restore), cached_stats=cached,
                  live_getters_complete=not missing_live, missing_live_getters=missing_live)
    return result


def assess(output: Path, *, legacy_raw: bool = False) -> dict:
    source = checkpoint.events(output / "source")
    checks = {"reading_comparison": "raw-v1" if legacy_raw else "live-values-v1",
              "source_saved": any(e.get("event") == "saved" and e["tick"] == CHECKPOINT
                                  for e in source),
              "source_complete": completeness(source, stop_tick=STOP, reading_every=100)}
    for run in ("restore-a", "restore-b", "changed"):
        rows = checkpoint.events(output / run)
        result = checkpoint.compare(source, rows) if legacy_raw else compare_live(source, rows)
        result["complete"] = completeness(rows, stop_tick=STOP, reading_every=100,
                                          restored_at=CHECKPOINT)
        checks[run] = result
        restored = result["restored_at"] == CHECKPOINT and result["seed_matches"] is True
        getters_complete = legacy_raw or result["live_getters_complete"]
        if run == "changed":
            result["pass"] = (restored and result["complete"]["pass"]
                              and getters_complete
                              and result["checksum_mismatches"] > 0
                              and result["first_mismatch"] > CHANGED_TICK
                              and bool(result["readings_unequal"]))
        else:
            result["pass"] = (restored and result["complete"]["pass"]
                              and getters_complete
                              and result["checksum_mismatches"] == 0
                              and not result["readings_unequal"])
    manifests = [json.loads((output / run / "manifest.json").read_text())
                 for run in ("source", "restore-a", "restore-b", "changed")]
    checks["closed"] = all(manifest.get("closed") is True for manifest in manifests)
    checks["completed"] = all(manifest.get("completed") is True and "error" not in manifest
                              for manifest in manifests)
    checks["pass"] = (checks["source_saved"] and checks["source_complete"]["pass"]
                      and checks["closed"] and checks["completed"]
                      and all(checks[run]["pass"] for run in ("restore-a", "restore-b", "changed")))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--recount", type=Path, help="assess an existing output without launching")
    parser.add_argument("--legacy-raw-recount", action="store_true",
                        help="use the historical strict raw-reading rule; requires --recount")
    args = parser.parse_args()
    if args.legacy_raw_recount and not args.recount:
        parser.error("--legacy-raw-recount requires --recount")
    if args.recount:
        checks = assess(args.recount.resolve(), legacy_raw=args.legacy_raw_recount)
    else:
        output = args.output.resolve()
        output.mkdir(parents=True)
        plan = plans(output)
        write_json(output / "plans.json", plan)
        checkpoint.run(plan["source"], output / "source")
        record = checkpoint.saved(output / "source", plan["name"])
        try:
            for run, key in (("restore-a", "restore"), ("restore-b", "restore"),
                             ("changed", "changed")):
                checkpoint.run({**plan[key], "checkpoint": record}, output / run)
        finally:
            # Keep the checkpoint with the evidence, out of the game's Replays list.
            replay = runtime.user_dir() / "replays" / (plan["name"] + ".replay")
            shutil.move(replay, output / replay.name)
        checks = assess(output)
        write_json(output / "checks.json", checks)
    print(json.dumps(checks, indent=1))
    return 0 if checks["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
