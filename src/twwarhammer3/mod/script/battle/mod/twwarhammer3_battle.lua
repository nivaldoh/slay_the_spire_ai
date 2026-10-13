-- twwarhammer3_battle.lua: the in-game side of the twwarhammer3 harness (Lua 5.1).
--
-- The vanilla mod loader runs this file from script/battle/mod/ when a battle's script
-- libraries load, after `bm` exists. It stays inert unless C:/wh3-agent/bridge/session.json
-- enables it. Then it publishes observation.json on model time, polls orders.json on UI
-- time (so pause mode keeps listening), applies orders through one unit controller per
-- friendly unit, and reports the result. engine/mailbox.py documents the messages.

local BRIDGE = "C:/wh3-agent/bridge/"
local REMATCH = {"in_battle_results_popup", "button_rematch"}
local CONFIRM = {"dialogue_box", "both_group", "button_tick"}
local json = twwarhammer3_json
local ui = twwarhammer3_ui

local state = {
    battle = nil, seq = 0, started = false, finished = false, result = nil,
    friendly = {}, friendly_ids = {}, enemy = {}, enemy_ids = {}, enemy_by_ui = {},
    pending = nil, last_request = nil, applied = nil, applied_ms = nil,
    paused = false, next_observe_ms = 0, force_observe = false, alliance = nil,
}
local session = nil

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

local function battle_time()
    local ok, value = pcall(function() return bm.battle:time_elapsed_ms() end)
    return ok and value or 0
end

local function log(text)
    local file = io.open(BRIDGE .. "mod.log", "a")
    if file then
        file:write(string.format("[%d] %s\n", battle_time(), tostring(text)))
        file:close()
    end
end

local function publish(name, value)
    local ok, text = pcall(json.encode, value)
    if not ok then log("encode failed: " .. tostring(text)); return false end
    local target, temporary = BRIDGE .. name, BRIDGE .. name .. ".tmp"
    local file = io.open(temporary, "w")
    if not file then log("cannot write " .. temporary); return false end
    file:write(text)
    file:close()
    os.remove(target)
    local renamed, err = os.rename(temporary, target)
    if not renamed then log("rename failed: " .. tostring(err)); return false end
    return true
end

local function clean_error(err)
    err = tostring(err)
    return string.match(err, ":%d+: (.*)$") or err
end

local function guarded(name, fn)
    return function(...)
        local ok, err = pcall(fn, ...)
        if not ok then log(name .. " failed: " .. clean_error(err)) end
    end
end

-- Engine queries, each isolated: a missing or failing method yields `default`.
local function get(object, method, default, ...)
    local ok, value = pcall(function(...) return object[method](object, ...) end, ...)
    if ok and value ~= nil then return value end
    return default
end

local function round(value, digits)
    if type(value) ~= "number" or value ~= value or value == (1 / 0) or value == -(1 / 0) then
        return nil
    end
    local scale = 10 ^ (digits or 0)
    return math.floor(value * scale + 0.5) / scale
end

-- From the land_units class (inf_mel, inf_mis, cav_shk, cav_mis, art_fld, mon, com, ...);
-- the is_* flags missed missile cavalry and war machines.
local CLASSES = {
    inf = "infantry", cav = "cavalry", chariot = "chariot", art = "artillery",
    mon = "monster", elph = "monster", com = "hero",
}

local function unit_class(unit)
    if get(unit, "is_commanding_unit", false) then return "lord" end
    local land_class = tostring(get(unit, "unit_class", ""))
    local class = CLASSES[string.match(land_class, "^(%a+)") or ""]
    if (not class or class == "monster") and get(unit, "can_fly", false) then return "flying" end
    if not class then return land_class ~= "" and land_class or "monster" end
    if (get(unit, "missile_range", 0) or 0) > 0 then
        if class == "infantry" then return "missile" end
        if class == "cavalry" or class == "chariot" then return "missile_" .. class end
    end
    return class
end

