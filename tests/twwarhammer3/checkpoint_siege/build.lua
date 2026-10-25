-- Source-only construction input: restorations must rebuild it from the recorded replay.
local local_army = bm:alliances():item(bm:local_alliance()):armies():item(1)
local actions = {}

local function context(expression)
    return common.get_context_value("CcoBattleRoot", "", expression)
end

assert(context("SetupContext.IsPlayerAttacker") == false, "local defender required")

local function action(name, fn)
    local row = {event = name, ms = bm.battle:time_elapsed_ms()}
    actions[#actions + 1] = row
    local ok, err = pcall(fn, row)
    row.ok = ok
    if not ok then row.error = tostring(err) end
end

for index = 0, 1 do
    action("build_tower", function(row)
        local towers = 'ToggleableSlotList(PlayerArmyContext).Filter(TypeString == "tower")'
        assert(context(towers .. ".Size") >= 2, "two tower slots required")
        local slot = towers .. ".At(" .. index .. ")"
        local buildable = slot .. ".BuildablesList.FirstContext(Index == " .. index .. ")"
        assert(context(slot .. ".BuildablesList.Count(Index == " .. index .. ")") == 1,
               "requested tower option missing")
        row.slot = index
        row.option = index
        row.x = context(slot .. ".WorldPosition.x")
        row.z = context(slot .. ".WorldPosition.z")
        row.supplies_before = context("PlayerArmyContext.GlobalCurrency")
        row.index_before = context(slot .. ".CurrentIndex")
        row.cost = context(buildable .. ".Cost(" .. local_army:unique_id() .. ")")
        assert(row.index_before == -1, "tower slot already occupied")
        -- The game's radial-menu PrimaryAction uses an expression with effects.
        context(buildable .. ".PrimaryAction")
        row.supplies_after = context("PlayerArmyContext.GlobalCurrency")
        row.index_after = context(slot .. ".CurrentIndex")
        row.constructing = context(slot .. ".IsConstructionInProgress")
        row.remaining_s = context(slot .. ".ConstructionTimeRemainingSeconds")
    end)
end

return twwarhammer3_json.encode({actions = actions})
