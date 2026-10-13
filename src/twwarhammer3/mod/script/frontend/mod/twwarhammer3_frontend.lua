-- twwarhammer3_frontend.lua: drives the main menu from C:/wh3-agent/bridge/menu.json.
--
-- Loaded by the vanilla mod loader from script/frontend/mod/ when the frontend starts.
-- Inert unless session.json has "menu": true. Then it polls menu.json; each step is one
-- of {"find": [names...], "click": true}, {"find": [...], "state": "name"}, {"key": "name"},
-- {"dump": "file.txt", "depth": N}, {"wait_ms": N} or {"log": "text"}. Results go to
-- menu.log; the file is deleted when read and "done" is logged after the last step.

local BRIDGE = "C:/wh3-agent/bridge/"
local json = twwarhammer3_json
local POLL_MS = 500

local function read_file(path)
    local file = io.open(path, "r")
    if not file then return nil end
    local text = file:read("*a")
    file:close()
    return text
end

local function read_json(path)
    local text = read_file(path)
    if not text or text == "" then return nil end
    local ok, value = pcall(json.decode, text)
    if ok and type(value) == "table" then return value end
    return nil
end

local function log(text)
    local file = io.open(BRIDGE .. "menu.log", "a")
    if file then
        file:write(tostring(text) .. "\n")
        file:close()
    end
end

local function clean_error(err)
    err = tostring(err)
    return string.match(err, ":%d+: (.*)$") or err
end

local function dump(uic, depth, max_depth, lines)
    local id = tostring(uic:Id())
    local visible = uic:Visible() and "" or " [hidden]"
    lines[#lines + 1] = string.rep("  ", depth) .. id .. visible .. " <" .. tostring(uic:CurrentState()) .. ">"
    if depth >= max_depth then return end
    for index = 0, uic:ChildCount() - 1 do
        dump(UIComponent(uic:Find(index)), depth + 1, max_depth, lines)
    end
end

local state = {steps = nil, index = 0, wait_polls = 0}

local function run_step(step)
    if step.wait_ms then
        state.wait_polls = math.ceil(step.wait_ms / POLL_MS)
        return "wait " .. step.wait_ms .. " ms"
    elseif step.log then
        return "log " .. tostring(step.log)
    elseif step.dump then
        local lines = {}
        local root = core:get_ui_root()
        if step.find then
            root = find_uicomponent(root, unpack(step.find))
            if not root then return "dump root not found" end
        end
        dump(root, 0, step.depth or 4, lines)
        local file = io.open(BRIDGE .. step.dump, "w")
        if not file then return "cannot write " .. step.dump end
        file:write(table.concat(lines, "\n") .. "\n")
        file:close()
        return "dumped " .. #lines .. " lines to " .. step.dump
    elseif step.key then
        core:get_ui_root():SimulateKey(step.key)
        return "key " .. step.key
    elseif step.find then
        local uic = find_uicomponent(core:get_ui_root(), unpack(step.find))
        if not uic then return "not found: " .. table.concat(step.find, "/") end
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
        return table.concat(done, ", ")
    end
    return "unknown step"
end

local function poll()
    if not state.steps then
        local text = read_file(BRIDGE .. "menu.json")
        if not text then return end
        os.remove(BRIDGE .. "menu.json")
        local ok, message = pcall(json.decode, text)
        if not ok or type(message) ~= "table" or type(message.steps) ~= "table" then
            log("menu.json unreadable; dropped")
            return
        end
        state.steps, state.index, state.wait_polls = message.steps, 0, 0
        log(string.format("menu: %d steps", #state.steps))
        return
    end
    if state.wait_polls > 0 then
        state.wait_polls = state.wait_polls - 1
        return
    end
    state.index = state.index + 1
    local step = state.steps[state.index]
    if not step then
        log("done")
        state.steps = nil
        return
    end
    local ok, result = pcall(run_step, step)
    log(string.format("step %d: %s", state.index, ok and tostring(result) or ("failed: " .. clean_error(result))))
end

local function load()
    local session = read_json(BRIDGE .. "session.json")
    if not session or not session.menu then return end
    log("frontend loaded for job " .. tostring(session.job))
    tm:repeat_real_callback(function()
        local ok, err = pcall(poll)
        if not ok then log("poll failed: " .. clean_error(err)) end
    end, POLL_MS, "twwarhammer3_menu")
end

local ok, err = pcall(load)
if not ok then log("load failed: " .. clean_error(err)) end