local function unit_record(id, unit, mine, class)
    local position = get(unit, "position", nil)
    local record = {
        id = id, type = get(unit, "type", "?"), class = class,
        commander = get(unit, "is_commanding_unit", false),
        x = position and round(position:get_x(), 1), z = position and round(position:get_z(), 1),
        bearing = round(get(unit, "bearing", 0)),
        men = get(unit, "number_of_men_alive", 0), men0 = get(unit, "initial_number_of_men", 0),
        hp = round(get(unit, "unary_hitpoints", 0), 2), state = {},
    }
    local flags = {
        {"is_routing", "routing"}, {"is_shattered", "shattered"}, {"is_wavering", "wavering"},
        {"is_in_melee", "melee"}, {"is_under_missile_attack", "under_fire"},
        {"is_moving", "moving"}, {"is_idle", "idle"},
        {"is_hidden", "hidden"}, {"is_unstable", "unstable"}, {"is_crumbling", "crumbling"},
        {"is_rampaging", "rampaging"},
    }
    for _, flag in ipairs(flags) do
        if get(unit, flag[1], false) then record.state[#record.state + 1] = flag[2] end
    end
    -- is_moving_fast follows the run setting, also while the unit stands.
    if get(unit, "is_moving", false) and get(unit, "is_moving_fast", false) then
        record.state[#record.state + 1] = "running"
    end
    record.range = round(get(unit, "missile_range", 0))
    if mine then
        record.ammo = get(unit, "ammo_left", 0)
        record.ammo0 = get(unit, "starting_ammo", 0)
        record.speed = {round(get(unit, "slow_speed", 0), 1), round(get(unit, "fast_speed", 0), 1)}
        record.fatigue = string.gsub(tostring(get(unit, "fatigue_state", "")), "^threshold_", "")
        local target = get(unit, "current_target", nil)
        if target then record.target = state.enemy_by_ui[get(target, "unique_ui_id", -1)] end
        -- ordered_position is the unit's own position while it attacks.
        local destination = get(unit, "ordered_position", nil)
        if destination and state.friendly[id].order == "move" and get(unit, "is_moving", false) then
            record.dest = {round(destination:get_x(), 1), round(destination:get_z(), 1)}
        end
    end
    return record
end

-- Line of sight (is_visible_to_alliance) and concealment in grass or trees (is_hidden) are
-- separate tests; an enemy is shown only when it passes both.
local function visible_to_player(unit)
    if get(unit, "is_hidden", false) then return false end
    local ok, visible = pcall(function() return unit:is_visible_to_alliance(state.alliance) end)
    return ok and visible == true
end

local function observation(now, awaiting)
    state.seq = state.seq + 1
    local friendly, enemy, roster = {}, {}, {}
    for _, id in ipairs(state.friendly_ids) do
        local entry = state.friendly[id]
        local ok, record = pcall(unit_record, id, entry.unit, true, entry.class)
        friendly[#friendly + 1] = ok and record or {id = id, error = clean_error(record)}
    end
    for _, id in ipairs(state.enemy_ids) do
        local entry = state.enemy[id]
        local alive = get(entry.unit, "number_of_men_alive", 0) > 0
        -- A unit's destruction is reported only once the player has seen the unit.
        roster[#roster + 1] = {id = id, type = get(entry.unit, "type", "?"),
                               dead = (entry.seen and not alive) or nil}
        if alive and visible_to_player(entry.unit) then
            entry.seen = true
            local ok, record = pcall(unit_record, id, entry.unit, false, entry.class)
            enemy[#enemy + 1] = ok and record or {id = id, error = clean_error(record)}
        end
    end
    local remaining = get(bm.battle, "remaining_conflict_time", -1)
    return {
        schema = 1, job = session.job, battle = state.battle, seq = state.seq,
        phase = bm:get_current_phase_name(), time_ms = now, speed = session.speed or 1,
        awaiting_orders = awaiting, remaining_ms = remaining >= 0 and remaining * 1000 or -1,
        armies = {
            player = {faction = get(bm:get_player_army(), "faction_key", "?")},
            enemy = {faction = get(bm:get_first_non_player_army(), "faction_key", "?")},
        },
        friendly = friendly, enemy_roster = roster, enemy = enemy,
        orders = state.applied, result = state.result, final = state.final,
    }
end

local function publish_observation(now, awaiting)
    local ok, message = pcall(observation, now, awaiting)
    if not ok then log("observation failed: " .. clean_error(message)); return false end
    return publish("observation.json", message)
end

local function vector(x, y, z)
    if type(v) == "function" then return v(x, y, z) end
    return battle_vector:new(x, y, z)
end

local function apply_order(order)
    local entry = state.friendly[order.unit]
    if not entry then return {unit = order.unit, ok = false, error = "unknown_unit"} end
    if not state.started then return {unit = order.unit, ok = false, error = "deployment"} end
    local unit, controller = entry.unit, entry.controller
    local ok, err = pcall(function()
        if get(unit, "number_of_men_alive", 0) == 0 then error("unit_dead") end
        if get(unit, "is_routing", false) or get(unit, "is_shattered", false) then
            error("unit_routing")
        end
        if order.type == "move" then
            local x, z = tonumber(order.x), tonumber(order.z)
            if not x or not z then error("bad_position") end
            local y = get(bm.battle, "get_terrain_height", 0, x, z)
            local destination = vector(x, y, z)
            if not get(unit, "can_reach_position", true, destination) then error("unreachable") end
            local facing = tonumber(order.facing)
            if facing then
                local width = get(unit, "ordered_width", 0)
                controller:goto_location_angle_width(destination, facing,
                                                     width > 0 and width or 40, order.run == true)
            else
                controller:goto_location(destination, order.run == true)
            end
        elseif order.type == "attack" then
            local target = state.enemy[order.target]
            if not target then error("unknown_target") end
            if get(target.unit, "number_of_men_alive", 0) == 0 then error("target_dead") end
            if not visible_to_player(target.unit) then error("target_not_visible") end
            controller:attack_unit(target.unit, true, order.run == true)
        elseif order.type == "halt" then
            controller:halt()
        else
            error("unknown_type")
        end
    end)
    if ok then
        entry.order = order.type
        return {unit = order.unit, ok = true}
    end
    return {unit = order.unit, ok = false, error = clean_error(err)}
end

local function apply_pending(now)
    local message = state.pending
    state.pending = nil
    local results = {}
    for _, order in ipairs(message.orders or {}) do
        results[#results + 1] = apply_order(order)
    end
    state.applied = {
        request = message.request, based_on = message.based_on, applied_ms = now, results = results,
    }
    state.applied_ms = now
    state.force_observe = true
    log(string.format("applied %s (%d orders)", tostring(message.request), #results))
end

local function try_end_deployment()
    local ok, err = pcall(function() bm.battle:end_current_battle_phase() end)
    log("end_current_battle_phase: " .. (ok and "ok" or clean_error(err)))
    if ok then return end
    local clicked, err2 = pcall(function()
        local button = find_uicomponent(core:get_ui_root(), "button_battle_start")
        if not button then error("button_battle_start not found") end
        button:SimulateLClick()
    end)
    log("start button click: " .. (clicked and "ok" or clean_error(err2)))
end

-- True strength of one side, alive and at the start, over every unit seen or not.
local function strength(entries)
    local men, men0 = 0, 0
    for _, entry in pairs(entries) do
        men = men + get(entry.unit, "number_of_men_alive", 0)
        men0 = men0 + get(entry.unit, "initial_number_of_men", 0)
    end
    return {men = men, men0 = men0}
end

local function finish()
    if state.finished then return end
    local battle = bm.battle
    if not get(battle, "battle_outcome_decided", false) then return end
    local winner, mine = get(battle, "victorious_alliance", 0), get(battle, "local_alliance", 1)
    if winner == -1 or get(battle, "is_draw", false) then
        state.result = "draw"
    elseif winner == 0 then
        return
    else
        state.result = winner == mine and "won" or "lost"
    end
    state.finished = true
    -- For evaluation only: the result observation ends the episode before any decision.
    state.final = {friendly = strength(state.friendly), enemy = strength(state.enemy)}
    for _, entry in pairs(state.friendly) do
        pcall(function() entry.controller:release_control() end)
    end
    if state.paused then
        pcall(function() bm:modify_battle_speed(session.speed or 1, true) end)
        state.paused = false
    end
    publish_observation(battle_time(), false)
    bm:remove_process("twwarhammer3_tick")
    log("result " .. state.result)
end

-- The results popup's rematch button, then the "Are you sure?" dialog's tick, reload the
-- same battle (bm:restart_battle(), the RestartBattle context command, did nothing on the
-- results screen). A decided battle is ended at once so the popup opens; RestartBattle is
-- the fallback before a decision.
local function restart()
    if state.finished then pcall(function() bm:end_battle() end) end
    local waited, rematched = 0, false
    bm:repeat_real_callback(guarded("restart", function()
        waited = waited + 1000
        local button = ui.find(rematched and CONFIRM or REMATCH)
        if button and not rematched then
            button:SetVisible(true)
            button:SimulateLClick()
            rematched = true
            log("rematch clicked")
        elseif button then
            bm:remove_real_callback("twwarhammer3_restart")
            button:SimulateLClick()
            log("rematch confirmed")
        elseif waited >= (state.finished and 60000 or 3000) then
            bm:remove_real_callback("twwarhammer3_restart")
            log(rematched and "no rematch confirmation" or "no rematch button")
            if not state.finished then bm:restart_battle() end
        end
    end), 1000, "twwarhammer3_restart")
end

local function tick()
    local now = battle_time()
    if state.pending then apply_pending(now) end
    if not state.finished and get(bm.battle, "battle_outcome_decided", false) then
        finish()
        return
    end
    if state.force_observe or now >= state.next_observe_ms then
        local awaiting = false
        if session.pause and state.started and not state.finished and not state.pending then
            local interval = session.interval_ms or 5000
            awaiting = state.applied_ms == nil or (now - state.applied_ms) >= interval
        end
        state.force_observe = false
        state.next_observe_ms = now + (session.observe_ms or 1000)
        local published = publish_observation(now, awaiting)
        if published and awaiting and not state.paused then
            bm:modify_battle_speed(0, true)
            state.paused = true
        end
    end
end

-- UI steps for probing the battle UI (menu --battle): the frontend script is unloaded
-- during a battle, so menu.json is free, and orders.json stays the job's alone.
local function run_menu()
    local text = read_file(BRIDGE .. "menu.json")
    if not text then return end
    os.remove(BRIDGE .. "menu.json")
    local ok, message = pcall(json.decode, text)
    if not ok or type(message) ~= "table" or type(message.steps) ~= "table" then return end
    for index, step in ipairs(message.steps) do
        local done_ok, done = pcall(ui.run, step, BRIDGE)
        log(string.format("ui %d: %s", index, done_ok and tostring(done) or clean_error(done)))
    end
end

local function poll()
    run_menu()
    local text = read_file(BRIDGE .. "orders.json")
    if not text then return end
    os.remove(BRIDGE .. "orders.json")
    local ok, message = pcall(json.decode, text)
    if not ok or type(message) ~= "table" then log("orders.json unreadable; dropped"); return end
    if message.job ~= session.job or message.battle ~= state.battle then
        log("stale request " .. tostring(message.request) .. " for battle " .. tostring(message.battle))
        return
    end
    if message.request == state.last_request then
        log("duplicate request " .. tostring(message.request))
        return
    end
    state.last_request = message.request
    if message.control == "restart" then
        log("restart requested by " .. tostring(message.request))
        restart()
        return
    elseif message.control == "start" then
        try_end_deployment()
        return
    elseif message.control then
        log("unknown control " .. tostring(message.control))
        return
    end
    state.pending = message
    if state.paused then
        bm:modify_battle_speed(session.speed or 1, true)
        state.paused = false
    end
end

local function start()
    if state.started then return end
    state.started = true
    local army = bm:get_player_army()
    state.alliance = bm:get_player_alliance()
    local units = army:units()
    for index = 1, units:count() do
        local unit = units:item(index)
        local id = "f" .. index
        local controller = army:create_unit_controller()
        controller:add_units(unit)
        controller:take_control()
        state.friendly[id] = {unit = unit, controller = controller, class = unit_class(unit)}
        state.friendly_ids[#state.friendly_ids + 1] = id
    end
    local armies = bm:get_non_player_alliance():armies()
    local count = 0
    for army_index = 1, armies:count() do
        local enemy_units = armies:item(army_index):units()
        for index = 1, enemy_units:count() do
            local unit = enemy_units:item(index)
            count = count + 1
            local id = "e" .. count
            state.enemy[id] = {unit = unit, class = unit_class(unit)}
            state.enemy_ids[#state.enemy_ids + 1] = id
            state.enemy_by_ui[get(unit, "unique_ui_id", -1)] = id
        end
    end
    bm:modify_battle_speed(session.speed or 1, true)
    state.force_observe = true
    bm:repeat_callback(tick, session.tick_ms or 250, "twwarhammer3_tick")
    log(string.format("started: %d friendly, %d enemy units", #state.friendly_ids, count))
end

local function load()
    session = read_json(BRIDGE .. "session.json")
    if not session or session.enabled == false then return end
    local battle = bm.battle
    for _, check in ipairs({"is_multiplayer", "is_replay", "is_from_campaign", "is_quest_battle", "is_tutorial"}) do
        if get(battle, check, false) then
            log("inactive: " .. check)
            return
        end
    end
    state.battle = string.format("%d-%s", os.time(), tostring(os.clock()))
    log("loaded battle " .. state.battle .. " for job " .. tostring(session.job))
    bm:register_phase_change_callback("Deployed", guarded("start", start))
    bm:register_phase_change_callback("VictoryCountdown", guarded("finish", finish))
    bm:register_phase_change_callback("Complete", guarded("finish", finish))
    bm:repeat_real_callback(guarded("poll", poll), 200, "twwarhammer3_poll")
    if session.autostart then
        -- Deployment begins after the loading screen; keep trying until combat starts.
        bm:repeat_real_callback(guarded("autostart", function()
            if state.started or state.finished then
                bm:remove_real_callback("twwarhammer3_autostart")
            elseif bm:get_current_phase_name() == "Deployment" then
                try_end_deployment()
            end
        end), 5000, "twwarhammer3_autostart")
    end
    publish("observation.json", {
        schema = 1, job = session.job, battle = state.battle, seq = 0, phase = "Loading",
        time_ms = 0, speed = session.speed or 1, awaiting_orders = false, friendly = {},
        enemy_roster = {}, enemy = {},
    })
end

local ok, err = pcall(load)
if not ok then log("load failed: " .. clean_error(err)) end
