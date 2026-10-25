-- Supplement to the land reading. Raw values at a completed native tick; no orders.
local function checked(value, kind, label)
    assert(type(value) == kind, label .. ': expected ' .. kind .. ', got ' .. type(value))
    if kind == 'number' then
        assert(value == value and math.abs(value) < 1/0, label .. ': non-finite number')
    end
    return value
end

local function ctx(expression, kind)
    local ok, value = pcall(common.get_context_value, 'CcoBattleRoot', '', expression)
    assert(ok, expression .. ': ' .. tostring(value))
    return checked(value, kind, expression)
end

-- Neutral points, empty vehicles and unused slots can have no owning army/occupant.
local function optional_context(expression)
    local ok, value = pcall(common.get_context_value, 'CcoBattleRoot', '', expression)
    if ok then return value end
end

local function count(expression)
    local size = ctx(expression .. '.Size', 'number')
    assert(size >= 0 and size == math.floor(size), expression .. ': invalid list size')
    return size
end

local function get(object, method, kind, ...)
    assert(object, method .. ': no object')
    local f = checked(object[method], 'function', method)
    local ok, value = pcall(f, object, ...)
    assert(ok, method .. ': ' .. tostring(value))
    return checked(value, kind, method)
end

local function position(object)
    return {x = get(object, 'get_x', 'number'), y = get(object, 'get_y', 'number'),
            z = get(object, 'get_z', 'number')}
end

local function context_position(expression)
    return {x = ctx(expression .. '.x', 'number'), y = ctx(expression .. '.y', 'number'),
            z = ctx(expression .. '.z', 'number')}
end

local captures = {}
for i = 0, count('CapturePointList') - 1 do
    local p = 'CapturePointList.At(' .. i .. ')'
    captures[#captures + 1] = {
        index = i, key = ctx(p .. '.Key', 'string'), script_id = ctx(p .. '.ScriptId', 'string'),
        name = ctx(p .. '.DisplayName', 'string'), position = context_position(p .. '.Position'),
        holder_alliance = ctx(p .. '.CurrentHolderAlliance', 'number'),
        original_alliance = ctx(p .. '.OriginalOwnerAlliance', 'number'),
        holder_army = optional_context(p .. '.HoldingArmyContext.UniqueID'),
        contesting_army = optional_context(p .. '.ContestingArmycontext.UniqueID'),
        capture_percent = ctx(p .. '.CapturePercent', 'number'),
        contested = ctx(p .. '.IsContested', 'boolean'), locked = ctx(p .. '.IsLocked', 'boolean'),
        enabled = ctx(p .. '.IsEnabled', 'boolean'), neutral = ctx(p .. '.IsNeutral', 'boolean'),
        victory = ctx(p .. '.ContributesToVictory', 'boolean'),
        owner_can_build = ctx(p .. '.CanCurrentOwnerBuild', 'boolean'),
    }
end

