-- Deterministic fixture: two field towers, then script-API ownership transfers.
-- Transfers establish held-by-different-armies states, not normal capture mechanics.
local attack_side = ATTACK_SIDE
local transfer_ownership = TRANSFER_OWNERSHIP
assert(attack_side == 1 or attack_side == 2, "expected one of two attacking alliances")
assert(type(transfer_ownership) == "boolean", "TRANSFER_OWNERSHIP must be a Lua boolean")
local local_side = bm:local_alliance()
local local_defender = local_side ~= attack_side
local attacker = bm:alliances():item(attack_side):armies():item(1)
local local_army = bm:alliances():item(local_side):armies():item(1)
checkpoint_siege_actions = {}

local function context(expression)
    return common.get_context_value("CcoBattleRoot", "", expression)
end

local function action(name, fn)
    local row = {event = name, ms = bm.battle:time_elapsed_ms()}
    checkpoint_siege_actions[#checkpoint_siege_actions + 1] = row
    local ok, err = pcall(fn, row)
    row.ok = ok
    if not ok then row.error = tostring(err) end
end

if local_defender then
    bm:callback(function()
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
    end, 10000, "checkpoint_siege_build_towers")


end

local function transfer(name, key_fragment)
    action(name, function(row)
        local selected
        for index = 0, context("CapturePointList.Size") - 1 do
            local point = "CapturePointList.At(" .. index .. ")"
            local key = context(point .. ".Key")
            if type(key) == "string" and string.find(key, key_fragment, 1) then
                selected = {key = key, x = context(point .. ".Position.x"),
                            z = context(point .. ".Position.z"),
                            script_id = context(point .. ".ScriptId")}
                break
            end
        end
        assert(selected, "capture-location type missing: " .. key_fragment)
        local locations = bm.battle:capture_location_manager()
        local found
        for index = 1, locations:count() do
            local location = locations:item(index)
            local position = location:position()
            if math.abs(position:get_x() - selected.x) < 0.01
                and math.abs(position:get_z() - selected.z) < 0.01 then
                assert(not found, "capture-location position is ambiguous")
                found = location
            end
        end
        assert(found, "capture location missing at " .. selected.x .. "," .. selected.z)
        assert(found:type() == selected.key, "wrong capture-location type " .. found:type())
        local owner = found:holding_army()
        row.type = found:type()
        row.id, row.script_id = found:unique_id(), selected.script_id
        row.x, row.z = selected.x, selected.z
        row.owner_before = owner and owner:unique_id() or nil
        row.alliance_before = found:holding_alliance_id()
        found:change_holding_army(attacker)
        owner = found:holding_army()
        row.owner_after = owner and owner:unique_id() or nil
        row.alliance_after = found:holding_alliance_id()
        row.requested_owner = attacker:unique_id()
    end)
end

if transfer_ownership then
    bm:callback(function()
        transfer("transfer_minor_supply", "minor_point_supplies")
    end, 90000, "checkpoint_siege_transfer_minor")
    bm:callback(function()
        transfer("transfer_key_building", "major_key_building")
    end, 180000, "checkpoint_siege_transfer_key")
end

return twwarhammer3_json.encode({installed = true, attack_side = attack_side,
    local_side = local_side, local_defender = local_defender,
    transfer_ownership = transfer_ownership,
    ms = bm.battle:time_elapsed_ms()})
