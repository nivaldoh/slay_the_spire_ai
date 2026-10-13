-- twwarhammer3_ui.lua: UI component steps shared by the frontend and battle scripts.
--
-- The mod loader runs every script/_lib/mod/*.lua before the frontend or battle mods, so
-- they find this table as the global twwarhammer3_ui. A step finds a component by its id
-- path from the UI root and acts on it, or dumps part of the tree to a file in the bridge.

twwarhammer3_ui = {}
local ui = twwarhammer3_ui

-- Visible itself and through every ancestor, when the game offers the check.
function ui.visible(uic)
    local ok, value = pcall(function() return uic:VisibleFromRoot() end)
    if ok then return value end
    return uic:Visible()
end

function ui.find(path)
    return find_uicomponent(core:get_ui_root(), unpack(path))
end

local function dump(uic, depth, max_depth, lines)
    local visible = uic:Visible() and "" or " [hidden]"
    lines[#lines + 1] = string.rep("  ", depth) .. tostring(uic:Id()) .. visible
        .. " <" .. tostring(uic:CurrentState()) .. ">"
    if depth >= max_depth then return end
    for index = 0, uic:ChildCount() - 1 do
        dump(UIComponent(uic:Find(index)), depth + 1, max_depth, lines)
    end
end

-- {"dump": "file.txt", "depth": N, "find": [...]?}: the tree under the root or a component.
function ui.dump(step, directory)
    local root = core:get_ui_root()
    if step.find then
        root = ui.find(step.find)
        if not root then return "dump root not found" end
    end
    local lines = {}
    dump(root, 0, step.depth or 4, lines)
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

-- One step that needs no waiting: dump, key, find (once) or log.
function ui.run(step, directory)
    if step.log then
        return "log " .. tostring(step.log)
    elseif step.dump then
        return ui.dump(step, directory)
    elseif step.key then
        core:get_ui_root():SimulateKey(step.key)
        return "key " .. step.key
    elseif step.find then
        local uic = ui.find(step.find)
        if not uic then return "not found: " .. table.concat(step.find, "/") end
        return ui.act(uic, step)
    end
    return "unknown step"
end
