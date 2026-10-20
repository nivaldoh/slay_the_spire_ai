-- twwarhammer3_ui.lua: UI component steps shared by the frontend and battle scripts.
--
-- The mod loader runs every script/_lib/mod/*.lua before the frontend or battle mods, so
-- they find this table as the global twwarhammer3_ui. A step finds a component by its id
-- path from the UI root and acts on it, or dumps part of the tree to a file in the bridge.

twwarhammer3_ui = {}
local ui = twwarhammer3_ui

function ui.find(path)
    return find_uicomponent(core:get_ui_root(), unpack(path))
end

local function dump(uic, depth, max_depth, lines, context)
    local visible = uic:Visible() and "" or " [hidden]"
    local line = string.rep("  ", depth) .. tostring(uic:Id()) .. visible
        .. " <" .. tostring(uic:CurrentState()) .. ">"
    if context then
        local ok, id = pcall(function() return uic:GetContextObjectId(context) end)
        if ok and id and id ~= "" then line = line .. " {" .. tostring(id) .. "}" end
    end
    local ok, text = pcall(function() return uic:GetStateText() end)
    if ok and type(text) == "string" and text ~= "" then
        line = line .. ' "' .. string.gsub(text, "\n", " / ") .. '"'
    end
    lines[#lines + 1] = line
    if depth >= max_depth then return end
    for index = 0, uic:ChildCount() - 1 do
        dump(UIComponent(uic:Find(index)), depth + 1, max_depth, lines, context)
    end
end

-- {"dump": "file.txt", "depth": N, "find": [...]?, "context": type?}: the tree under the
-- root or a component, with each component's context object id of that type.
function ui.dump(step, directory)
    local root = core:get_ui_root()
    if step.find then
        root = ui.find(step.find)
        assert(root, "dump root not found")
    end
    local lines = {}
    dump(root, 0, step.depth or 4, lines, step.context)
    local file = io.open(directory .. step.dump, "w")
    assert(file, "cannot write " .. step.dump)
    file:write(table.concat(lines, "\n") .. "\n")
    file:close()
    return "dumped " .. #lines .. " lines to " .. step.dump
end

-- The actions of a find step on a found component: visible, state, click, dblclick, rclick.
function ui.act(uic, step)
    local done = {"found " .. table.concat(step.find, "/")}
    if step.visible ~= nil then
        uic:SetVisible(step.visible)
        done[#done + 1] = "visible=" .. tostring(step.visible)
    end
    if step.state then
        uic:SetState(step.state)
        done[#done + 1] = "state=" .. step.state
    end
    if step.click then
        uic:SimulateLClick()
        done[#done + 1] = "clicked"
    end
    if step.dblclick then
        uic:SimulateDblLClick()
        done[#done + 1] = "double-clicked"
    end
    if step.rclick then
        uic:SimulateRClick()
        done[#done + 1] = "right-clicked"
    end
    return table.concat(done, ", ")
end

-- Set a recruited unit's rank through the same commands as its +/- buttons. Read after
-- each command: insufficient funds or a unit that cannot gain XP must fail setup.
function ui.experience(step)
    local counts = {}
    -- Recruitment sorts by class. Apply ranks only after the entire army is recruited,
    -- matching by type and occurrence. Rank changes do not reorder this lobby list.
    for _, wanted in ipairs(step.experience) do
        assert(type(wanted.rank) == "number" and wanted.rank % 1 == 0
            and wanted.rank >= 0 and wanted.rank <= 9, "experience must be an integer from 0 to 9")
        local count = counts[wanted.type] or 0
        local prefix = "CustomBattleLobbyContext.PlayerSlotList.At(" .. step.slot
            .. ").UnitList.Filter(UnitRecordContext.Key == " .. twwarhammer3_json.encode(wanted.type)
            .. ").At(" .. count .. ")."
        local function rank()
            return common.get_context_value("CcoFrontendRoot", "", prefix .. "ExperienceLevel")
        end
        local current = rank()
        assert(type(current) == "number", "unit experience unavailable: " .. wanted.type)
        local delta = wanted.rank > current and 1 or -1
        local command = delta == 1 and "IncreaseExperience()" or "DecreaseExperience()"
        for _ = 1, math.abs(wanted.rank - current) do
            common.call_context_command("CcoFrontendRoot", "", prefix .. command)
            assert(rank() == current + delta, "experience did not change for " .. wanted.type
                .. " from " .. current .. " to " .. (current + delta))
            current = current + delta
        end
        counts[wanted.type] = count + 1
    end
    return "experience set for slot " .. step.slot .. ": " .. #step.experience .. " units"
end

-- Use the lobby's recruitment permissions and its separate cost-label funds check.
-- Mount before assigning XP; matching rank-zero duplicates are interchangeable.
function ui.recruit(step)
    local encode = twwarhammer3_json.encode
    local slot = "CustomBattleLobbyContext.PlayerSlotList.At(" .. step.slot .. ")."
    local unit = "DatabaseRecordContext(\"CcoMainUnitRecord\", " .. encode(step.recruit) .. ")"
    local permission = unit .. ".CustomBattlePermissionsContext("
        .. "DatabaseRecordContext(\"CcoFactionRecord\", " .. encode(step.faction) .. "))"
    local reserve = step.reinforcements == true and "true" or "false"
    local pool = slot .. (step.reinforcements == true and "ReinforcingUnitList" or "UnitList")
    local function value(expression)
        return common.get_context_value("CcoFrontendRoot", "", expression)
    end
    local function command(expression)
        common.call_context_command("CcoFrontendRoot", "", expression)
    end
    if value(slot .. "CanRecruitUnit(" .. unit .. ", " .. reserve .. ")") ~= true then
        error("cannot recruit " .. step.recruit .. " in slot " .. step.slot .. ": "
              .. tostring(value(slot .. "TooltipForUnit(" .. unit .. ", " .. reserve .. ")")))
    end
    local main_funds = step.reinforcements ~= true or value(permission .. ".IsGeneralUnit") == true
    local remaining = value(slot .. "FundsRemaining(" .. tostring(main_funds) .. ")")
    local cost = value(unit .. ".Cost")
    assert(type(remaining) == "number" and type(cost) == "number", "recruitment funds unavailable")
    assert(cost <= remaining, "insufficient funds for " .. step.recruit
        .. ": cost " .. cost .. ", remaining " .. remaining)
    local count = value(pool .. ".Size")
    command(slot .. "RecruitUnit(" .. permission .. ", " .. reserve .. ")")
    assert(value(pool .. ".Size") == count + 1, "recruitment did not add " .. step.recruit)
    if step.mount then
        local original = pool .. ".Count(UnitRecordContext.Key == " .. encode(step.recruit) .. ")"
        local mounted = pool .. ".Count(UnitRecordContext.Key == " .. encode(step.mount) .. ")"
        local before, after = value(original), value(mounted)
        local selected = pool .. ".FirstContext(UnitRecordContext.Key == " .. encode(step.recruit) .. ")."
        command(selected .. "ChangeMount(" .. selected
            .. "AvailableMountsList.FirstContext(MountedUnitContext.Key == " .. encode(step.mount) .. "))")
        assert(value(original) == before - 1 and value(mounted) == after + 1,
               "mount did not change " .. step.recruit .. " to " .. step.mount)
    end
    return "recruited " .. step.recruit .. " in slot " .. step.slot
end

-- One immediate step: recruit (unit key, slot, faction, optional mount/reinforcements),
-- experience (final types/ranks and slot), dump, key, find (once), log, advisor text ("" closes
-- it), an expression on a context object ({"context": "CcoBattleUnit", "id": "...",
-- "expression": "..."}), a context command ({"context": ..., "command": "..."}) or, for
-- probing the script API, a Lua chunk whose return value is logged ({"lua": "return ..."}).
function ui.run(step, directory)
    if step.recruit then
        return ui.recruit(step)
    elseif step.experience ~= nil then
        return ui.experience(step)
    elseif step.log then
        return "log " .. tostring(step.log)
    elseif step.advice == "" then
        bm:close_advisor()
        return "advisor closed"
    elseif step.advice then
        common.advice(step.advice)
        return "advice shown"
    elseif step.lua then
        local chunk, err = loadstring(step.lua)
        assert(chunk, "lua: " .. tostring(err))
        setfenv(chunk, getfenv(1))  -- the mod's environment, where bm and core live
        return "lua = " .. tostring(chunk())
    elseif step.command then
        common.call_context_command(step.context, step.id or "", step.command)
        return "command " .. step.command
    elseif step.expression then
        local value = common.get_context_value(step.context, step.id or "", step.expression)
        local matches = value == step.expect
        if type(value) == "number" and type(step.expect) == "number" then
            matches = math.abs(value - step.expect) < 0.000001
        end
        if step.expect ~= nil and not matches then
            error(step.expression .. " = " .. tostring(value) .. ", expected " .. tostring(step.expect))
        end
        return step.expression .. " = " .. tostring(value)
    elseif step.dump then
        return ui.dump(step, directory)
    elseif step.key then
        core:get_ui_root():SimulateKey(step.key)
        return "key " .. step.key
    elseif step.find then
        local uic = ui.find(step.find)
        if not uic then
            local message = "not found: " .. table.concat(step.find, "/")
            error(message)
        end
        return ui.act(uic, step)
    end
    error("unknown step")
end
