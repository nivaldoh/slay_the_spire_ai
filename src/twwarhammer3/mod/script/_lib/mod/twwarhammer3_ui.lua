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
        if not root then return "dump root not found" end
    end
    local lines = {}
    dump(root, 0, step.depth or 4, lines, step.context)
    local file = io.open(directory .. step.dump, "w")
    if not file then return "cannot write " .. step.dump end
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

-- One step that needs no waiting: dump, key, find (once), log, advisor text ("" closes
-- it), an expression on a context object ({"context": "CcoBattleUnit", "id": "...",
-- "expression": "..."}), a context command ({"context": ..., "command": "..."}) or, for
-- probing the script API, a Lua chunk whose return value is logged ({"lua": "return ..."}).
function ui.run(step, directory)
    if step.log then
        return "log " .. tostring(step.log)
    elseif step.advice == "" then
        bm:close_advisor()
        return "advisor closed"
    elseif step.advice then
        common.advice(step.advice)
        return "advice shown"
    elseif step.lua then
        local chunk, err = loadstring(step.lua)
        if not chunk then return "lua: " .. tostring(err) end
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
            if step.required then error(message) end
            return message
        end
        return ui.act(uic, step)
    end
    return "unknown step"
end
