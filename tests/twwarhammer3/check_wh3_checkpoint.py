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
Recount saved evidence without launching: --recount EXISTING_OUTPUT.
"""
import argparse
import json
import sys
from pathlib import Path

from gameai.provenance import write_json
from twwarhammer3.battle import checkpoint

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
READING = r'''
local function get(obj, name, ...)
  local f = obj and obj[name]; if not f then return nil end
  local ok, value = pcall(f, obj, ...); if ok then return value end
end
local function ctx(id, expression)
  local ok, value = pcall(function()
    return common.get_context_value("CcoBattleUnit", id, expression) end)
  if ok then return value end
end
local ABILITIES = 'BattleAbilityList.JoinString(SetupAbilityContext.RecordKey + "|" + '
  .. 'CanCurrentlyPerform + "|" + RechargeTimeRemainingSecs + "|" + IsActive, ";")'
local units = {}
for side = 1, 2 do
  local list = bm:alliances():item(side):armies():item(1):units()
  for i = 1, list:count() do
    local u = list:item(i); local id = tostring(get(u, "unique_ui_id"))
    local p, d = get(u, "position"), get(u, "ordered_position")
    local target = get(u, "current_target")
    units[#units + 1] = {side = side, id = id, type = get(u, "type"),
      x = p and p:get_x(), z = p and p:get_z(), bearing = get(u, "bearing"),
      width = get(u, "ordered_width"), dest_x = d and d:get_x(), dest_z = d and d:get_z(),
      men = get(u, "number_of_men_alive"), hp = get(u, "unary_hitpoints"),
      ammo = get(u, "ammo_left"),
      kills = get(u, "number_of_enemies_killed"), fatigue = tostring(get(u, "fatigue_state")),
      target = target and tostring(get(target, "unique_ui_id")) or nil,
      morale = ctx(id, 'MoralePercent + "|" + MoraleGreatestEffect'),
      abilities = ctx(id, ABILITIES),
      fire_at_will = get(u, "is_behaviour_active", "fire_at_will"), moving = get(u, "is_moving"),
      melee = get(u, "is_in_melee"), routing = get(u, "is_routing"),
      wavering = get(u, "is_wavering")}
  end
end
local s = checkpoint_script
return twwarhammer3_json.encode({time_ms = bm.battle:time_elapsed_ms(),
  remaining_s = bm.battle:remaining_conflict_time(), phase = bm:get_current_phase_name(),
  units = units,
  script = s and {fires = s.fires, times = s.times, draws = s.draws, orders = s.orders} or nil})
'''


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
    readings = {"every": 100, "lua": READING}
    setup_lua = [{"tick": 1, "label": "battle_script", "lua": SCRIPT}]
    source = {"scenario": SCENARIO, "save_at": [{"tick": CHECKPOINT, "name": name}],
              "lua_at": setup_lua + BEFORE + AFTER, "readings": readings, "stop_tick": STOP}
    restore = {"lua_at": setup_lua + AFTER, "readings": readings, "stop_tick": STOP}
    return {"name": name, "source": source, "restore": restore,
            "changed": {**restore, "lua_at": setup_lua + CHANGED}}


def assess(output: Path) -> dict:
    source = checkpoint.events(output / "source")
    checks = {"source_saved": any(e.get("event") == "saved" and e["tick"] == CHECKPOINT
                                  for e in source)}
    for run in ("restore-a", "restore-b", "changed"):
        result = checkpoint.compare(source, checkpoint.events(output / run))
        checks[run] = result
        restored = result["restored_at"] == CHECKPOINT and result["seed_matches"] is True
        if run == "changed":
            result["pass"] = (restored and result["checksum_mismatches"] > 0
                              and result["first_mismatch"] > CHANGED_TICK
                              and bool(result["readings_unequal"]))
        else:
            result["pass"] = (restored and (result["last_tick"] or 0) >= STOP
                              and result["checksum_mismatches"] == 0 and result["readings"] >= 8
                              and not result["readings_unequal"])
    checks["closed"] = all(json.loads((output / run / "manifest.json").read_text()).get("closed")
                           for run in ("source", "restore-a", "restore-b", "changed"))
    checks["pass"] = (checks["source_saved"] and checks["closed"]
                      and all(checks[run]["pass"] for run in ("restore-a", "restore-b", "changed")))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--recount", type=Path, help="assess an existing output without launching")
    args = parser.parse_args()
    if args.recount:
        checks = assess(args.recount.resolve())
    else:
        output = args.output.resolve()
        output.mkdir(parents=True)
        plan = plans(output)
        write_json(output / "plans.json", plan)
        checkpoint.run(plan["source"], output / "source")
        record = checkpoint.saved(output / "source", plan["name"])
        for run, key in (("restore-a", "restore"), ("restore-b", "restore"),
                         ("changed", "changed")):
            checkpoint.run({**plan[key], "checkpoint": record}, output / run)
        checks = assess(output)
        write_json(output / "checks.json", checks)
    print(json.dumps(checks, indent=1))
    return 0 if checks["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
