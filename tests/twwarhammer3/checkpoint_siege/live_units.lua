-- Add direct numeric readings while retaining the original infocard stats and morale text.
-- Walk/run speeds are unit capabilities, not instantaneous movement velocity.
-- `battle` is the decoded land reading; the simulation has not advanced between these calls.
local function get(object, method, ...)
    local f = object and object[method]
    if not f then return nil end
    local ok, value = pcall(f, object, ...)
    if ok then return value end
end

for _, record in ipairs(battle.units) do
    local ok, unit = pcall(function()
        return bm:alliances():item(record.side):armies():item(1):units():item(record.index)
    end)
    if ok and unit then
        assert(tostring(get(unit, 'unique_ui_id')) == record.id, 'unit UI id changed while reading')
        record.slow_speed = get(unit, 'slow_speed')
        record.fast_speed = get(unit, 'fast_speed')
        local read, morale = pcall(common.get_context_value, 'CcoBattleUnit', record.id, 'MoralePercent')
        if read then record.morale_percent = morale end
    end
end