local function read_buildings(list, gates)
    local result = {}
    for i = 0, count(list) - 1 do
        local p = list .. '.At(' .. i .. ')'
        local row = {
            index = i, name = ctx(p .. '.Name', 'string'), category = ctx(p .. '.CategoryType', 'string'),
            position = context_position(p .. '.Position'),
            hp = ctx(p .. '.CurrentHitpoints', 'number'), max_hp = ctx(p .. '.MaxHitpoints', 'number'),
            damage_percent = ctx(p .. '.DamagePercent', 'number'),
            destroyed = ctx(p .. '.IsDestroyed', 'boolean'), enabled = ctx(p .. '.IsEnabled', 'boolean'),
            on_fire = ctx(p .. '.IsOnFire', 'boolean'), percent_on_fire = ctx(p .. '.PercentOnFire', 'number'),
            holder_army = optional_context(p .. '.HoldingArmyContext.UniqueID'),
            holder_alliance = optional_context(p .. '.HoldingAllianceContext.Id'),
        }
        if gates then
            row.gate_hp = ctx(p .. '.GateCurrentHitpoints', 'number')
            row.gate_max_hp = ctx(p .. '.GateMaxHitpoints', 'number')
            row.gate_damage_percent = ctx(p .. '.GateDamagePercent', 'number')
        end
        result[#result + 1] = row
    end
    return result
end

local vehicles = {}
for i = 0, count('VehicleList') - 1 do
    local p = 'VehicleList.At(' .. i .. ')'
    vehicles[#vehicles + 1] = {
        index = i, name = ctx(p .. '.Name', 'string'), category = ctx(p .. '.CategoryName', 'string'),
        position = context_position(p .. '.Position'), health_percent = ctx(p .. '.HealthPercent', 'number'),
        destroyed = ctx(p .. '.IsDestroyed', 'boolean'), percent_on_fire = ctx(p .. '.PercentOnFire', 'number'),
        army = optional_context(p .. '.ArmyContext.UniqueID'),
        alliance = optional_context(p .. '.ArmyContext.AllianceIndex'),
        occupant_type = optional_context(p .. '.UnitContext.UnitRecordContext.Key'),
    }
end

local armies = {}
for i = 0, count('ArmyList') - 1 do
    local a = 'ArmyList.At(' .. i .. ')'
    local list = 'ToggleableSlotList(' .. a .. ')'
    local slots = {}
    for j = 0, count(list) - 1 do
        local p = list .. '.At(' .. j .. ')'
        local options = {}
        for k = 0, count(p .. '.BuildablesList') - 1 do
            local b = p .. '.BuildablesList.At(' .. k .. ')'
            options[#options + 1] = {
                index = ctx(b .. '.Index', 'number'), destroyed = ctx(b .. '.IsDestroyed', 'boolean'),
                refund_value = ctx(b .. '.RefundValue', 'number'),
            }
        end
        slots[#slots + 1] = {
            index = j, type = ctx(p .. '.TypeString', 'string'),
            position = context_position(p .. '.WorldPosition'),
            current_index = ctx(p .. '.CurrentIndex', 'number'), enabled_index = ctx(p .. '.EnabledIndex', 'number'),
            any_enabled = ctx(p .. '.IsAnyEnabled', 'boolean'),
            constructing = ctx(p .. '.IsConstructionInProgress', 'boolean'),
            construction_s = ctx(p .. '.ConstructionTimeRemainingSeconds', 'number'),
            destroying = ctx(p .. '.IsDestructionInProgress', 'boolean'),
            destroyed = ctx(p .. '.IsDestroyed', 'boolean'),
            owner = optional_context(p .. '.CurrentBuildableOwner.UniqueID'),
            parent_capture_key = optional_context(p .. '.ParentCapturePointContext.Key'),
            parent_capture_position = {
                x = optional_context(p .. '.ParentCapturePointContext.Position.x'),
                z = optional_context(p .. '.ParentCapturePointContext.Position.z'),
            },
            options = options,
        }
    end
    armies[#armies + 1] = {
        index = i, id = ctx(a .. '.UniqueID', 'number'), alliance = ctx(a .. '.AllianceIndex', 'number'),
        supplies = ctx(a .. '.GlobalCurrency', 'number'), slots = slots,
    }
end

local assault, climbing = {}, {}
local equipment = bm.battle:assault_equipment()
for i = 1, get(equipment, 'vehicle_count', 'number') do
    local vehicle = equipment:vehicle_item(i)
    assault[#assault + 1] = {
        index = i, key = get(vehicle, 'vehicle_key', 'string'), position = position(vehicle:position()),
    }
end
local alliances = bm:alliances()
for side = 1, get(alliances, 'count', 'number') do
    local side_armies = alliances:item(side):armies()
    for army = 1, get(side_armies, 'count', 'number') do
        local units = side_armies:item(army):units()
        for i = 1, get(units, 'count', 'number') do
            local unit = units:item(i)
            climbing[#climbing + 1] = {
                side = side, army = army, index = i,
                id = get(unit, 'unique_ui_id', 'number'),
                climbing = get(unit, 'is_climbing_ladder', 'boolean'),
            }
        end
    end
end

return twwarhammer3_json.encode({
    time_ms = get(bm.battle, 'time_elapsed_ms', 'number'), captures = captures,
    gates = read_buildings('BuildingsList.Filter(IsGate)', true),
    field_buildings = read_buildings('BuildingsList.Filter(IsToggleable)', false),
    vehicles = vehicles, armies = armies, assault_equipment = assault, climbing = climbing,
    actions = checkpoint_siege_actions,
})
